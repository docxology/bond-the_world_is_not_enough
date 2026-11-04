"""JSON/YAML mission-record persistence with schema validation.

Mission records are the provenance-outcome envelope that bond-api outcomes
will persist: every record carries a canonical ``input_hash`` (SHA-256 over
the sorted-JSON inputs), the schema ``version`` that produced it, and the
``seed`` used for any randomness — so a record can always be reproduced
from its persisted inputs.

Formats: JSON (default) and YAML, inferred from the file suffix when not
explicitly selected.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .randomness import derive_seed

#: Version of the mission-record schema this module writes.
MISSION_SCHEMA_VERSION = "1.0"

#: Required keys and their expected types for a valid mission record.
MISSION_SCHEMA: dict[str, type] = {
    "mission_id": str,
    "codename": str,
    "seed": int,
    "version": str,
    "started_at": str,
    "parameters": dict,
}

#: Optional keys that, when present, must be mappings.
OPTIONAL_KEYS = ("outcomes", "provenance")


class MissionValidationError(ValueError):
    """Raised when a mission record fails schema validation."""


def hash_payload(payload: dict) -> str:
    """Return the SHA-256 hex digest of ``payload`` under canonical JSON.

    Canonicalization is ``sort_keys`` with compact separators, so the hash
    is stable across key orderings and formatting choices.

    Args:
        payload: Any JSON-serializable mapping.

    Returns:
        A 64-character lowercase hex digest.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_record(record: dict) -> dict:
    """Validate ``record`` against :data:`MISSION_SCHEMA`; return it unchanged.

    Every required key must be present with the expected type, and optional
    mapping keys must be mappings when present.

    Args:
        record: The record mapping to validate.

    Returns:
        The same mapping, untouched.

    Raises:
        MissionValidationError: With a message listing every failing key.
    """
    if not isinstance(record, dict):
        raise MissionValidationError("record must be a mapping")
    problems: list[str] = []
    for key, expected in MISSION_SCHEMA.items():
        if key not in record:
            problems.append(f"missing required key {key!r}")
        elif not isinstance(record[key], expected):
            problems.append(f"key {key!r} must be {expected.__name__}, got {type(record[key]).__name__}")
    for key in OPTIONAL_KEYS:
        if key in record and not isinstance(record[key], dict):
            problems.append(f"key {key!r} must be a mapping")
    if problems:
        raise MissionValidationError("; ".join(problems))
    return record


def save_record(record: dict, path: str | Path, fmt: str | None = None) -> Path:
    """Validate and write ``record`` as JSON (default) or YAML.

    ``fmt`` is inferred from the ``.yaml``/``.yml``/``.json`` suffix when
    omitted. Parent directories are created as needed.

    Args:
        record: The record mapping (validated before writing).
        path: Destination file path.
        fmt: Explicit format: ``"json"``, ``"yaml"``, or ``"yml"``.

    Returns:
        The resolved path that was written.

    Raises:
        MissionValidationError: If the record is invalid.
        ValueError: If ``fmt`` is unsupported.
    """
    validate_record(record)
    target = Path(path)
    resolved_fmt = (fmt or target.suffix.lstrip(".") or "json").lower()
    target.parent.mkdir(parents=True, exist_ok=True)
    if resolved_fmt in ("yaml", "yml"):
        with target.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(record, handle, sort_keys=False)
    elif resolved_fmt == "json":
        with target.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
    else:
        raise ValueError(f"unsupported record format {resolved_fmt!r}")
    return target.resolve()


def load_record(path: str | Path) -> dict:
    """Load and validate a mission record, inferring format from the suffix.

    Args:
        path: File path with a ``.json``, ``.yaml``, or ``.yml`` suffix.

    Returns:
        The validated record mapping.

    Raises:
        MissionValidationError: If the file content violates the schema.
        ValueError: If the suffix is unsupported or the content is malformed.
        FileNotFoundError: If the file does not exist.
    """
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix in (".yaml", ".yml"):
        with target.open("r", encoding="utf-8") as handle:
            content = yaml.safe_load(handle)
    elif suffix == ".json":
        with target.open("r", encoding="utf-8") as handle:
            content = json.load(handle)
    else:
        raise ValueError(f"unsupported record suffix {suffix!r}")
    return validate_record(content)


def record_provenance_outcome(
    mission_id: str,
    seed: int | str,
    version: str,
    input_payload: dict,
    outcome: dict,
    path: str | Path,
    fmt: str | None = None,
    codename: str | None = None,
    started_at: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Persist a provenance-outcome mission record and return it.

    This is the persistence helper bond-api outcomes will call: it bundles
    the canonical ``input_hash`` (via :func:`hash_payload`), the schema
    ``version``, and the derived ``seed`` into ``provenance``, stores the
    supplied ``outcome`` under ``outcomes``, and writes the record to
    ``path``.

    Args:
        mission_id: Stable mission identifier.
        seed: Seed used by the producing run (stored derived, see
            :func:`derive_seed`).
        version: Package/schema version of the producing run.
        input_payload: Inputs consumed by the run; hashed into provenance.
        outcome: Measured outcome mapping to persist.
        path: Destination file.
        fmt: ``"json"`` (default) or ``"yaml"``.
        codename: Optional codename; defaults to ``mission_id``.
        started_at: ISO timestamp; defaults to ``now`` (UTC).
        now: Clock override, for deterministic tests.

    Returns:
        The full record dict that was written to ``path``.
    """
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    derived_seed = derive_seed(seed)
    record = {
        "mission_id": mission_id,
        "codename": codename or mission_id,
        "seed": derived_seed,
        "version": version,
        "started_at": started_at or stamp,
        "parameters": dict(input_payload),
        "outcomes": dict(outcome),
        "provenance": {
            "input_hash": hash_payload(input_payload),
            "schema_version": MISSION_SCHEMA_VERSION,
            "seed": derived_seed,
        },
    }
    save_record(record, path, fmt)
    return record


_RECORD_SUFFIXES = (".json", ".yaml", ".yml")


def verify_provenance(record: dict) -> bool:
    """Return True when a record's provenance is internally consistent.

    Recomputes the canonical hash of ``record["parameters"]`` and compares it
    with ``provenance["input_hash"]``, checks the provenance seed matches the
    record seed, and confirms the schema version. Records without a full
    provenance block return False.

    Args:
        record: A mission record mapping.

    Returns:
        True iff the stored provenance is reproducible from the parameters.
    """
    try:
        validate_record(record)
        provenance = record.get("provenance")
        if not isinstance(provenance, dict):
            return False
        if provenance.get("input_hash") != hash_payload(record["parameters"]):
            return False
        if provenance.get("seed") != record["seed"]:
            return False
        return provenance.get("schema_version") == MISSION_SCHEMA_VERSION
    except MissionValidationError:
        return False


def load_records(directory: str | Path) -> list[dict]:
    """Load and validate every mission-record file in ``directory``.

    Files are processed in sorted path order for deterministic output;
    unsupported suffixes are ignored. A malformed or schema-invalid file
    raises, wrapped with the offending filename.

    Args:
        directory: Directory to scan for ``.json`` / ``.yaml`` / ``.yml``.

    Returns:
        The validated record mappings, in sorted filename order.

    Raises:
        MissionValidationError: If a record file is malformed or invalid
            (message includes the filename).
    """
    root = Path(directory)
    records: list[dict] = []
    for path in sorted(root.iterdir()):
        if path.suffix.lower() in _RECORD_SUFFIXES and path.is_file():
            try:
                records.append(load_record(path))
            except (MissionValidationError, ValueError) as exc:
                raise MissionValidationError(f"{path.name}: {exc}") from exc
    return records


def record_summary(record: dict) -> dict:
    """Return a flat, deterministic summary of a mission record.

    Args:
        record: A valid mission record mapping.

    Returns:
        A summary dict with mission id, codename, seed, version, started_at,
        sorted outcome keys, and the provenance input hash (or None).

    Raises:
        MissionValidationError: If the record is invalid.
    """
    validate_record(record)
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    return {
        "mission_id": record["mission_id"],
        "codename": record["codename"],
        "seed": record["seed"],
        "version": record["version"],
        "started_at": record["started_at"],
        "outcome_keys": sorted(record.get("outcomes", {}).keys()),
        "input_hash": provenance.get("input_hash"),
    }


def append_outcome(record_path: str | Path, outcome_update: dict, fmt: str | None = None) -> dict:
    """Merge ``outcome_update`` into an existing record's outcomes and save.

    Provenance (input hash, seed, schema version) is preserved untouched;
    only ``outcomes`` is extended.

    A record that carries no ``outcomes`` key yet (the key is optional under
    :data:`MISSION_SCHEMA`) starts from an empty mapping rather than raising.

    Args:
        record_path: Path to an existing mission record file.
        outcome_update: Mapping merged into ``record["outcomes"]``.
        fmt: Override format; defaults to suffix inference.

    Returns:
        The updated record mapping (already persisted).

    Raises:
        MissionValidationError / ValueError / FileNotFoundError: Per
            :func:`load_record` / :func:`save_record`.
    """
    record = load_record(record_path)
    existing = record.get("outcomes")
    outcomes = dict(existing) if isinstance(existing, dict) else {}
    outcomes.update(outcome_update)
    record["outcomes"] = outcomes
    save_record(record, record_path, fmt=fmt)
    return record


__all__ = [
    "MISSION_SCHEMA_VERSION",
    "MISSION_SCHEMA",
    "OPTIONAL_KEYS",
    "MissionValidationError",
    "hash_payload",
    "validate_record",
    "save_record",
    "load_record",
    "load_records",
    "record_provenance_outcome",
    "record_summary",
    "append_outcome",
    "verify_provenance",
]
