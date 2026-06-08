import os
from numpy.random import Generator, PCG64, Philox, SFC64, SeedSequence

ALGORITHMS = {
    "pcg64":  PCG64,
    "philox": Philox,
    "sfc64":  SFC64,
}

try:
    from randomgen import Xoshiro256
    ALGORITHMS["xoshiro256"] = Xoshiro256
except ImportError:
    pass


class RNG:
    """
    A thin wrapper around numpy.random.Generator with a consistent seeding
    strategy and support for spawning independent streams.

    Defaults to PCG64. Xoshiro256 is available if the optional `randomgen`
    package is installed.

    Parameters
    ----------
    seed : int, optional
        Integer seed for reproducible results. If None, seeds from OS entropy.
    algorithm : str, optional
        One of 'pcg64' (default), 'philox', 'sfc64', 'xoshiro256'.
    """

    def __init__(self, seed=None, algorithm="pcg64"):
        if algorithm not in ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Available: {list(ALGORITHMS)}"
            )

        self._algo = ALGORITHMS[algorithm]
        self._ss   = SeedSequence(seed or int.from_bytes(os.urandom(32), "big"))
        self.gen   = Generator(self._algo(self._ss))

    def reseed(self, seed=None):
        """
        Reseed the generator in place.

        Parameters
        ----------
        seed : int, optional
            New seed. If None, pulls fresh entropy from the OS.
        """
        self._ss = SeedSequence(seed or int.from_bytes(os.urandom(32), "big"))
        self.gen = Generator(self._algo(self._ss))

    def spawn(self, n):
        """
        Return n independent RNG instances derived from this one.

        Each child is guaranteed a non-overlapping stream via SeedSequence.spawn.
        All children use the same algorithm as the parent.

        Parameters
        ----------
        n : int
            Number of independent child generators to create.

        Returns
        -------
        list[RNG]
        """
        return [RNG._from_ss(s, self._algo) for s in self._ss.spawn(n)]

    @classmethod
    def _from_ss(cls, ss, algo):
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
