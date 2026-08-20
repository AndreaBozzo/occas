"""The download wrapper refuses to run while the personal-data audit is unresolved (G1)."""

from __future__ import annotations

import pytest

from ingest import px4_download


def test_gate_is_derived_from_the_document() -> None:
    """Opens by itself once B1-B5 are answered; the gate is not hard-coded."""
    assert px4_download.AUDIT.exists()
    assert px4_download.audit_is_blocking() is (
        px4_download.BLOCKING_MARKER in px4_download.AUDIT.read_text(encoding="utf-8")
    )


@pytest.mark.skipif(not px4_download.audit_is_blocking(), reason="personal-data section resolved")
def test_refuses_to_download_while_personal_data_is_unresolved(tmp_path, capsys) -> None:
    code = px4_download.main(["--upstream", str(tmp_path / "download_logs.py")])
    assert code == 2
    assert "UNRESOLVED" in capsys.readouterr().err
    assert not (tmp_path / "retrieval").exists()


def test_missing_upstream_script_is_reported(tmp_path, capsys) -> None:
    code = px4_download.main(["--upstream", str(tmp_path / "nope.py"), "--acknowledge-unaudited"])
    assert code == 2
    assert "not found" in capsys.readouterr().err
