"""
Low-level PRNG wrapper built on :mod:`numpy.random.Generator`.

Exports :class:`RNG` and the :data:`ALGORITHMS` registry.
"""

import os
import numpy as np
from numpy.random import Generator, PCG64, Philox, SFC64, SeedSequence

_UINT64_MAX = 2**64 - 1

ALGORITHMS = {
    "pcg64":  PCG64,
    "philox": Philox,
    "sfc64":  SFC64,
}
"""
Mapping of algorithm name to its bit-generator class.

Built-in entries:

- ``"pcg64"``  — :class:`numpy.random.PCG64` (default)
- ``"philox"`` — :class:`numpy.random.Philox`
- ``"sfc64"``  — :class:`numpy.random.SFC64`

``"xoshiro256"`` is added automatically when the optional ``randomgen``
package is installed.
"""

try:
    from randomgen import Xoshiro256
    ALGORITHMS["xoshiro256"] = Xoshiro256
except ImportError:
    pass


class RNG:
    """
    A thin wrapper around :class:`numpy.random.Generator` with a consistent
    seeding strategy and support for spawning independent child streams.

    Defaults to PCG64. Xoshiro256 is available when the optional ``randomgen``
    package is installed (``pip install py-die-roller[extended]``).

    :param seed: Integer seed for reproducible results. ``None`` seeds from
        OS entropy.
    :type seed: int or None
    :param algorithm: Bit-generator algorithm to use. One of ``"pcg64"``
        (default), ``"philox"``, ``"sfc64"``, or ``"xoshiro256"`` (requires
        ``randomgen``).
    :type algorithm: str
    :raises ValueError: If *algorithm* is not in :data:`ALGORITHMS`.

    Usage::

        rng = RNG()                    # seeded from OS entropy
        rng = RNG(seed=42)             # reproducible
        rng = RNG(algorithm="sfc64")   # fastest; good for game dev

        value = rng.gen.random()       # float in [0, 1)
        roll  = rng.gen.integers(1, 7) # d6 result
    """

    def __init__(self, seed=None, algorithm="pcg64"):
        if algorithm not in ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Available: {list(ALGORITHMS)}"
            )

        self._algo = ALGORITHMS[algorithm]
        self._ss   = SeedSequence(seed if seed is not None else int.from_bytes(os.urandom(32), "big"))
        self.gen   = Generator(self._algo(self._ss))

    def reseed(self, seed=None):
        """
        Reseed the generator in place.

        :param seed: New seed. ``None`` pulls fresh entropy from the OS.
        :type seed: int or None
        """
        self._ss = SeedSequence(seed if seed is not None else int.from_bytes(os.urandom(32), "big"))
        self.gen = Generator(self._algo(self._ss))

    def __next__(self):
        """
        Return the next raw 64-bit unsigned integer from the bit-generator.

        Implements the iterator protocol so :class:`RNG` instances can be
        used with :func:`next` or consumed directly in loops.

        :returns: A 64-bit unsigned integer drawn from the underlying
            bit-generator's raw output stream.
        :rtype: int
        """
        return int(self.gen.bit_generator.random_raw())

    def nextint(self, min=0, max=_UINT64_MAX):
        """
        Return a random integer in the closed interval [*min*, *max*].

        Both bounds are **inclusive**, so ``nextint(1, 6)`` produces a
        fair d6 roll.  The default range covers the full unsigned 64-bit
        space (0 to 2\\ :sup:`64` − 1).

        :param min: Lower bound (inclusive). Defaults to ``0``.
        :type min: int
        :param max: Upper bound (inclusive). Defaults to ``2**64 - 1``.
        :type max: int
        :returns: A random integer *n* such that ``min <= n <= max``.
        :rtype: int
        :raises ValueError: If *min* is greater than *max*.
        """
        if min > max:
            raise ValueError(f"min ({min}) must be <= max ({max})")
        return int(self.gen.integers(min, max, endpoint=True, dtype=np.uint64))

    def nextfloat(self):
        """
        Return a random float in the closed interval [0.0, 1.0].

        Computed as ``nextint() / (2**64 - 1)``, mapping the full unsigned
        64-bit range onto [0.0, 1.0] with both endpoints reachable.

        :returns: A float *f* such that ``0.0 <= f <= 1.0``.
        :rtype: float
        """
        return self.nextint() / _UINT64_MAX

    def spawn(self, n):
        """
        Return *n* independent :class:`RNG` instances derived from this one.

        Each child is guaranteed a non-overlapping stream via
        :meth:`numpy.random.SeedSequence.spawn`. All children use the same
        bit-generator algorithm as the parent.

        :param n: Number of independent child generators to create.
        :type n: int
        :returns: List of *n* independent :class:`RNG` instances.
        :rtype: list[RNG]
        """
        return [RNG._from_ss(s, self._algo) for s in self._ss.spawn(n)]

    @classmethod
    def _from_ss(cls, ss, algo):
        """Construct an RNG directly from an existing SeedSequence (internal)."""
        obj       = object.__new__(cls)
        obj._algo = algo
        obj._ss   = ss
        obj.gen   = Generator(algo(ss))
        return obj

    def __repr__(self):
        return (
            f"RNG(algorithm='{self._algo.__name__.lower()}', "
            f"entropy={self._ss.entropy})"
        )
