"""The download wrapper refuses to run while the personal-data audit is unresolved (G1)."""

from __future__ import annotations

import json

import pytest

from ingest import px4_download


def test_gate_is_derived_from_the_document() -> None:
    """The gate reads the audit rather than a hard-coded constant."""
    assert px4_download.AUDIT.exists()
    assert px4_download.G1_STATUS.search(px4_download.AUDIT.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("body", "blocking"),
    [
        ("**G1-status: NOT CLEARED**", True),
        ("**G1-status: CLEARED**", False),
        ("**G1-status:   CLEARED**", False),
        # Fails closed: anything the gate does not positively recognise blocks.
        ("the personal-data section is fine now, honest", True),
        ("**G1-status: PROBABLY FINE**", True),
        ("G1-status: CLEARED", True),
        ("", True),
    ],
)
def test_gate_fails_closed(tmp_path, monkeypatch, body: str, blocking: bool) -> None:
    """Only an explicit CLEARED line opens G1.

    The gate used to search for a phrase that also appeared in the audit's prose, so
    rewriting the prose opened it silently. That happened on 2026-08-24: answering
    B1-B5 removed the phrase and the download gate swung open, stamping retrieval
    records publication_eligibility=eligible. The rows below are the shapes that
    mistake can take.
    """
    audit = tmp_path / "01-source-audit.md"
    audit.write_text("# audit\n\n" + body + "\n\nmore prose\n", encoding="utf-8")
    monkeypatch.setattr(px4_download, "AUDIT", audit)
    assert px4_download.audit_is_blocking() is blocking


def test_gate_blocks_when_the_audit_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(px4_download, "AUDIT", tmp_path / "gone.md")
    assert px4_download.audit_is_blocking() is True


def test_the_real_audit_is_cleared() -> None:
    """G1 was cleared on 2026-08-25, on the DPIA adopted the same day.

    This assertion is the deliberate act of clearing it: the previous version asserted
    the gate blocked, and flipping it is meant to be a visible line in a diff rather than
    a test that quietly started skipping. That is exactly how the gate was opened by
    accident once before, on 2026-08-24, when prose was rewritten.
    """
    assert px4_download.audit_is_blocking() is False


def test_the_encryption_measure_is_confirmed() -> None:
    """R5's measure is real as of 2026-08-25: EFS on data/, not merely declared.

    This assertion flipped deliberately, in the commit that applied the encryption. It
    asserted blocking while the machine was unencrypted -- which it was at adoption --
    and a gate that opens without a visible line in a diff is the failure mode this
    project has already had once.
    """
    assert px4_download.encryption_is_blocking() is False


@pytest.mark.parametrize(
    ("body", "blocking"),
    [
        ("**R5-encryption-at-rest: NOT CONFIRMED**", True),
        ("**R5-encryption-at-rest: CONFIRMED**", False),
        ("  **R5-encryption-at-rest: CONFIRMED**", False),
        # Fails closed, in the same shapes G1 does.
        ("the disk is encrypted, trust me", True),
        ("**R5-encryption-at-rest: PROBABLY**", True),
        ("R5-encryption-at-rest: CONFIRMED", True),
        ("", True),
    ],
)
def test_encryption_gate_fails_closed(tmp_path, monkeypatch, body: str, blocking: bool) -> None:
    dpia = tmp_path / "09-dpia.md"
    dpia.write_text("# dpia\n\n" + body + "\n\nmore prose\n", encoding="utf-8")
    monkeypatch.setattr(px4_download, "DPIA", dpia)
    assert px4_download.encryption_is_blocking() is blocking


def test_encryption_gate_blocks_when_the_dpia_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(px4_download, "DPIA", tmp_path / "gone.md")
    assert px4_download.encryption_is_blocking() is True


def test_both_gates_are_open_against_the_real_documents() -> None:
    """Retrieval is permitted. Recorded as an assertion so reverting either flag fails.

    The parametrised tests above still hold both gates to failing closed on anything
    unrecognised; this one records the live state the project is actually in.
    """
    assert px4_download.audit_is_blocking() is False
    assert px4_download.encryption_is_blocking() is False


@pytest.fixture
def gates_open(tmp_path, monkeypatch):
    """Open the permission gates so the operational checks below can be reached.

    G1 and R5 are deliberately checked before anything else in ``main``, so a test about
    a missing upstream script or a missing exclusion list would otherwise only ever
    observe R5 refusing. Opening them here is scoped to the test, never to the repository.
    """
    dpia = tmp_path / "09-dpia.md"
    dpia.write_text("**R5-encryption-at-rest: CONFIRMED**\n", encoding="utf-8")
    monkeypatch.setattr(px4_download, "DPIA", dpia)
    return tmp_path


def test_missing_upstream_script_is_reported(gates_open, tmp_path, capsys) -> None:
    code = px4_download.main(
        ["--upstream", str(tmp_path / "nope.py"), "--out-dir", str(tmp_path / "raw")]
    )
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


def test_download_refuses_when_the_exclusion_list_is_missing(
    gates_open, tmp_path, monkeypatch, capsys
) -> None:
    """Article 21 must not be honoured only when someone remembers to look.

    A missing list is not an empty one. Retrieving while unable to say which objections
    were in force is the failure this blocks, and it blocks before anything is fetched.
    """
    from analysis.common import exclusions

    upstream = tmp_path / "download_logs.py"
    upstream.write_text("", encoding="utf-8")
    monkeypatch.setattr(exclusions, "EXCLUSIONS_PATH", tmp_path / "absent.jsonl")

    code = px4_download.main(["--upstream", str(upstream), "--out-dir", str(tmp_path / "raw")])
    assert code == 2
    assert "does not exist" in capsys.readouterr().err


def test_the_retrieval_record_names_the_exclusion_state_not_the_objectors(tmp_path) -> None:
    """The record must say which exclusions applied, and never whose logs they were."""
    from analysis.common import exclusions

    path = px4_download.write_retrieval_record(tmp_path, ["cmd"], 0, acknowledged=True)
    state = json.loads(path.read_text(encoding="utf-8"))["exclusions"]
    assert state["digest"].startswith("sha256:")
    assert set(state) == {"path", "digest", "count", "latest_received"}
    assert state["count"] == exclusions.load().count


def test_the_separator_is_not_passed_to_the_upstream_script(gates_open, tmp_path) -> None:
    """`--` belongs to our argparse, not upstream's.

    argparse.REMAINDER keeps the separator and upstream's own parser then rejects it as
    an unrecognised argument -- downloading nothing while the wrapper still writes a
    retrieval record describing the run. That happened on 2026-08-25 and cost a pilot
    retrieval that looked like it had succeeded.

    Driven through ``main`` on purpose: the stripping happens there, so a test against
    ``upstream_command`` alone passes with and without the fix.
    """
    seen = tmp_path / "argv.json"
    upstream = tmp_path / "download_logs.py"
    upstream.write_text(
        "import json, sys, pathlib\n"
        f"pathlib.Path({str(seen)!r}).write_text(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    px4_download.main(
        [
            "--upstream",
            str(upstream),
            "--out-dir",
            str(tmp_path / "raw"),
            "--",
            "--log-id",
            "abc",
            "--max-num",
            "1",
        ]
    )
    argv = json.loads(seen.read_text(encoding="utf-8"))
    assert "--" not in argv
    assert argv[-4:] == ["--log-id", "abc", "--max-num", "1"]
