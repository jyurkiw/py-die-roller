"""
Dice roll-code parser and executor.

Exports :class:`Dice`, which parses standard dice notation strings and
executes them using :class:`~dieroller.rng.RNG` for random number generation.

Supported notation::

    XdY            — roll X dice with Y sides, sum all
    XdY+Z          — roll and add flat modifier
    XdY-Z          — roll and subtract flat modifier
    XdY+Z1+Z2      — multiple flat modifiers, all summed
    XdYkh          — keep highest 1
    XdYkhN         — keep highest N
    XdYkl          — keep lowest 1
    XdYklN         — keep lowest N
    XdYdZ          — chain: roll XdY, use sum as count for dZ
    4d3d12kh4d7+9  — full chained example
    Xdf            — fate/fudge dice: each die produces -1, 0, or 1
    4df+3+2+2+2    — 4 fate dice with multiple stacked modifiers
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .rng import RNG

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_LEADING_COUNT_RE = re.compile(r'^(\d+)')
_SEGMENT_RE = re.compile(r'd(f|\d+)(k[hl]\d*)?', re.IGNORECASE)
_ALL_MODIFIERS_RE = re.compile(r'[+-]\d+')


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _Segment:
    sides: int          # number of sides; ignored when fate=True
    keep: Optional[str] = None  # e.g. 'kh', 'kh3', 'kl', 'kl2', or None
    fate: bool = False  # True for fate/fudge dice (dF/df)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse(code: str):
    """
    Parse a dice notation string into its components.

    :param code: A dice notation string such as ``'5d6kh3+2'`` or ``'4df+3+2'``.
    :type code: str
    :returns: A ``(segments, initial_count, modifier)`` tuple where *segments*
        is a list of :class:`_Segment`, *initial_count* is the number of dice
        for the first roll, and *modifier* is the sum of all flat modifiers.
    :rtype: tuple[list[_Segment], int, int]
    :raises ValueError: If *code* contains no ``d`` expression, uses
        non-positive sides, or has an invalid keep specifier.
    """
    code = code.strip()

    # 1. Optional leading count
    initial_count = 1
    pos = 0
    m = _LEADING_COUNT_RE.match(code)
    if m:
        initial_count = int(m.group(1))
        pos = m.end()

    if initial_count <= 0:
        raise ValueError(f"Initial die count must be positive, got {initial_count}")

    # 2. One _Segment per 'd<sides|f>[keep]' match
    segments = []
    last_end = pos
    for m in _SEGMENT_RE.finditer(code, pos):
        face_str = m.group(1).lower()
        fate = (face_str == 'f')
        if fate:
            sides = 0
        else:
            sides = int(face_str)
            if sides <= 0:
                raise ValueError(f"Die sides must be positive, got {sides}")
        keep = (m.group(2) or '').lower() or None
        segments.append(_Segment(sides=sides, keep=keep, fate=fate))
        last_end = m.end()

    if not segments:
        raise ValueError(f"No die expression found in '{code}'")

    # 3. Sum all flat modifiers that appear after the last segment
    modifier_str = code[last_end:]
    modifier = sum(int(x) for x in _ALL_MODIFIERS_RE.findall(modifier_str))

    return segments, initial_count, modifier


# ---------------------------------------------------------------------------
# Keep logic
# ---------------------------------------------------------------------------

def _apply_keep(rolls: List[int], keep_spec: Optional[str]) -> List[int]:
    """
    Filter *rolls* according to a keep specifier.

    :param rolls: The list of rolled values.
    :param keep_spec: A keep specifier such as ``'kh'``, ``'kh3'``, ``'kl2'``,
        or ``None`` to keep all rolls.
    :returns: The filtered list of kept values.
    :raises ValueError: If the keep count exceeds the number of rolls.
    """
    if keep_spec is None:
        return rolls

    mode = keep_spec[:2]          # 'kh' or 'kl'
    n_str = keep_spec[2:]
    n = int(n_str) if n_str else 1

    if n > len(rolls):
        raise ValueError(
            f"Cannot keep {n} dice from a pool of {len(rolls)}"
        )

    return sorted(rolls, reverse=(mode == 'kh'))[:n]


# ---------------------------------------------------------------------------
# Dice class
# ---------------------------------------------------------------------------

class Dice:
    """
    Parses and executes dice notation strings using a :class:`~dieroller.rng.RNG`
    instance for random number generation.

    :param seed: Integer seed for reproducible results. ``None`` seeds from
        OS entropy.
    :type seed: int or None
    :param algorithm: Bit-generator algorithm passed to :class:`~dieroller.rng.RNG`.
        One of ``'pcg64'`` (default), ``'philox'``, ``'sfc64'``, or
        ``'xoshiro256'``.
    :type algorithm: str

    Usage::

        d = Dice()
        d.roll('1d6+2')        # random d6, add 2
        d.roll('5d6kh3+2')     # roll 5d6, keep highest 3, add 2
        d.roll('3d20kl+7')     # roll 3d20, keep lowest, add 7
        d.roll('4df')          # 4 fate dice, result in [-4, 4]
        d.roll('4df+3+2+2+2')  # fate dice with stacked modifiers, result in [5, 13]

        # Reproducible
        d = Dice(seed=42)

        # Parallel independent streams
        workers = d.spawn(8)
        results = [w.roll('3d6') for w in workers]
    """

    def __init__(self, seed=None, algorithm="pcg64"):
        self._rng = RNG(seed=seed, algorithm=algorithm)

    def roll(self, code: str) -> int:
        """
        Parse and execute a dice notation string.

        Chained segments (e.g. ``'4d3d12kh4d7+9'``) are resolved iteratively:
        the sum of each segment's kept values becomes the die count for the
        next segment. All flat modifiers are summed and added to the final total.

        Fate/fudge dice (``df``) each produce -1, 0, or 1 with equal probability.

        :param code: A dice notation string such as ``'5d6kh3+2'``,
            ``'4d3d12kh4d7+9'``, or ``'4df+3+2+2+2'``.
        :type code: str
        :returns: The total result of the roll.
        :rtype: int
        :raises ValueError: If *code* cannot be parsed or a keep count exceeds
            the number of dice in its pool.
        """
        segments, count, modifier = _parse(code)
        for seg in segments:
            if seg.fate:
                rolls = [self._rng.nextint(0, 2) - 1 for _ in range(count)]
            else:
                rolls = [self._rng.nextint(1, seg.sides) for _ in range(count)]
            kept = _apply_keep(rolls, seg.keep)
            count = sum(kept)
        return count + modifier

    def spawn(self, n: int) -> "List[Dice]":
        """
        Return *n* independent :class:`Dice` instances derived from this one.

        Each child uses a non-overlapping RNG stream via
        :meth:`~dieroller.rng.RNG.spawn`, making them safe for parallel work
        across threads or processes.

        :param n: Number of independent child instances to create.
        :type n: int
        :returns: A list of *n* :class:`Dice` instances with independent streams.
        :rtype: list[Dice]
        """
        children = []
        for rng in self._rng.spawn(n):
            child = Dice.__new__(Dice)
            child._rng = rng
            children.append(child)
        return children

    def __repr__(self):
        return f"Dice({self._rng!r})"
