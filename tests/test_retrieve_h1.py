"""A log that fails once has not been shown to be unavailable.

Audit row A8 asks whether Dronecode's retention policy deletes the `.ulg` files. The
retrieval answers it as a byproduct: a sampled log either downloads or it does not. That
only works if "does not" means the server has nothing to give, and upstream's downloader
also gives up after five failed *connections* -- which happened once in the first 800 logs
of the H1 draw, on 2026-08-26, while the log requested immediately after it recovered on
its first retry.

Recording that as unavailable would feed a network fact into the evidence for a question
about deletion, and would do so in the direction of the hypothesis. So a log is recorded
absent only after two attempts on two separate connections.

No network: the downloader is replaced by one that writes the files a real one would.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.common import manifest as manifest_module
from ingest import availability, retrieve_h1

FIRST = "aaaaaaaa-0000-0000-0000-000000000001"
FLAKY = "bbbbbbbb-0000-0000-0000-000000000002"


def _write_ulog(path: Path) -> None:
    """A file that passes the magic-byte and size checks, describing no real flight."""
    path.write_bytes(availability.ULOG_MAGIC + b"\0" * availability.MIN_PLAUSIBLE_BYTES)


class _NoServer:
    def shutdown(self) -> None:
        """The real one serves the pinned frame; nothing here makes a request."""


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """A retrieval whose only real parts are the bookkeeping under test."""
    raw = tmp_path / "raw"
    raw.mkdir()
    sample = tmp_path / "sample.jsonl"
    sample.write_text(
        "".join(
            json.dumps(
                {
                    "log_id": log_id,
                    "stratum": "fixed_wing_or_vtol|older",
                    "log_date": "2025-01-24",
                    "ulg_available": None,
                }
            )
            + "\n"
            for log_id in (FIRST, FLAKY)
        ),
        encoding="utf-8",
        newline="\n",
    )

    monkeypatch.setattr(
        retrieve_h1,
        "serve_pinned_frame",
        lambda: (
            _NoServer(),
            "http://127.0.0.1:0/dbinfo",
            {FIRST.replace("-", ""), FLAKY.replace("-", "")},
        ),
    )
    monkeypatch.setattr(retrieve_h1, "convert_chunk", lambda *_: 0)
    monkeypatch.setattr(
        retrieve_h1,
        "write_manifest",
        lambda built: manifest_module.write_manifest(built, tmp_path / "manifests"),
    )
    return {
        "raw": raw,
        "sample": sample,
        "out": tmp_path / "availability.json",
        "progress": tmp_path / "progress.jsonl",
        "parquet": tmp_path / "parquet",
    }


def _run(harness) -> dict:
    assert (
        retrieve_h1.main(
            [
                "--sample",
                str(harness["sample"]),
                "--raw",
                str(harness["raw"]),
                "--parquet",
                str(harness["parquet"]),
                "--out",
                str(harness["out"]),
                "--progress",
                str(harness["progress"]),
                "--chunk-size",
                "10",
            ]
        )
        == 0
    )
    return json.loads(harness["out"].read_text(encoding="utf-8"))


def test_a_log_that_arrives_on_the_second_attempt_is_available(harness, monkeypatch) -> None:
    """The exact case seen in chunk 8: five connections fail, the sixth works."""
    attempts = {"n": 0}

    def flaky_download(chunk, raw, _api):
        attempts["n"] += 1
        for row in chunk:
            if row["log_id"] == FLAKY and attempts["n"] == 1:
                continue  # upstream: "Failed after 5 attempts. Skipping."
            _write_ulog(raw / f"{row['log_id']}.ulg")
        return 0

    monkeypatch.setattr(retrieve_h1, "download_chunk", flaky_download)
    summary = _run(harness)

    assert attempts["n"] == 2, "never made a second attempt"
    assert summary["available"] == 2
    assert summary["missing"] == 0, "recorded a transient connection failure as a missing log"

    # Both observations are kept. The first is not rewritten, because "failed once then
    # arrived" is a different fact from "arrived", and the retrieval rate is worth knowing.
    rows = [
        json.loads(line) for line in harness["progress"].read_text(encoding="utf-8").splitlines()
    ]
    flaky = [r for r in rows if r["log_id"] == FLAKY]
    assert [(r["attempt"], r["ulg_available"]) for r in flaky] == [(1, False), (2, True)]


def test_a_log_that_fails_twice_is_recorded_absent(harness, monkeypatch) -> None:
    """Two attempts on two connections is the bar. A log that clears neither is gone.

    This is the observation audit row A8 is actually about, and it must still be made.
    """

    def always_missing(chunk, raw, _api):
        for row in chunk:
            if row["log_id"] != FLAKY:
                _write_ulog(raw / f"{row['log_id']}.ulg")
        return 0

    monkeypatch.setattr(retrieve_h1, "download_chunk", always_missing)
    summary = _run(harness)

    assert summary["available"] == 1
    assert summary["missing"] == 1
    assert summary["availability_rate"] == 0.5


def test_no_second_pass_when_everything_arrived(harness, monkeypatch) -> None:
    """The retry costs requests, so it happens only when something is actually missing."""
    attempts = {"n": 0}

    def clean_download(chunk, raw, _api):
        attempts["n"] += 1
        for row in chunk:
            _write_ulog(raw / f"{row['log_id']}.ulg")
        return 0

    monkeypatch.setattr(retrieve_h1, "download_chunk", clean_download)
    summary = _run(harness)

    assert attempts["n"] == 1, "asked the service for logs it had already delivered"
    assert summary["available"] == 2
