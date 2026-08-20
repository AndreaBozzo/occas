"""Load the JSON Schemas and validate records against them.

Schemas cross-reference each other by relative filename (``$ref: source_metadata.json``)
and each carries an absolute ``$id``. The reference resolves against that ``$id`` as
its base URI, so registering every schema under its ``$id`` is what makes cross-schema
references work; the filename on disk is only how ``validator_for`` finds the file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


def schema_paths() -> list[Path]:
    return sorted(SCHEMA_DIR.glob("*.json"))


def load(schema_name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def registry() -> Registry:
    reg: Registry = Registry()
    for path in schema_paths():
        contents = json.loads(path.read_text(encoding="utf-8"))
        identifier = contents.get("$id")
        if not identifier:
            raise ValueError(f"{path.name} has no $id, so nothing can reference it")
        reg = reg.with_resource(
            identifier, Resource.from_contents(contents, default_specification=DRAFT202012)
        )
    return reg


@cache
def validator_for(schema_name: str) -> Draft202012Validator:
    """Return a validator for a schema, by filename (e.g. ``run.json``)."""
    schema = load(schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=registry())


def validate(record: Mapping[str, Any], schema_name: str) -> None:
    """Raise ``jsonschema.ValidationError`` if ``record`` does not satisfy the schema."""
    validator_for(schema_name).validate(dict(record))
