"""Classic cipher primitives and cryptanalysis helpers (Q-BRANCH).

Every cipher here is an educational utility with a hard round-trip
guarantee: ``decrypt(encrypt(x)) == x`` for every supported input (or, for
the digraph cipher, against its prepared form). Cryptographic strength is
explicitly out of scope — the suite uses these for deterministic test
vectors, obfuscation, and teaching classic cryptography, never for real
secrecy.

Ciphers:

- :func:`caesar_encrypt` / :func:`caesar_decrypt` — classic shift cipher,
  letters only, case preserved, non-letters pass through untouched.
- :func:`vigenere_encrypt` / :func:`vigenere_decrypt` — polyalphabetic
  cipher; the key advances only over letters.
- :func:`xor_bytes` — symmetric byte-wise XOR with a cyclically repeated key.
- :func:`one_time_pad` — XOR with a key at least as long as the data.
- :func:`generate_otp_key` — deterministic random key material from a seed.
- :func:`obfuscate_codename` / :func:`restore_codename` — letter+digit shift
  helper for codenames; :func:`codename_token` derives a stable token.
- :func:`atbash` — reverse-alphabet substitution, self-inverse.
- :func:`beaufort_encrypt` / :func:`beaufort_decrypt` — reciprocal keyword
  cipher ``c = (k - p) mod 26`` (self-inverse).
- :func:`rail_fence_encrypt` / :func:`rail_fence_decrypt` — zig-zag
  transposition over ``rails`` rows.
- :func:`playfair_encrypt` / :func:`playfair_decrypt` — digraph substitution
  on a 5x5 keyed square (I/J merged).
- :func:`columnar_encrypt` / :func:`columnar_decrypt` — columnar
  transposition with a digit key.

Cryptanalysis helpers:

- :func:`letter_frequency`, :func:`frequency_normalized` — A-Z counts and
  relative frequencies.
- :func:`index_of_coincidence` — Friedman's IC (~0.066 English, ~0.038
  random).
- :func:`english_chi_squared` — chi-squared fit against English.
- :func:`caesar_shift_scores` / :func:`caesar_break` — scored brute force
  over all 26 shifts.
- :func:`kasiski_key_lengths` — repeated n-gram distance voting.
- :func:`vigenere_break` — recover a keyword of known length.
"""

from __future__ import annotations

import hashlib

from .randomness import derive_seed, seeded_bytes

#: Canonical cipher names, used by reporting and manuscript variables.
CIPHER_NAMES = (
    "caesar",
    "vigenere",
    "one_time_pad",
    "xor",
    "atbash",
    "beaufort",
    "rail_fence",
    "playfair",
    "columnar",
)

#: One-line descriptions per cipher, used by reporting and manuscripts.
CIPHER_DESCRIPTIONS: dict[str, str] = {
    "caesar": "shift cipher, letters only",
    "vigenere": "polyalphabetic keyword cipher",
    "one_time_pad": "XOR with a key at least as long as the data",
    "xor": "symmetric byte-wise XOR with a cyclic key",
    "atbash": "reverse-alphabet substitution (self-inverse)",
    "beaufort": "reciprocal keyword cipher c = (k - p)",
    "rail_fence": "zig-zag row transposition",
    "playfair": "digraph substitution on a 5x5 keyed square",
    "columnar": "column-order transposition with a digit key",
}

#: Cryptanalysis helper names, used by reporting and manuscript variables.
CRYPTANALYSIS_HELPERS = (
    "letter_frequency",
    "frequency_normalized",
    "index_of_coincidence",
    "english_chi_squared",
    "caesar_shift_scores",
    "caesar_break",
    "kasiski_key_lengths",
    "vigenere_break",
)

#: Standard English relative letter frequencies (a..z), summing to 1.0.
ENGLISH_FREQUENCIES: dict[str, float] = {
    "a": 0.08167,
    "b": 0.01492,
    "c": 0.02782,
    "d": 0.04253,
    "e": 0.12702,
    "f": 0.02228,
    "g": 0.02015,
    "h": 0.06094,
    "i": 0.06966,
    "j": 0.00153,
    "k": 0.00772,
    "l": 0.04025,
    "m": 0.02406,
    "n": 0.06749,
    "o": 0.07507,
    "p": 0.01929,
    "q": 0.00095,
    "r": 0.05987,
    "s": 0.06327,
    "t": 0.09056,
    "u": 0.02758,
    "v": 0.00978,
    "w": 0.02360,
    "x": 0.00150,
    "y": 0.01974,
    "z": 0.00074,
}

_ALPHABET_SIZE = 26
_DIGIT_SIZE = 10


def _is_letter(char: str) -> bool:
    """True for an ASCII ``A-Z`` / ``a-z`` letter (the cipher alphabet).

    The whole module's "letter" semantics are deliberately ASCII-only:
    :meth:`str.isalpha` also accepts non-ASCII alphabetic characters (e.g.
    ``é``, ``ñ``, Cyrillic, CJK), and treating those as cipher letters would
    both corrupt them in the ciphers and crash the A-Z counting helpers
    (:func:`letter_frequency` and the cryptanalysis built on it) with a
    ``KeyError``. Routing every check through this helper fixes that class:
    a non-ASCII letter is a *non-letter* -- passed through unchanged by the
    ciphers and ignored by frequency/IC/chi-squared counting.
    """
    return ("A" <= char <= "Z") or ("a" <= char <= "z")


def _shift_letter(char: str, shift: int) -> str:
    """Shift one ASCII letter by ``shift`` positions, preserving case."""
    if not _is_letter(char):
        return char
    base = ord("a") if char.islower() else ord("A")
    return chr(base + (ord(char) - base + shift) % _ALPHABET_SIZE)


def caesar_encrypt(text: str, shift: int) -> str:
    """Encrypt ``text`` with a Caesar shift (letters only, case preserved).

    Args:
        text: Plaintext (any characters; non-letters pass through).
        shift: Number of positions to shift; any integer is valid.

    Returns:
        The shifted ciphertext.
    """
    return "".join(_shift_letter(char, shift) for char in text)


def caesar_decrypt(text: str, shift: int) -> str:
    """Invert :func:`caesar_encrypt` for the same ``shift``."""
    return caesar_encrypt(text, -shift)


def _vigenere(text: str, key: str, encrypt: bool) -> str:
    """Shared Vigenère engine; only letters advance the key position."""
    if not key:
        raise ValueError("vigenere key must not be empty")
    if not all(_is_letter(c) for c in key):
        raise ValueError("vigenere key must contain only letters")
    out: list[str] = []
    key_index = 0
    direction = 1 if encrypt else -1
    for char in text:
        if not _is_letter(char):
            out.append(char)
            continue
        shift = direction * (ord(key[key_index % len(key)].lower()) - ord("a"))
        out.append(_shift_letter(char, shift))
        key_index += 1
    return "".join(out)


def vigenere_encrypt(text: str, key: str) -> str:
    """Encrypt ``text`` with the Vigenère cipher.

    Args:
        text: Plaintext; non-letters pass through without advancing the key.
        key: Non-empty alphabetic keyword.

    Returns:
        The ciphertext.
    """
    return _vigenere(text, key, True)


def vigenere_decrypt(text: str, key: str) -> str:
    """Invert :func:`vigenere_encrypt` for the same ``key``."""
    return _vigenere(text, key, False)


def xor_bytes(data: bytes, key: bytes) -> bytes:
    """Byte-wise XOR of ``data`` with a cyclically repeated ``key``.

    Symmetric: ``xor_bytes(xor_bytes(data, key), key) == data``.

    Args:
        data: Payload bytes.
        key: Key bytes; must be non-empty.

    Returns:
        The XORed bytes, same length as ``data``.

    Raises:
        ValueError: If ``key`` is empty.
    """
    if not key:
        raise ValueError("xor key must not be empty")
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def one_time_pad(data: bytes, key: bytes) -> bytes:
    """Apply a one-time pad: XOR ``data`` with a key at least as long.

    Only the first ``len(data)`` key bytes are consumed. Symmetric:
    ``one_time_pad(one_time_pad(data, key), key) == data``.

    Args:
        data: Payload bytes.
        key: Key bytes with ``len(key) >= len(data)``.

    Returns:
        The ciphertext bytes, same length as ``data``.

    Raises:
        ValueError: If the key is shorter than the data.
    """
    if len(key) < len(data):
        raise ValueError(f"one-time-pad key must be at least {len(data)} bytes, got {len(key)}")
    return bytes(a ^ b for a, b in zip(data, key))


def generate_otp_key(length: int, seed: int | str) -> bytes:
    """Generate a deterministic random key of ``length`` bytes from ``seed``.

    Delegates to :func:`randomness.seeded_bytes` — the canonical byte source
    of the suite — so OTP keys and any other byte draws are reproducible
    from the same seed through one path.

    Args:
        length: Key length in bytes (>= 1).
        seed: Seed; strings are hashed via :func:`derive_seed`.

    Returns:
        Deterministic key bytes, reproducible for the same seed.

    Raises:
        ValueError: If ``length`` is less than 1.
    """
    return seeded_bytes(seed, length)


def obfuscate_codename(codename: str, shift: int) -> str:
    """Shift letters and digits of ``codename`` by ``shift`` positions.

    Non-alphanumeric characters (spaces, hyphens) pass through unchanged, so
    hyphenated codenames keep their shape. Digits use a 10-position cycle.

    Args:
        codename: The codename to obfuscate.
        shift: Shift amount; any integer is valid.

    Returns:
        The obfuscated codename.
    """
    out: list[str] = []
    for char in codename:
        if _is_letter(char):
            base = ord("a") if char.islower() else ord("A")
            out.append(chr(base + (ord(char) - base + shift) % _ALPHABET_SIZE))
        elif char.isdigit():
            out.append(chr(ord("0") + (ord(char) - ord("0") + shift) % _DIGIT_SIZE))
        else:
            out.append(char)
    return "".join(out)


def restore_codename(codename: str, shift: int) -> str:
    """Invert :func:`obfuscate_codename` for the same ``shift``."""
    return obfuscate_codename(codename, -shift)


def codename_token(name: str, seed: int | str, length: int = 6) -> str:
    """Derive a stable uppercase hex token for a codename.

    The token is a truncated SHA-256 digest over the derived seed and the
    name, so it is deterministic across runs and processes.

    Args:
        name: Codename or mission name.
        seed: Seed; strings are hashed via :func:`derive_seed`.
        length: Token length in hex characters (>= 1).

    Returns:
        Uppercase hex token of ``length`` characters.

    Raises:
        ValueError: If ``length`` is less than 1.
    """
    if length < 1:
        raise ValueError("token length must be >= 1")
    digest = hashlib.sha256(f"{derive_seed(seed)}:{name}".encode("utf-8")).hexdigest()
    return digest[:length].upper()


# --------------------------------------------------------------------------
# New classical ciphers (phase 4)
# --------------------------------------------------------------------------


def atbash(text: str) -> str:
    """Apply the Atbash reverse-alphabet substitution.

    ``A <-> Z``, ``B <-> Y``, ... with case preserved; non-letters pass
    through. The cipher is self-inverse: ``atbash(atbash(x)) == x``.

    Args:
        text: Plaintext (any characters).

    Returns:
        The substituted text.
    """
    out: list[str] = []
    for char in text:
        if _is_letter(char):
            base = ord("a") if char.islower() else ord("A")
            out.append(chr(base + (_ALPHABET_SIZE - 1) - (ord(char) - base)))
        else:
            out.append(char)
    return "".join(out)


def _beaufort(text: str, key: str) -> str:
    """Shared Beaufort engine: ``c = (k - p) mod 26``; letters only."""
    if not key:
        raise ValueError("beaufort key must not be empty")
    if not all(_is_letter(c) for c in key):
        raise ValueError("beaufort key must contain only letters")
    out: list[str] = []
    key_index = 0
    for char in text:
        if not _is_letter(char):
            out.append(char)
            continue
        key_shift = ord(key[key_index % len(key)].lower()) - ord("a")
        base = ord("a") if char.islower() else ord("A")
        out.append(chr(base + (key_shift - (ord(char) - base)) % _ALPHABET_SIZE))
        key_index += 1
    return "".join(out)


def beaufort_encrypt(text: str, key: str) -> str:
    """Encrypt ``text`` with the Beaufort cipher.

    The Beaufort cipher is reciprocal: encryption and decryption are the
    same operation (``c = (k - p)`` and ``p = (k - c)``), so
    ``beaufort_decrypt`` is an alias of :func:`beaufort_encrypt`.

    Args:
        text: Plaintext; non-letters pass through without advancing the key.
        key: Non-empty alphabetic keyword.

    Returns:
        The ciphertext.
    """
    return _beaufort(text, key)


def beaufort_decrypt(text: str, key: str) -> str:
    """Invert :func:`beaufort_encrypt` for the same ``key`` (same operation)."""
    return _beaufort(text, key)


def _rail_pattern(length: int, rails: int) -> list[int]:
    """Rail index per position in zig-zag order ``0..rails-1..0``."""
    if rails < 2:
        raise ValueError("rail fence requires rails >= 2")
    cycle = 2 * (rails - 1)
    return [min(position % cycle, cycle - position % cycle) for position in range(length)]


def rail_fence_encrypt(text: str, rails: int) -> str:
    """Encrypt ``text`` with the rail-fence transposition.

    Args:
        text: Plaintext (any characters, positions preserved).
        rails: Number of zig-zag rows (>= 2).

    Returns:
        The ciphertext (a permutation of ``text``).

    Raises:
        ValueError: If ``rails`` is less than 2.
    """
    pattern = _rail_pattern(len(text), rails)
    rows: list[list[str]] = [[] for _ in range(rails)]
    for char, rail in zip(text, pattern):
        rows[rail].append(char)
    return "".join("".join(row) for row in rows)


def rail_fence_decrypt(text: str, rails: int) -> str:
    """Invert :func:`rail_fence_encrypt` for the same ``rails``."""
    pattern = _rail_pattern(len(text), rails)
    row_counts = [pattern.count(rail) for rail in range(rails)]
    slices: list[str] = []
    offset = 0
    for count in row_counts:
        slices.append(text[offset : offset + count])
        offset += count
    pointers = [0] * rails
    out: list[str] = []
    for rail in pattern:
        out.append(slices[rail][pointers[rail]])
        pointers[rail] += 1
    return "".join(out)


def _playfair_square(key: str) -> list[list[str]]:
    """Build the 5x5 keyed Playfair square (I/J merged)."""
    if not key:
        raise ValueError("playfair key must not be empty")
    square: list[str] = []
    for char in (key + "ABCDEFGHIKLMNOPQRSTUVWXYZ").upper():
        if char == "J":
            char = "I"
        if _is_letter(char) and char not in square:
            square.append(char)
    return [square[offset : offset + 5] for offset in range(0, 25, 5)]


def _playfair_positions(square: list[list[str]]) -> dict[str, tuple[int, int]]:
    """Map each letter to its ``(row, column)`` in the square."""
    return {square[row][col]: (row, col) for row in range(5) for col in range(5)}


def _playfair_prepare(text: str) -> str:
    """Normalize plaintext: uppercase, J->I, drop non-letters, split doubles.

    Repeated adjacent letters are split with an inserted ``X`` and an odd
    final letter is padded with ``X``, so the output is always even-length.
    """
    cleaned = "".join("I" if char == "J" else char for char in text.upper() if _is_letter(char))
    prepared: list[str] = []
    index = 0
    while index < len(cleaned):
        first = cleaned[index]
        if index + 1 < len(cleaned) and cleaned[index + 1] == first:
            prepared.extend([first, "X"])
            index += 1
        elif index + 1 < len(cleaned):
            prepared.extend([first, cleaned[index + 1]])
            index += 2
        else:
            prepared.extend([first, "X"])
            index += 1
    return "".join(prepared)


def _playfair_transform(
    digraph: str,
    square: list[list[str]],
    positions: dict[str, tuple[int, int]],
    encrypt: bool,
) -> str:
    """Apply the Playfair rule to one digraph (same row / same column / rectangle)."""
    (row1, col1), (row2, col2) = positions[digraph[0]], positions[digraph[1]]
    step = 1 if encrypt else -1
    if row1 == row2:
        return square[row1][(col1 + step) % 5] + square[row2][(col2 + step) % 5]
    if col1 == col2:
        return square[(row1 + step) % 5][col1] + square[(row2 + step) % 5][col2]
    return square[row1][col2] + square[row2][col1]


def playfair_encrypt(text: str, key: str) -> str:
    """Encrypt ``text`` with the classic Playfair digraph cipher.

    The plaintext is normalized via :func:`_playfair_prepare` (uppercase,
    J->I, non-letters dropped, doubles split with ``X``, odd tail padded),
    then each digraph is transformed on the 5x5 keyed square.

    Args:
        text: Plaintext (any characters; only letters are enciphered).
        key: Non-empty keyword used to build the keyed square.

    Returns:
        The ciphertext (letters only, uppercase).
    """
    square = _playfair_square(key)
    positions = _playfair_positions(square)
    prepared = _playfair_prepare(text)
    out: list[str] = []
    for index in range(0, len(prepared), 2):
        out.append(_playfair_transform(prepared[index : index + 2], square, positions, True))
    return "".join(out)


def playfair_decrypt(text: str, key: str) -> str:
    """Invert :func:`playfair_encrypt` for the same ``key``.

    Returns the *prepared* plaintext (uppercase letters, with inserted
    ``X`` split/pad characters), which is the exact inverse of the digraph
    transformation.

    Args:
        text: Ciphertext (letters only, uppercase).
        key: The keyword used for encryption.

    Returns:
        The prepared plaintext.

    Raises:
        ValueError: If the ciphertext length (letters only) is odd, or the
            key is empty.
    """
    square = _playfair_square(key)
    positions = _playfair_positions(square)
    cleaned = "".join(char for char in text.upper() if _is_letter(char))
    if len(cleaned) % 2 != 0:
        raise ValueError("playfair ciphertext length must be even")
    out: list[str] = []
    for index in range(0, len(cleaned), 2):
        out.append(_playfair_transform(cleaned[index : index + 2], square, positions, False))
    return "".join(out)


def _columnar_key_order(key: str) -> list[int]:
    """Column reading order from a digit key, stable on duplicate digits."""
    if not key:
        raise ValueError("columnar key must not be empty")
    if not key.isdigit():
        raise ValueError("columnar key must contain only digits")
    pairs = sorted((char, index) for index, char in enumerate(key))
    return [index for _, index in pairs]


def columnar_encrypt(text: str, key: str) -> str:
    """Encrypt ``text`` with columnar transposition.

    The text is laid into rows of ``len(key)`` columns (the final row may be
    short) and columns are read in the order given by the digit ``key``.
    Round-trips exactly — no padding characters are introduced.

    Args:
        text: Plaintext (any characters).
        key: Non-empty digit key, e.g. ``"3142"``.

    Returns:
        The ciphertext (a permutation of ``text``).

    Raises:
        ValueError: If ``key`` is empty or not digits-only.
    """
    if not text:
        return ""
    order = _columnar_key_order(key)
    columns = len(key)
    rows = (len(text) + columns - 1) // columns
    last_len = len(text) - (rows - 1) * columns
    out: list[str] = []
    for col in order:
        count = rows - 1 + (1 if col < last_len else 0)
        for row in range(count):
            out.append(text[row * columns + col])
    return "".join(out)


def columnar_decrypt(text: str, key: str) -> str:
    """Invert :func:`columnar_encrypt` for the same ``key``."""
    if not text:
        return ""
    order = _columnar_key_order(key)
    columns = len(key)
    rows = (len(text) + columns - 1) // columns
    last_len = len(text) - (rows - 1) * columns
    row_counts = [rows - 1 + (1 if col < last_len else 0) for col in range(columns)]
    grid: list[list[str | None]] = [[None] * columns for _ in range(rows)]
    pointer = 0
    for col in order:
        for row in range(row_counts[col]):
            grid[row][col] = text[pointer]
            pointer += 1
    return "".join(cell for row in grid for cell in row if cell is not None)


# --------------------------------------------------------------------------
# Cryptanalysis helpers (phase 4)
# --------------------------------------------------------------------------


def letter_frequency(text: str) -> dict[str, int]:
    """Count A-Z letters in ``text`` (case-insensitive); non-letters ignored.

    Args:
        text: Any text.

    Returns:
        A dict of 26 lowercase letters to integer counts (all letters present,
        zero-filled).
    """
    counts = {chr(code): 0 for code in range(ord("a"), ord("z") + 1)}
    for char in text:
        if _is_letter(char):
            counts[char.lower()] += 1
    return counts


def frequency_normalized(text: str) -> dict[str, float]:
    """Return relative letter frequencies (count / total letters).

    Args:
        text: Any text.

    Returns:
        A dict of 26 lowercase letters to relative frequencies; all zeros
        when the text contains no letters.
    """
    counts = letter_frequency(text)
    total = sum(counts.values())
    if total == 0:
        return {letter: 0.0 for letter in counts}
    return {letter: count / total for letter, count in counts.items()}


def index_of_coincidence(text: str) -> float:
    """Return Friedman's index of coincidence for ``text``.

    Roughly 0.066 for natural English and 0.038 for uniform random text;
    a value close to English suggests a monoalphabetic substitution.

    Args:
        text: Any text (letters only are counted).

    Returns:
        The IC in ``[0, 1]``; ``0.0`` for fewer than two letters.
    """
    counts = letter_frequency(text)
    total = sum(counts.values())
    if total < 2:
        return 0.0
    numerator = sum(count * (count - 1) for count in counts.values())
    return numerator / (total * (total - 1))


def english_chi_squared(text: str) -> float:
    """Return the chi-squared fit of ``text`` against English frequencies.

    Lower values indicate a better fit; the shift minimizing this score is
    the recovered Caesar key.

    Args:
        text: Any text.

    Returns:
        A non-negative score; ``0.0`` when the text has no letters.
    """
    counts = letter_frequency(text)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    chi: float = 0.0
    for letter, expected in ENGLISH_FREQUENCIES.items():
        expected_count = expected * total
        delta = counts[letter] - expected_count
        chi += (delta * delta) / expected_count
    return chi


def caesar_shift_scores(text: str) -> list[tuple[int, float]]:
    """Score every Caesar shift (0..25) for ``text``; best (lowest) first.

    Args:
        text: Ciphertext.

    Returns:
        A list of ``(shift, chi_squared)`` pairs sorted ascending by score.
    """
    scores = [(shift, english_chi_squared(caesar_decrypt(text, shift))) for shift in range(_ALPHABET_SIZE)]
    return sorted(scores, key=lambda item: item[1])


def caesar_break(text: str) -> tuple[int, str]:
    """Recover a Caesar shift via chi-squared scoring.

    Args:
        text: Ciphertext containing at least one letter.

    Returns:
        The ``(best_shift, best_plaintext)`` pair.

    Raises:
        ValueError: If the text contains no letters.
    """
    if not any(_is_letter(char) for char in text):
        raise ValueError("caesar_break requires at least one letter")
    shift, _ = caesar_shift_scores(text)[0]
    return shift, caesar_decrypt(text, shift)


def kasiski_key_lengths(text: str, max_length: int = 10, min_run: int = 3) -> list[int]:
    """Vote on candidate Vigenère key lengths via repeated n-gram distances.

    Repeated runs of ``min_run`` letters are located; the distance between
    occurrences is factored, and each factor in ``[2, max_length]`` receives
    a vote. Lengths are returned most-voted first, ties broken ascending.

    Args:
        text: Ciphertext.
        max_length: Largest key length to consider (>= 2).
        min_run: Repeated-run length (>= 1).

    Returns:
        Candidate key lengths, deterministic; empty when the text is too
        short to contain repeats.

    Raises:
        ValueError: If ``max_length`` is less than 2.
    """
    if max_length < 2:
        raise ValueError("max_length must be >= 2")
    cleaned = "".join(char for char in text.upper() if _is_letter(char))
    if len(cleaned) < min_run * 2:
        return []
    distances: list[int] = []
    for start in range(len(cleaned) - min_run):
        ngram = cleaned[start : start + min_run]
        next_pos = cleaned.find(ngram, start + min_run)
        if next_pos != -1:
            distances.append(next_pos - start)
    votes: dict[int, int] = {}
    for distance in distances:
        for factor in range(2, max_length + 1):
            if distance % factor == 0:
                votes[factor] = votes.get(factor, 0) + 1
    ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
    return [length for length, _ in ranked]


def _vigenere_columns(text: str, key_length: int) -> list[str]:
    """Split letter-only uppercase text into ``key_length`` Caesar columns."""
    cleaned = "".join(char for char in text.upper() if _is_letter(char))
    return [cleaned[index::key_length] for index in range(key_length)]


def vigenere_break(text: str, key_length: int) -> tuple[str, str]:
    """Recover a Vigenère keyword of known length and decrypt.

    Each key column is broken independently with :func:`caesar_break`, and
    the recovered columns are re-interleaved into reading order.

    Args:
        text: Ciphertext.
        key_length: The keyword length (>= 1).

    Returns:
        The ``(key, plaintext)`` pair; the key is uppercase letters and the
        plaintext is uppercase letters only.

    Raises:
        ValueError: If ``key_length`` is less than 1.
    """
    if key_length < 1:
        raise ValueError("key_length must be >= 1")
    columns = _vigenere_columns(text, key_length)
    key_chars: list[str] = []
    plaintext_columns: list[str] = []
    for column in columns:
        shift, plain = caesar_break(column)
        key_chars.append(chr(ord("A") + shift))
        plaintext_columns.append(plain)
    max_len = max(len(column) for column in plaintext_columns)
    plaintext = "".join(
        plaintext_columns[col][row]
        for row in range(max_len)
        for col in range(key_length)
        if row < len(plaintext_columns[col])
    )
    return "".join(key_chars), plaintext


__all__ = [
    "CIPHER_NAMES",
    "CIPHER_DESCRIPTIONS",
    "CRYPTANALYSIS_HELPERS",
    "ENGLISH_FREQUENCIES",
    "caesar_encrypt",
    "caesar_decrypt",
    "vigenere_encrypt",
    "vigenere_decrypt",
    "xor_bytes",
    "one_time_pad",
    "generate_otp_key",
    "obfuscate_codename",
    "restore_codename",
    "codename_token",
    "atbash",
    "beaufort_encrypt",
    "beaufort_decrypt",
    "rail_fence_encrypt",
    "rail_fence_decrypt",
    "playfair_encrypt",
    "playfair_decrypt",
    "columnar_encrypt",
    "columnar_decrypt",
    "letter_frequency",
    "frequency_normalized",
    "index_of_coincidence",
    "english_chi_squared",
    "caesar_shift_scores",
    "caesar_break",
    "kasiski_key_lengths",
    "vigenere_break",
]
