"""
Dice roll-code parser and executor.

Exports :class:`Dice`, which parses standard dice notation strings and
executes them using :class:`~dieroller.rng.RNG` for random number generation.

Supported roll notation (used with :meth:`Dice.roll`)::

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

Supported pool notation (used with :meth:`Dice.pool`)::

    NdS              — roll N dice with S sides; return list of results
    NdS+M            — roll N dice, add M to each result
    NdS-M            — roll N dice, subtract M from each result
    NdStT            — roll N dice, return count of results >= T
    NdS+MtT          — per-die modifier then success threshold
    N1dS+M+N2dS-MtT  — compound pool with mixed per-die modifiers and threshold
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Union

from .rng import RNG

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_LEADING_COUNT_RE = re.compile(r'^(\d+)')
_SEGMENT_RE = re.compile(r'd(f|\d+)(k[hl]\d*)?', re.IGNORECASE)
_ALL_MODIFIERS_RE = re.compile(r'[+-]\d+')

_POOL_THRESHOLD_RE = re.compile(r't(\d+)$', re.IGNORECASE)
# Negative lookahead (?!d) prevents consuming the leading count of the next
# sub-pool (e.g. "+4" in "+4d6") as a per-die modifier.
_SUB_POOL_RE = re.compile(r'(\d+)d(\d+)([+-]\d+(?!d))?', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _Segment:
    sides: int          # number of sides; ignored when fate=True
    keep: Optional[str] = None  # e.g. 'kh', 'kh3', 'kl', 'kl2', or None
    fate: bool = False  # True for fate/fudge dice (dF/df)


@dataclass
class _SubPool:
    """One component of a compound die pool."""

    count: int
    """Number of dice to roll."""

    sides: int
    """Number of sides on each die."""

    per_die_modifier: int = 0
    """Flat value added to every individual die result before success comparison."""


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
# Pool parsing and helpers
# ---------------------------------------------------------------------------

def _parse_pool(code: str):
    """
    Parse a pool notation string into sub-pools and an optional success threshold.

    Pool notation supports one or more sub-pools joined together, each of the
    form ``NdS`` with an optional per-die modifier ``+M`` or ``-M``, followed
    by an optional success threshold ``tT`` at the very end.

    The per-die modifier is distinguished from a sub-pool boundary by a
    negative lookahead: ``+4`` is treated as the start of a new sub-pool
    ``4dS`` when it is immediately followed by ``d``, and as a per-die
    modifier otherwise.

    :param code: A pool notation string such as ``'12d6'``, ``'4d6t4'``,
        ``'12d6+1t4'``, or ``'8d10+2+4d10-1t5'``.
    :type code: str
    :returns: A ``(sub_pools, threshold)`` tuple where *sub_pools* is a list
        of :class:`_SubPool` instances and *threshold* is an ``int`` if a
        ``tT`` specifier was present, otherwise ``None``.
    :rtype: tuple[list[_SubPool], int or None]
    :raises ValueError: If no die expression is found in *code*, or if any
        die has non-positive sides.
    """
    code = code.strip()

    # Strip optional success threshold from the end before parsing dice
    threshold = None
    m = _POOL_THRESHOLD_RE.search(code)
    if m:
        threshold = int(m.group(1))
        code = code[:m.start()]

    sub_pools = []
    for m in _SUB_POOL_RE.finditer(code):
        count = int(m.group(1))
        sides = int(m.group(2))
        if sides <= 0:
            raise ValueError(f"Die sides must be positive, got {sides}")
        per_die_mod = int(m.group(3)) if m.group(3) else 0
        sub_pools.append(_SubPool(count=count, sides=sides, per_die_modifier=per_die_mod))

    if not sub_pools:
        raise ValueError(f"No die pool expression found in '{code}'")

    return sub_pools, threshold


def _count_successes(results: List[int], threshold: int) -> int:
    """
    Count the number of results that meet or exceed *threshold*.

    A result is a success when ``result >= threshold``.

    :param results: Individual die results from a pool roll, after any
        per-die modifiers have been applied.
    :type results: list[int]
    :param threshold: Minimum value (inclusive) required for a die to count
        as a success.
    :type threshold: int
    :returns: Number of values in *results* that are >= *threshold*.
    :rtype: int
    """
    return sum(1 for r in results if r >= threshold)


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

        # Pool rolls — individual results
        d.pool('12d6')             # list of 12 integers in [1, 6]
        d.pool('4d6+1')            # list of 4 integers in [2, 7]

        # Pool rolls — success counting
        d.pool('4d6t4')            # int: count of dice >= 4
        d.pool('12d6+1t4')         # int: each die in [2, 7], count >= 4
        d.pool('8d6+4d6+1t4')      # compound pool: 8d6 plain + 4d6 with +1
        d.pool('8d10+2+4d10-1t5')  # compound pool with mixed per-die modifiers

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

    def _roll_sub_pool(self, sub_pool: _SubPool) -> List[int]:
        """
        Roll the dice in a single :class:`_SubPool` and return individual results.

        Each die is rolled uniformly on ``[1, sub_pool.sides]`` and then
        ``sub_pool.per_die_modifier`` is added. No clamping is applied, so
        results may fall outside the native die range when a modifier is present.

        :param sub_pool: The sub-pool descriptor to roll.
        :type sub_pool: _SubPool
        :returns: A list of *sub_pool.count* integers, each being the raw die
            value plus *sub_pool.per_die_modifier*.
        :rtype: list[int]
        """
        return [
            self._rng.nextint(1, sub_pool.sides) + sub_pool.per_die_modifier
            for _ in range(sub_pool.count)
        ]

    def pool(self, code: str) -> Union[List[int], int]:
        """
        Roll a die pool and return raw results or a success count.

        Pool rolls differ from :meth:`roll` in that dice are **not** summed —
        each result is kept individually. An optional per-die modifier shifts
        every result before any threshold comparison. A success threshold (``tT``
        suffix) triggers success counting instead of returning the raw list.

        Compound pools (e.g. ``'8d6+4d6+1t4'``) are formed by concatenating
        sub-pools; each sub-pool may carry its own per-die modifier.

        Supported notation::

            NdS              — roll N dice, return list of results
            NdS+M            — add M to each result
            NdS-M            — subtract M from each result
            NdStT            — roll N dice, return count of results >= T
            NdS+MtT          — per-die modifier, then success threshold
            N1dS+M+N2dS-MtT  — compound pool with mixed modifiers

        :param code: A pool notation string.
        :type code: str
        :returns: A ``list[int]`` of individual die results when no threshold
            is given, or an ``int`` success count when a threshold is present.
        :rtype: list[int] or int
        :raises ValueError: If *code* cannot be parsed.
        """
        sub_pools, threshold = _parse_pool(code)
        results: List[int] = []
        for sp in sub_pools:
            results.extend(self._roll_sub_pool(sp))
        if threshold is None:
            return results
        return _count_successes(results, threshold)

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
