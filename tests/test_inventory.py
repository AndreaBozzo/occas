"""One corpus directory, two draws, and they must not be pooled.

`data/parquet` holds every run ever converted. Since 2026-08-26 that is the pilot's 100
and the H1 draw's 1,600, overlapping in 50 -- so "every directory under the corpus root"
stopped being a description of any one sample. The pilot's leftover 50 are rotorcraft, at
roughly 8% usable against fixed-wing's 72%, so pooling them into H1's rate would move the
headline number that answers G2.

No network and no ULog here: the question is which run directories the inventory counts,
which is settled by names on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.common import manifest as manifest_module
from ingest import inventory

pytest.importorskip("pyarrow")


@pytest.fixture(autouse=True)
def manifests_stay_out_of_the_repository(tmp_path, monkeypatch):
    """``inventory.main`` writes a manifest; it must not write it into ``artifacts/``.

    Nine of them landed there the first time this file ran, each attesting a summary in
    a pytest temp directory that no longer exists -- provenance records pointing at
    nothing, in the directory whose whole job is provenance.

    Patching ``manifest.MANIFEST_DIR`` does not reach it: ``write_manifest``'s
    ``directory`` default is bound at import time, so the name the caller resolves is
    the one to replace.
    """
    directory = tmp_path / "manifests"
    monkeypatch.setattr(
        inventory,
        "write_manifest",
        lambda built: manifest_module.write_manifest(built, directory),
    )
    return directory


def _corpus(root: Path, names: list[str]) -> Path:
    """A corpus directory of empty run directories, plus the files that are not runs."""
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / name).mkdir()
    (root / "conversion-summary.json").write_text("{}", encoding="utf-8")
    return root


def _sample(path: Path, rows: list[tuple[str, str]]) -> Path:
    path.write_text(
        "".join(json.dumps({"log_id": i, "stratum": s, "log_date": None}) + "\n" for i, s in rows),
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_runs_outside_the_sample_are_excluded_and_counted(tmp_path, capsys) -> None:
    """A run from another draw is set aside, and how many were set aside is recorded.

    Excluded rather than filed under "unknown": `summarise` did put strangers in an
    unknown stratum, so they were visible, but they still counted towards `runs` and
    `usable_rate`. Visible-but-counted is the shape of most pooling errors.
    """
    corpus = _corpus(tmp_path / "parquet", ["aaa", "bbb", "ccc"])
    sample = _sample(tmp_path / "sample.jsonl", [("aaa", "fixed_wing_or_vtol|older")])
    out = tmp_path / "summary.json"

    inventory.main(
        [
            "--parquet",
            str(corpus),
            "--sample",
            str(sample),
            "--out",
            str(out),
            "--per-run",
            str(tmp_path / "per-run.jsonl"),
        ]
    )

    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["runs"] == 1, "counted runs belonging to a different draw"
    assert summary["runs_outside_sample_excluded"] == 2
    assert "unknown" not in summary["by_stratum"]
    assert "excluded" in capsys.readouterr().out


def test_a_sample_naming_no_converted_run_yields_an_empty_inventory(tmp_path) -> None:
    """Not an error, and not a silent fallback to the whole directory.

    The failure this guards against is a mistyped ``--sample`` quietly inventorying the
    entire corpus and reporting it as that sample's result.
    """
    corpus = _corpus(tmp_path / "parquet", ["aaa", "bbb"])
    sample = _sample(tmp_path / "sample.jsonl", [("zzz", "fixed_wing_or_vtol|older")])
    out = tmp_path / "summary.json"

    inventory.main(
        [
            "--parquet",
            str(corpus),
            "--sample",
            str(sample),
            "--out",
            str(out),
            "--per-run",
            str(tmp_path / "per-run.jsonl"),
        ]
    )

    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["runs"] == 0
    assert summary["runs_outside_sample_excluded"] == 2
    assert summary["usable_rate"] is None


def test_without_a_sample_every_run_is_still_inventoried(tmp_path) -> None:
    """The restriction is the sample's, so no sample means no restriction.

    Kept working because it is how the corpus is inspected before a draw exists.
    """
    corpus = _corpus(tmp_path / "parquet", ["aaa", "bbb"])
    out = tmp_path / "summary.json"

    inventory.main(
        [
            "--parquet",
            str(corpus),
            "--sample",
            str(tmp_path / "absent.jsonl"),
            "--out",
            str(out),
            "--per-run",
            str(tmp_path / "per-run.jsonl"),
        ]
    )

    summary = json.loads(out.read_text(encoding="utf-8"))
    assert summary["runs"] == 2
    assert summary["runs_outside_sample_excluded"] == 0
