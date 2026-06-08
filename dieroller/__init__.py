"""
py-die-roller — fast PRNG wrapper for Monte Carlo simulation and game development.

Primary exports:

- :class:`~dieroller.rng.RNG` — seeded generator with spawn support.
- :data:`~dieroller.rng.ALGORITHMS` — registry of available bit-generators.
"""

from .rng import RNG, ALGORITHMS

__all__ = ["RNG", "ALGORITHMS"]
__version__ = "0.1.0"
