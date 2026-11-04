"""Deterministic codename generation from adjective + noun word lists.

Codenames are always sampled through a seeded :class:`random.Random`
generator, so a fixed seed yields a fixed list — across runs, processes,
and machines. The word lists are small and curated so every generated name
reads as a plausible mission codename.

Phase 4 adds deterministic *schemes* beyond the adjective–noun grid:

- ``adjective_noun`` (default) — unique pairs sampled without replacement.
- ``alliterative`` — ADJ-NOUN pairs whose words share a starting letter.
- ``nato`` — NATO phonetic spelling of a base codename.
- ``numeric`` — ``PREFIX-HEX`` codes derived from a mission id.
- ``token`` — truncated SHA-256 hex tokens.
"""

from __future__ import annotations

import random
from itertools import product

from .ciphers import codename_token
from .randomness import derive_seed, make_rng

#: Adjective pool for codename generation (kept short and curated).
ADJECTIVES = (
    "SILENT",
    "CRIMSON",
    "VELVET",
    "IRON",
    "GOLDEN",
    "SHADOW",
    "CLEAR",
    "WILD",
    "POLAR",
    "BRAVE",
    "SUBTLE",
    "RAPID",
)

#: Noun pool for codename generation (kept short and curated).
NOUNS = (
    "JAGUAR",
    "FALCON",
    "BEACON",
    "RIVER",
    "LANTERN",
    "RAVEN",
    "SENTINEL",
    "ORACLE",
    "COMET",
    "HARBOR",
    "WOLVERINE",
    "HORIZON",
)

_MAX_PAIRS = len(ADJECTIVES) * len(NOUNS)

#: NATO phonetic code words, letter -> word (ICAO spelling).
NATO_ALPHABET: dict[str, str] = {
    "A": "ALFA",
    "B": "BRAVO",
    "C": "CHARLIE",
    "D": "DELTA",
    "E": "ECHO",
    "F": "FOXTROT",
    "G": "GOLF",
    "H": "HOTEL",
    "I": "INDIA",
    "J": "JULIETT",
    "K": "KILO",
    "L": "LIMA",
    "M": "MIKE",
    "N": "NOVEMBER",
    "O": "OSCAR",
    "P": "PAPA",
    "Q": "QUEBEC",
    "R": "ROMEO",
    "S": "SIERRA",
    "T": "TANGO",
    "U": "UNIFORM",
    "V": "VICTOR",
    "W": "WHISKEY",
    "X": "XRAY",
    "Y": "YANKEE",
    "Z": "ZULU",
}

#: Canonical codename schemes, used by reporting and manuscript variables.
CODENAME_SCHEMES = ("adjective_noun", "alliterative", "nato", "numeric", "token")


def _generate_adj_noun(count: int, seed: int | str | None, separator: str) -> list[str]:
    """Core adjective–noun sampler: unique pairs, no replacement."""
    pairs = list(product(ADJECTIVES, NOUNS))
    if not 1 <= count <= len(pairs):
        raise ValueError(f"count must be in [1, {len(pairs)}], got {count}")
    if not separator:
        raise ValueError("separator must not be empty")
    rng = make_rng(seed)
    return [f"{adj}{separator}{noun}" for adj, noun in rng.sample(pairs, count)]


def random_codename(rng: random.Random, separator: str = "-") -> str:
    """Sample one ``ADJ{separator}NOUN`` codename from ``rng``.

    Args:
        rng: A (preferably seeded) generator, e.g. from :func:`make_rng`.
        separator: Joiner between adjective and noun.

    Returns:
        A single uppercase codename.
    """
    if not separator:
        raise ValueError("separator must not be empty")
    return f"{rng.choice(ADJECTIVES)}{separator}{rng.choice(NOUNS)}"


def generate_codenames(
    count: int,
    seed: int | str | None = None,
    separator: str = "-",
    scheme: str = "adjective_noun",
) -> list[str]:
    """Generate ``count`` deterministic codenames under a named scheme.

    The default ``scheme="adjective_noun"`` samples unique pairs without
    replacement from the full adjective × noun product (backwards
    compatible with phase 1). See :func:`codenames_by_scheme` for the other
    schemes.

    Args:
        count: Number of codenames (``1 <= count <= 144`` for the default
            grid; ``>= 1`` for the other schemes).
        seed: Seed for the generator; ``None`` uses system entropy.
        separator: Joiner between adjective and noun (default scheme).
        scheme: One of :data:`CODENAME_SCHEMES`.

    Returns:
        A list of ``count`` codenames.

    Raises:
        ValueError: If ``count`` is out of range, ``separator`` is empty, or
            ``scheme`` is unknown.
    """
    if scheme == "adjective_noun":
        return _generate_adj_noun(count, seed, separator)
    return codenames_by_scheme(count, seed=seed, scheme=scheme, separator=separator)


def codename_for(name: str, seed: int | str | None = None) -> str:
    """Derive one stable codename for a mission ``name``.

    The name (and optional seed) is folded into a derived seed, so the same
    inputs always yield the same codename while different names diverge.

    Args:
        name: Mission or operator name.
        seed: Optional extra seed to namespace the derivation.

    Returns:
        A single uppercase codename.
    """
    combined = f"{seed}:{name}" if seed is not None else name
    rng = make_rng(derive_seed(combined))
    return random_codename(rng)


def nato_codename(text: str, separator: str = "-") -> str:
    """Spell ``text`` in NATO phonetic code words (letters) and digits.

    Letters map to their NATO code word; digits are emitted verbatim; any
    other character (space, hyphen, punctuation) is skipped.

    Args:
        text: Short identifier, e.g. ``"QB7"``.
        separator: Joiner between code words.

    Returns:
        E.g. ``nato_codename("QB7") == "QUEBEC-BRAVO-7"``.
    """
    words: list[str] = []
    for char in text.upper():
        if char in NATO_ALPHABET:
            words.append(NATO_ALPHABET[char])
        elif char.isdigit():
            words.append(char)
    return separator.join(words)


def numeric_codename(mission_id: str, seed: int | str, prefix: str = "QB") -> str:
    """Derive a deterministic numeric-styled codename for a mission.

    The code is an 8-hex-digit fold of the seeded mission id, giving a
    compact, sortable, collision-resistant identifier.

    Args:
        mission_id: Stable mission identifier.
        seed: Seed value (any int/str).
        prefix: Leading label (must be non-empty).

    Returns:
        ``"{prefix}-{CODE:08X}"``, e.g. ``"QB-1A2B3C4D"``.

    Raises:
        ValueError: If ``prefix`` is empty.
    """
    if not prefix:
        raise ValueError("prefix must not be empty")
    code = derive_seed(f"{seed}:{mission_id}")
    return f"{prefix}-{code:08X}"


def _alliterative_letters() -> list[str]:
    """Letters with at least one adjective AND one noun of that initial."""
    return [
        letter
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if any(adj.startswith(letter) for adj in ADJECTIVES) and any(noun.startswith(letter) for noun in NOUNS)
    ]


def _initial_pair(rng: random.Random, letter: str) -> tuple[str, str]:
    """Sample an adjective and a noun both starting with ``letter``."""
    adjectives = [adj for adj in ADJECTIVES if adj.startswith(letter)]
    nouns = [noun for noun in NOUNS if noun.startswith(letter)]
    if not adjectives or not nouns:
        raise ValueError(f"no alliterative pair available for letter {letter!r}")
    return rng.choice(adjectives), rng.choice(nouns)


def alliterative_codename(seed: int | str | None = None) -> str:
    """Sample one ADJ-NOUN codename whose words share a starting letter.

    Args:
        seed: Seed; ``None`` uses system entropy.

    Returns:
        A single uppercase alliterative codename.

    Raises:
        ValueError: If the word lists have no shared-initial letter pair
            (cannot happen with the bundled lists).
    """
    rng = make_rng(seed)
    letters = _alliterative_letters()
    if not letters:
        raise ValueError("no alliterative letter available in the word lists")
    letter = rng.choice(letters)
    adj, noun = _initial_pair(rng, letter)
    return f"{adj}-{noun}"


def codenames_by_scheme(
    count: int,
    seed: int | str | None = None,
    scheme: str = "adjective_noun",
    separator: str = "-",
) -> list[str]:
    """Generate ``count`` deterministic codenames under a named scheme.

    Schemes:

    - ``adjective_noun`` — unique pairs sampled without replacement.
    - ``alliterative`` — per-index seeded ADJ-NOUN pairs sharing an initial.
    - ``nato`` — NATO spelling of an adjective–noun base codename.
    - ``numeric`` — ``QB-XXXXXXXX`` codes derived from per-index mission ids.
    - ``token`` — 8-hex-char SHA-256 tokens from per-index mission ids.

    Args:
        count: Number of codenames (``>= 1``).
        seed: Seed; ``None`` uses system entropy.
        scheme: One of :data:`CODENAME_SCHEMES`.
        separator: Joiner for the ``adjective_noun`` and ``nato`` schemes.

    Returns:
        A list of ``count`` deterministic codenames.

    Raises:
        ValueError: If ``count`` is out of range, ``scheme`` is unknown, or
            the scheme's own constraints are violated.
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    base = seed if seed is not None else 0
    if scheme == "adjective_noun":
        return _generate_adj_noun(count, seed, separator)
    if scheme == "alliterative":
        return [alliterative_codename(derive_seed(f"{base}:{index}")) for index in range(count)]
    if scheme == "nato":
        return [nato_codename(codename_for(f"M-{index}", seed), separator) for index in range(count)]
    if scheme == "numeric":
        return [numeric_codename(f"M-{index}", base) for index in range(count)]
    if scheme == "token":
        return [codename_token(f"M-{index}", base, length=8) for index in range(count)]
    raise ValueError(f"unknown scheme {scheme!r}; known: {', '.join(CODENAME_SCHEMES)}")


__all__ = [
    "ADJECTIVES",
    "NOUNS",
    "NATO_ALPHABET",
    "CODENAME_SCHEMES",
    "random_codename",
    "generate_codenames",
    "codename_for",
    "nato_codename",
    "numeric_codename",
    "alliterative_codename",
    "codenames_by_scheme",
]
