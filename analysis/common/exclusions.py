"""The Article 21 exclusion list: who has objected, and what that excludes.

``PRIVACY.md`` promises that an objection is honoured by excluding that person's logs
"and added to a permanent exclusion list so that later runs do not re-include it". A
promise with no mechanism behind it is worse than no promise, so this is the mechanism.

**Fails closed.** A missing list is an error, not zero exclusions. The distinction
matters: "nobody has objected" and "I could not find out whether anyone objected" are
different states, and only the first is safe to process on. Declaring the first is
cheap -- an empty file -- so there is no reason to let absence mean it.

**The list is never committed.** It lives under ``data/``, which is gitignored, and it
stays there. Publishing it would announce which operators exercised a right, which is a
more revealing disclosure than the flight data the objection was about: it turns an
anonymous objection into a public act. What reaches a manifest instead is the *state* of
the list -- a digest and a count -- which is enough to say which exclusions were in force
for a run without saying whose.

That trade has a cost, and it is the honest one to name: a third party re-running the
pipeline cannot reproduce our exact excluded set. They get the digest and can see it
differs from theirs. Reproducibility of a suppression list and the privacy of the people
on it cannot both be complete, and between the two this project takes the side of the
people who objected.

Format -- one JSON object per line, ``data/exclusions.jsonl``::

    {"kind": "vehicle_uuid", "value": "...", "received": "2026-09-01"}
    {"kind": "log_id", "value": "...", "received": "2026-09-03"}

``received`` is the date the objection arrived, kept because Article 12(3) puts a
deadline on acting and a list with no dates cannot show it was met.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUSIONS_PATH = REPO_ROOT / "data" / "exclusions.jsonl"

KINDS = ("vehicle_uuid", "log_id")


class ExclusionListMissing(RuntimeError):
    """Raised when the exclusion list is absent.

    Absence is not emptiness. To declare that nobody has objected, create the file and
    leave it empty -- that is a statement, and it is auditable. A missing file is the
    absence of a statement, and processing on it would mean honouring objections only
    when someone remembered to check.
    """


class ExclusionListInvalid(ValueError):
    """Raised when a line cannot be understood.

    Also fatal, and for the same reason: a malformed entry is an objection this code
    cannot see, and skipping it silently would drop exactly the record whose whole
    purpose is not to be dropped.
    """


@dataclass(frozen=True)
class Exclusions:
    """The exclusion list as loaded, plus what a manifest is allowed to record."""

    vehicle_uuids: frozenset[str]
    log_ids: frozenset[str]
    digest: str
    path: Path
    latest_received: str | None

    @property
    def count(self) -> int:
        return len(self.vehicle_uuids) + len(self.log_ids)

    def excludes(self, *, log_id: str | None = None, vehicle_uuid: str | None = None) -> bool:
        """True if this run must be left out.

        Either identifier is sufficient. An objection naming a vehicle covers every log
        that vehicle produced, including ones uploaded after the objection -- which is
        what "later runs do not re-include it" has to mean to be worth promising.
        """
        if log_id is not None and log_id in self.log_ids:
            return True
        return vehicle_uuid is not None and vehicle_uuid in self.vehicle_uuids

    def state(self) -> dict[str, Any]:
        """The manifest block: which exclusions were in force, without saying whose."""
        return {
            "path": self.path.relative_to(REPO_ROOT).as_posix()
            if self.path.is_relative_to(REPO_ROOT)
            else self.path.as_posix(),
            "digest": self.digest,
            "count": self.count,
            "latest_received": self.latest_received,
        }


def load(path: Path | None = None) -> Exclusions:
    """Read the exclusion list. Raises rather than assuming an empty one.

    The default is resolved here rather than in the signature: a default argument binds
    at definition time, so ``EXCLUSIONS_PATH`` could not be redirected afterwards -- not
    by a test, and not by anything that needs to point at a different list. A gate whose
    target cannot be moved is a gate that cannot be shown to work.
    """
    path = EXCLUSIONS_PATH if path is None else path
    if not path.exists():
        raise ExclusionListMissing(
            f"{path} does not exist. Create it -- empty is fine, and means 'no objections "
            f"received' -- rather than letting a missing file mean the same thing silently. "
            f"See PRIVACY.md and docs/07-personal-data.md."
        )
    raw = path.read_bytes()
    # Hashed as bytes, before parsing: the digest identifies the file that was in force,
    # not our reading of it.
    digest = f"sha256:{hashlib.sha256(raw).hexdigest()}"

    vehicles: set[str] = set()
    logs: set[str] = set()
    received: list[str] = []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            raise ExclusionListInvalid(f"{path}:{number} is not JSON: {error}") from error
        kind, value = entry.get("kind"), entry.get("value")
        if kind not in KINDS or not isinstance(value, str) or not value:
            raise ExclusionListInvalid(
                f"{path}:{number} needs a 'kind' of {KINDS} and a non-empty 'value'; got "
                f"kind={kind!r}, value={value!r}"
            )
        (vehicles if kind == "vehicle_uuid" else logs).add(value)
        if isinstance(entry.get("received"), str):
            received.append(entry["received"])

    return Exclusions(
        vehicle_uuids=frozenset(vehicles),
        log_ids=frozenset(logs),
        digest=digest,
        path=path,
        latest_received=max(received) if received else None,
    )


def log_id_from(reference: str) -> str:
    """Normalise what an objector actually sends into a log id.

    ``PRIVACY.md`` invites "your ``vehicle_uuid``, a log id, or a link to your log",
    because asking a person exercising a right to look up an internal identifier is a way
    of making the right harder to use. So the link forms are accepted here rather than
    being someone's manual step later.
    """
    reference = reference.strip()
    if "/" not in reference and "?" not in reference:
        return reference
    # Both shapes the service uses: the CDN download URL and the review page's query.
    tail = reference.rsplit("/", 1)[-1]
    if "log_id=" in reference:
        tail = reference.split("log_id=", 1)[1].split("&", 1)[0]
    return tail.removesuffix(".ulg")
