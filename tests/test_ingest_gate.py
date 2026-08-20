"""The download wrapper refuses to run while the personal-data audit is unresolved (G1)."""

from __future__ import annotations

import json

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


def test_out_dir_is_forced_on_the_upstream_script(tmp_path) -> None:
    """The logs must land beside the record that describes them."""
    command = px4_download.upstream_command(
        tmp_path / "dl.py", tmp_path / "raw", ["--max-num", "5"]
    )
    assert "--download-folder" in command
    assert command[command.index("--download-folder") + 1] == str(tmp_path / "raw")
    assert command[-2:] == ["--max-num", "5"]


def test_explicit_download_folder_is_respected_with_a_warning(tmp_path, capsys) -> None:
    command = px4_download.upstream_command(tmp_path / "dl.py", tmp_path / "raw", ["-d", "/other"])
    assert command.count("-d") == 1
    assert "--download-folder" not in command
    assert "Warning" in capsys.readouterr().err


def test_retrieval_record_carries_the_g1_taint(tmp_path) -> None:
    """A blocked pull stays machine-readably blocked, not just warned about."""
    path = px4_download.write_retrieval_record(tmp_path, ["cmd"], 0, acknowledged=True)
    record = json.loads(path.read_text(encoding="utf-8"))
    blocking = px4_download.audit_is_blocking()
    assert record["publication_eligibility"] == ("blocked" if blocking else "eligible")
    assert record["policy_reason"] == ("G1_PERSONAL_DATA_UNRESOLVED" if blocking else None)
    assert record["acknowledged_unaudited"] is True
    assert record["download_folder"] == str(tmp_path)
