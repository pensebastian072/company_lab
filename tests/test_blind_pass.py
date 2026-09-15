"""The blind pass is enforced by mechanism, not by asking.

Until E53 both request files were written at stage time, so the pass-B conclusions - our
local model's SG/BQ - sat on disk at a documented path for the whole of the blind pass.
On E53 they were opened during routine inventory and the breach was reported honestly.
A blind anyone can lift by opening a file is not a blind, and that is a defect in this
module rather than a failure by the researcher.
"""
from __future__ import annotations

import json

import pytest

from clab.external import request as R


@pytest.fixture()
def staged(tmp_path, monkeypatch):
    """Redirect every path this module writes to, so nothing touches the live flags."""
    from clab import config
    monkeypatch.setattr(config, "EXTERNAL_REQUEST", tmp_path / "request.json")
    monkeypatch.setattr(config, "EXTERNAL_CONCLUSIONS", tmp_path / "conclusions.json")
    monkeypatch.setattr(config, "EXTERNAL_ROOT", tmp_path / "ext")
    return config


def _pair(request_id="abc123"):
    req = {"request_id": request_id, "roster": [{"ticker": "AAA"}]}
    con = {"request_id": request_id, "conclusions": [{"ticker": "AAA", "sg": 18}]}
    return req, con


def test_staging_does_NOT_write_the_conclusions_file(staged):
    req, con = _pair()
    a, b = R.write(req, con)
    assert a.exists(), "pass A must be staged"
    assert b is None
    assert not staged.EXTERNAL_CONCLUSIONS.exists(), \
        "the whole point: the answers must not be on disk during the blind pass"


def test_staging_deletes_a_STALE_release_from_a_previous_request(staged):
    """Otherwise last request's answers stand in for this one's, and the blind is lifted
    without anyone doing anything wrong."""
    staged.EXTERNAL_CONCLUSIONS.write_text('{"request_id": "old"}', encoding="utf-8")
    R.write(*_pair())
    assert not staged.EXTERNAL_CONCLUSIONS.exists()


def test_release_REQUIRES_a_frozen_pass_A_on_disk(staged, tmp_path):
    req, con = _pair()
    R.write(req, con)
    with pytest.raises(FileNotFoundError):
        R.release_conclusions("abc123", tmp_path / "no_such_pass_a.json")
    assert not staged.EXTERNAL_CONCLUSIONS.exists()


def test_release_writes_the_conclusions_once_pass_A_exists(staged, tmp_path):
    req, con = _pair()
    R.write(req, con)
    pass_a = tmp_path / "pass_a.json"
    pass_a.write_text('{"companies": []}', encoding="utf-8")
    out = R.release_conclusions("abc123", pass_a)
    assert staged.EXTERNAL_CONCLUSIONS.exists()
    body = json.loads(staged.EXTERNAL_CONCLUSIONS.read_text(encoding="utf-8"))
    assert body["conclusions"][0]["sg"] == 18
    assert body["pass_a_sha256"] == out["pass_a_sha256"]


def test_the_released_file_records_pass_As_HASH(staged, tmp_path):
    """This is what turns "reconciliation did not alter pass A" from something reported
    into something checkable: the hash is taken at reveal time, so a pass A rewritten
    afterwards no longer matches it."""
    import hashlib
    req, con = _pair()
    R.write(req, con)
    pass_a = tmp_path / "pass_a.json"
    pass_a.write_bytes(b'{"companies": [1]}')
    R.release_conclusions("abc123", pass_a)
    recorded = json.loads(
        staged.EXTERNAL_CONCLUSIONS.read_text(encoding="utf-8"))["pass_a_sha256"]
    assert recorded == hashlib.sha256(b'{"companies": [1]}').hexdigest()

    pass_a.write_bytes(b'{"companies": [1, 2]}')      # rewritten after the reveal
    assert recorded != hashlib.sha256(pass_a.read_bytes()).hexdigest()


def test_releasing_an_unknown_request_raises(staged, tmp_path):
    pass_a = tmp_path / "pass_a.json"
    pass_a.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        R.release_conclusions("never_staged", pass_a)
