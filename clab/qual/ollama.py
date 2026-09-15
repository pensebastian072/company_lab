"""Local Ollama client plus a GPU lease.

Ported from research_rag/rag/common.py::_post/chat/embed_texts, with three
additions this repo needs:

  - `num_ctx` is set EXPLICITLY. research_rag documents that the default silently
    truncates the front of a long prompt, which here would mean quietly dropping
    the 10-K evidence and scoring on the instructions alone.
  - `keep_alive` so the model loads once per batch rather than once per company.
    This is the single largest throughput lever, worth roughly 20-30 s per company.
  - a GPU lease. The RTX 3050 has 6 GB and qwen2.5:7b takes ~4.7 GB of it, so two
    overlapping runs would thrash. No lease convention existed anywhere on this box,
    so company_lab defines one: an advisory lock file with a TTL, which protects
    this repo from itself. It does not stop a sibling repo that does not honour it,
    which is why the qual task is scheduled at 02:30 when nothing else runs.

Everything here degrades rather than raising: a refused connection, a timeout or
unparseable output all become "no score", which the scoring layer renders as
NO_DATA - never a neutral midpoint, and never a zero.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .. import config
from ..net import atomic_write_json, read_json, utc_now_iso


class OllamaUnavailable(RuntimeError):
    pass


def _post(endpoint: str, payload: dict, timeout: float = 300.0) -> dict:
    url = f"{config.OLLAMA_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        raise OllamaUnavailable(f"{type(exc).__name__}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise OllamaUnavailable(f"unparseable response: {exc}") from exc


def available() -> tuple[bool, str]:
    """Is Ollama up, and does it have the model we need?"""
    try:
        url = f"{config.OLLAMA_URL.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=10) as resp:
            tags = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return False, f"ollama unreachable at {config.OLLAMA_URL}: {type(exc).__name__}"
    names = {m.get("name", "") for m in (tags.get("models") or [])}
    if not any(n.startswith(config.QUAL_MODEL.split(":")[0]) for n in names):
        return False, (f"model {config.QUAL_MODEL} not present; have "
                       f"{sorted(names) or 'nothing'}")
    return True, f"ollama up with {len(names)} models"


def chat(prompt: str, *, system: str = "", model: str | None = None,
         num_predict: int | None = None, timeout: float = 300.0,
         fmt: dict | None = None) -> str:
    """One completion. Raises OllamaUnavailable; callers degrade to NO_DATA."""
    payload = {
        "model": model or config.QUAL_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "keep_alive": config.QUAL_KEEP_ALIVE,
        "options": {
            # set explicitly: the default silently truncates long prompts
            "num_ctx": config.QUAL_NUM_CTX,
            "temperature": config.QUAL_TEMPERATURE,
            "seed": config.QUAL_SEED,
            "num_predict": num_predict or config.QUAL_NUM_PREDICT,
        },
    }
    # Only present when explicitly asked for. Absent, ollama picks the placement itself,
    # which is what every GPU lane wants; 0 forces CPU-only for a parallel lane that must
    # not touch the card. See config.QUAL_NUM_GPU for why the env var route does not work.
    if config.QUAL_NUM_GPU is not None:
        payload["options"]["num_gpu"] = config.QUAL_NUM_GPU
    if config.QUAL_NUM_THREAD is not None:
        payload["options"]["num_thread"] = config.QUAL_NUM_THREAD
    # Structured output. Ollama constrains generation to this JSON schema, which makes a
    # parse failure, a missing key and a prose preamble structurally impossible rather
    # than merely discouraged. Measured 2026-08-28: LFM2.5-2.6B-Finance emitted 3,417
    # characters of reasoning and was truncated before reaching any JSON - a 77.8%
    # "parse failure" rate that was a format artefact, not judgement.
    #
    # The schema keeps `null` as a legal type for every score (see prompts.schema_for).
    # A schema that forced an integer would convert every honest abstention into a
    # fabricated number, which is the exact opposite of what this pipeline needs.
    if fmt is not None:
        payload["format"] = fmt
    out = _post("api/generate", payload, timeout=timeout)
    return (out.get("response") or "").strip()


#: Measured on this box: the legacy per-item /api/embeddings endpoint costs
#: ~2.19 s per chunk, while the batch /api/embed endpoint costs ~0.013 s per
#: chunk - roughly 160x. Embedding one company's filing went from about six
#: minutes to about two seconds. Always batch; the singular endpoint is only a
#: fallback for an Ollama too old to have /api/embed.
EMBED_BATCH = 64


def embed(texts: list[str], *, model: str | None = None,
          is_query: bool = False) -> list[list[float]]:
    """Embeddings for retrieval. nomic-embed-text requires the task prefixes."""
    if not texts:
        return []
    prefix = "search_query: " if is_query else "search_document: "
    prefixed = [prefix + t for t in texts]
    name = model or config.EMBED_MODEL
    vecs: list[list[float]] = []
    for i in range(0, len(prefixed), EMBED_BATCH):
        chunk = prefixed[i:i + EMBED_BATCH]
        try:
            out = _post("api/embed",
                        {"model": name, "input": chunk,
                         "keep_alive": config.QUAL_KEEP_ALIVE},
                        timeout=300.0)
            got = out.get("embeddings")
            if isinstance(got, list) and len(got) == len(chunk):
                vecs.extend(v or [] for v in got)
                continue
        except OllamaUnavailable:
            pass
        vecs.extend(_embed_one_by_one(chunk, name))
    return vecs


def _embed_one_by_one(prefixed: list[str], model: str) -> list[list[float]]:
    """Fallback for an Ollama without /api/embed. Slow - see EMBED_BATCH."""
    out: list[list[float]] = []
    for t in prefixed:
        try:
            res = _post("api/embeddings", {"model": model, "prompt": t}, timeout=120.0)
            out.append(res.get("embedding") or [])
        except OllamaUnavailable:
            out.append([])
    return out


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


# ------------------------------------------------------------------ GPU lease
def _lease_expired(lease: dict) -> bool:
    exp = lease.get("expires_at")
    if not exp:
        return True
    try:
        when = datetime.fromisoformat(exp)
    except (TypeError, ValueError):
        return True
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > when


def lease_holder() -> dict | None:
    """The current live lease, or None if absent, expired or dead."""
    lease = read_json(config.GPU_LEASE)
    if not isinstance(lease, dict):
        return None
    if _lease_expired(lease):
        return None
    pid = lease.get("pid")
    if isinstance(pid, int) and pid != os.getpid() and not _pid_alive(pid):
        return None          # holder died without releasing
    return lease


def _pid_alive(pid: int) -> bool:
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    except Exception:  # noqa: BLE001 - unknown means assume alive; the TTL still frees it
        return True


@contextmanager
def gpu_lease(*, minutes: int | None = None, wait: bool = False,
              poll_seconds: float = 30.0, max_wait_minutes: float = 0.0):
    """Advisory GPU lease. Yields True when held, False when someone else holds it.

    The TTL is what makes this safe: a killed process cannot deadlock the GPU
    forever, it just holds the lease until it expires.
    """
    minutes = minutes or config.GPU_LEASE_TTL_MINUTES
    deadline = time.monotonic() + max_wait_minutes * 60
    while True:
        holder = lease_holder()
        if holder is None or holder.get("pid") == os.getpid():
            break
        if not wait or time.monotonic() > deadline:
            yield False
            return
        time.sleep(poll_seconds)

    lease = {
        "pid": os.getpid(),
        "repo": "company_lab",
        "model": config.QUAL_MODEL,
        "acquired_at": utc_now_iso(),
        "expires_at": (datetime.now(timezone.utc)
                       + timedelta(minutes=minutes)).isoformat(),
    }
    try:
        atomic_write_json(config.GPU_LEASE, lease)
    except Exception:  # noqa: BLE001 - an unwritable lease must not block the work
        pass
    try:
        yield True
    finally:
        try:
            current = read_json(config.GPU_LEASE)
            if isinstance(current, dict) and current.get("pid") == os.getpid():
                config.GPU_LEASE.unlink(missing_ok=True)
        except OSError:
            pass


def renew_lease(*, minutes: int | None = None) -> None:
    """Extend our own lease mid-batch so a long run does not expire under itself."""
    minutes = minutes or config.GPU_LEASE_TTL_MINUTES
    current = read_json(config.GPU_LEASE)
    if isinstance(current, dict) and current.get("pid") == os.getpid():
        current["expires_at"] = (datetime.now(timezone.utc)
                                 + timedelta(minutes=minutes)).isoformat()
        try:
            atomic_write_json(config.GPU_LEASE, current)
        except Exception:  # noqa: BLE001
            pass
