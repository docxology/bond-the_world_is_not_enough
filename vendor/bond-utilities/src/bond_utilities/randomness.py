"""Seeded randomness primitives for reproducible mission operations.

Every random draw in the bond suite flows through :func:`make_rng` or the
:func:`seeded` decorator so experiments, codenames, and cipher keys are
byte-for-byte reproducible from a single seed value.

The module is deterministic by construction: the same ``seed`` input always
yields the same generator state, independent of process, platform, or call
order (``random.Random`` is a pure-Python Mersenne Twister).
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable, Sequence
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

_MASK32 = 0xFFFFFFFF

#: Names of the seeded draw helpers, in declaration order. Used by reporting
#: and manuscript variables; ``tests/test_randomness.py`` binds this registry
#: to the module's real callables so it cannot silently drift.
SEEDED_HELPERS = (
    "seeded_bytes",
    "seeded_int",
    "seeded_float",
    "seeded_choice",
    "seeded_choices",
    "seeded_shuffle",
    "seeded_sample",
)


def derive_seed(seed: int | str) -> int:
    """Return a stable, non-negative integer seed usable by ``random.Random``.

    Integers are folded to 32 bits; strings are hashed with SHA-256 and the
    first 32 bits of the digest are used. Both paths are deterministic and
    documented so persisted provenance seeds can be replayed exactly.

    Args:
        seed: Any integer or string identifier.

    Returns:
        A deterministic integer in ``[0, 2**32)``.
    """
    if isinstance(seed, int):
        return seed & _MASK32
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def make_rng(seed: int | str | None = None) -> random.Random:
    """Return a fresh :class:`random.Random` generator.

    With a numeric or string ``seed`` the generator is fully reproducible;
    with ``None`` it is seeded from system entropy (use only where
    reproducibility is not required, e.g. one-off throwaway draws).

    Args:
        seed: Optional seed; strings are hashed via :func:`derive_seed`.

    Returns:
        A new, independent generator instance.
    """
    if seed is None:
        return random.Random()
    return random.Random(derive_seed(seed))


def seeded(seed: int | str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that runs ``func`` with the global ``random`` module seeded.

    The previous global RNG state is restored after the call, so decorated
    functions are deterministic in isolation without perturbing callers.

    Args:
        seed: Seed value passed through :func:`derive_seed`.

    Returns:
        A decorator wrapping the decorated function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = random.getstate()
            random.seed(derive_seed(seed))
            try:
                return func(*args, **kwargs)
            finally:
                random.setstate(state)

        return wrapper

    return decorator


def seeded_bytes(seed: int | str, length: int) -> bytes:
    """Return ``length`` deterministic random bytes derived from ``seed``.

    This is the canonical byte source for the suite: cipher key material
    (``ciphers.generate_otp_key`` delegates here) and any other byte draws
    stay reproducible for the same seed.

    Args:
        seed: Seed; strings are hashed via :func:`derive_seed`.
        length: Number of bytes (>= 1).

    Returns:
        Deterministic bytes, reproducible for the same seed.

    Raises:
        ValueError: If ``length`` is less than 1.
    """
    if length < 1:
        raise ValueError("byte length must be >= 1")
    rng = make_rng(seed)
    return bytes(rng.randrange(256) for _ in range(length))


def seeded_int(seed: int | str, lo: int = 0, hi: int = 2**32) -> int:
    """Return a deterministic integer in ``[lo, hi)`` from ``seed``.

    Args:
        seed: Seed value.
        lo: Inclusive lower bound.
        hi: Exclusive upper bound.

    Returns:
        A reproducible integer in ``[lo, hi)``.

    Raises:
        ValueError: If ``lo >= hi``.
    """
    if lo >= hi:
        raise ValueError("seeded_int requires lo < hi")
    return make_rng(seed).randrange(lo, hi)


def seeded_float(seed: int | str, lo: float = 0.0, hi: float = 1.0) -> float:
    """Return a deterministic float in ``[lo, hi)`` from ``seed``.

    Args:
        seed: Seed value.
        lo: Inclusive lower bound.
        hi: Exclusive upper bound.

    Returns:
        A reproducible float in ``[lo, hi)``.

    Raises:
        ValueError: If ``lo > hi``.
    """
    if lo > hi:
        raise ValueError("seeded_float requires lo <= hi")
    return make_rng(seed).uniform(lo, hi)


def seeded_choice(seed: int | str, items: Sequence[Any]) -> Any:
    """Return one deterministic element from ``items``.

    Args:
        seed: Seed value.
        items: Non-empty sequence of candidates.

    Returns:
        A reproducible element of ``items``.

    Raises:
        ValueError: If ``items`` is empty.
    """
    if not items:
        raise ValueError("seeded_choice requires a non-empty sequence")
    return make_rng(seed).choice(items)


def seeded_choices(seed: int | str, items: Sequence[Any], k: int) -> list[Any]:
    """Return ``k`` deterministic elements from ``items`` (with replacement).

    Args:
        seed: Seed value.
        items: Non-empty sequence of candidates.
        k: Number of draws (>= 0).

    Returns:
        A reproducible list of ``k`` draws.

    Raises:
        ValueError: If ``items`` is empty or ``k`` is negative.
    """
    if not items:
        raise ValueError("seeded_choices requires a non-empty sequence")
    if k < 0:
        raise ValueError("seeded_choices requires k >= 0")
    return make_rng(seed).choices(items, k=k)


def seeded_shuffle(seed: int | str, items: Sequence[Any]) -> list[Any]:
    """Return a deterministic permutation of ``items`` (input is not mutated).

    Args:
        seed: Seed value.
        items: Sequence to permute.

    Returns:
        A new list containing the shuffled elements.
    """
    shuffled = list(items)
    make_rng(seed).shuffle(shuffled)
    return shuffled


def seeded_sample(seed: int | str, items: Sequence[Any], k: int) -> list[Any]:
    """Return ``k`` deterministic elements from ``items`` (without replacement).

    Args:
        seed: Seed value.
        items: Sequence of candidates.
        k: Sample size; must satisfy ``0 <= k <= len(items)``.

    Returns:
        A reproducible list of ``k`` distinct elements.

    Raises:
        ValueError: If ``k`` is out of range (delegated to ``random.sample``).
    """
    return make_rng(seed).sample(items, k)


__all__ = [
    "SEEDED_HELPERS",
    "derive_seed",
    "make_rng",
    "seeded",
    "seeded_bytes",
    "seeded_int",
    "seeded_float",
    "seeded_choice",
    "seeded_choices",
    "seeded_shuffle",
    "seeded_sample",
]
