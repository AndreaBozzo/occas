"""Shared test isolation.

The Article 21 exclusion list lives under ``data/``, which is gitignored, because
publishing it would announce which operators exercised a right. A consequence nobody
noticed until CI ran: a fresh checkout has no list, ``exclusions.load()`` fails closed as
designed, and any test that reached it failed — on the clone rather than on the machine
that wrote it.

The tests were the wrong place for that to surface. Reading the developer's real list is
not something a test should ever do: it makes the suite depend on local state, and it
would let a test pass or fail because of who had objected.
"""

from __future__ import annotations

import pytest

from analysis.common import exclusions


@pytest.fixture(autouse=True)
def isolated_exclusion_list(tmp_path_factory, monkeypatch):
    """Point every test at an empty exclusion list of its own.

    Empty rather than absent, because absence is the failure state the module exists to
    enforce — tests that want to see it pass an explicit path instead, which is what
    ``test_exclusions.py`` does.

    Deliberately *not* in ``tmp_path``: an autouse fixture that writes there pollutes
    every test's working directory, and one of them asserts an invalid manifest "leaves
    nothing behind". The first version of this fixture broke exactly that assertion.
    """
    path = tmp_path_factory.mktemp("exclusions") / "exclusions.jsonl"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr(exclusions, "EXCLUSIONS_PATH", path)
    return path
