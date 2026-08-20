"""The download wrapper refuses to run while the source audit is unanswered (gate G1)."""

from __future__ import annotations

import pytest

from ingest import px4_download


def test_audit_is_detected_as_unstarted() -> None:
    """Fails once docs/01-source-audit.md is actually started, which is the point:
    the gate is derived from the document, not hard-coded."""
    assert px4_download.AUDIT.exists()
    assert px4_download.audit_is_unstarted() is (
        px4_download.UNSTARTED_MARKER in px4_download.AUDIT.read_text(encoding="utf-8")
    )


@pytest.mark.skipif(not px4_download.audit_is_unstarted(), reason="source audit has been started")
def test_refuses_to_download_while_the_audit_is_unstarted(tmp_path, capsys) -> None:
    code = px4_download.main(["--upstream", str(tmp_path / "download_logs.py")])
    assert code == 2
    assert "NOT STARTED" in capsys.readouterr().err
    assert not (tmp_path / "retrieval").exists()


def test_missing_upstream_script_is_reported(tmp_path, capsys) -> None:
    code = px4_download.main(["--upstream", str(tmp_path / "nope.py"), "--acknowledge-unaudited"])
    assert code == 2
    assert "not found" in capsys.readouterr().err
