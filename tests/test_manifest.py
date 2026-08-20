"""No result without a manifest, so the manifest builder is itself tested."""

from __future__ import annotations

import hashlib
import json

import pytest
from jsonschema import ValidationError

from analysis.common import manifest as m


def test_hash_file_matches_hashlib(tmp_path) -> None:
    payload = b"binary\x00bytes\r\n"  # read as bytes: no newline translation
    path = tmp_path / "input.bin"
    path.write_bytes(payload)
    assert m.hash_file(path) == f"sha256:{hashlib.sha256(payload).hexdigest()}"


def test_build_manifest_satisfies_the_schema(tmp_path) -> None:
    inp = tmp_path / "input.parquet"
    inp.write_bytes(b"not really parquet")
    built = m.build_manifest(
        name="h1-agreement-smoke",
        hypothesis="H1",
        entrypoint="analysis/h1_agreement/run.py",
        inputs=[inp],
        parameters={"spatial_tolerance_km": 20.0},
        seed=20260820,
        external_tools=[{"name": "ulog-convert", "version": "fixture"}],
    )
    m.validate_manifest(built)
    assert built["inputs"][0]["content_hash"].startswith("sha256:")
    assert built["environment"]["dependencies"], "dependency versions must be resolved"


def test_manifest_rejects_an_unknown_hypothesis() -> None:
    built = m.build_manifest(name="x", hypothesis="H9", entrypoint="x.py")
    with pytest.raises(ValidationError):
        m.validate_manifest(built)


def test_add_output_records_the_hash(tmp_path) -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    out = tmp_path / "result.json"
    out.write_text("{}", encoding="utf-8")
    m.add_output(built, out)
    assert built["outputs"][0]["content_hash"] == m.hash_file(out)
    m.validate_manifest(built)


def test_require_publishable_rejects_a_dirty_tree() -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    built["code"] = {"entrypoint": "x.py", "git_commit": "abc123", "dirty": True}
    with pytest.raises(ValueError, match="not publishable"):
        m.require_publishable(built)


def test_require_publishable_rejects_an_unknown_commit() -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    built["code"] = {"entrypoint": "x.py", "git_commit": "unknown", "dirty": False}
    with pytest.raises(ValueError, match="not publishable"):
        m.require_publishable(built)


def test_require_publishable_accepts_a_clean_tree() -> None:
    built = m.build_manifest(name="x", hypothesis="none", entrypoint="x.py")
    built["code"] = {"entrypoint": "x.py", "git_commit": "abc123", "dirty": False}
    m.require_publishable(built)


def test_write_manifest_validates_before_writing(tmp_path) -> None:
    built = m.build_manifest(name="x", hypothesis="H9", entrypoint="x.py")
    with pytest.raises(ValidationError):
        m.write_manifest(built, directory=tmp_path)
    assert not list(tmp_path.iterdir()), "an invalid manifest must leave nothing behind"


def test_write_manifest_round_trips(tmp_path) -> None:
    built = m.build_manifest(name="x", hypothesis="H1", entrypoint="x.py")
    path = m.write_manifest(built, directory=tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["manifest_id"] == built["manifest_id"]
