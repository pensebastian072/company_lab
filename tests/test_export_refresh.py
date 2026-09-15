from __future__ import annotations

from clab.export import refresh


def test_place_uses_pending_sibling_when_stable_file_is_locked(monkeypatch, tmp_path):
    dated = tmp_path / "company_lab_2026-08-12.xlsx"
    stable = tmp_path / "company_lab_latest.xlsx"
    dated.write_bytes(b"fresh")

    real_copyfile = refresh.shutil.copyfile

    def locked_copy(src, dst):
        if dst == stable:
            raise PermissionError("Excel has the file open")
        return real_copyfile(src, dst)

    monkeypatch.setattr(refresh.shutil, "copyfile", locked_copy)
    ok, where = refresh._place(dated, stable)

    assert ok is False
    assert where == tmp_path / "company_lab_latest_PENDING.xlsx"
    assert where.read_bytes() == b"fresh"


def test_refresh_returns_no_scores_without_writing(monkeypatch):
    monkeypatch.setattr(refresh, "load_rows", lambda: [])
    assert refresh.refresh(day="2026-08-12") == refresh.EXIT_NO_SCORES
