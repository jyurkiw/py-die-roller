"""
py-die-roller — fast PRNG wrapper for Monte Carlo simulation and game development.

Primary exports:

- :class:`~dieroller.rng.RNG` — seeded generator with spawn support.
- :data:`~dieroller.rng.ALGORITHMS` — registry of available bit-generators.
- :class:`~dieroller.table.table` — rollable lookup table with sub-table support.
"""

from .rng import RNG, ALGORITHMS
from .dice import Dice
from .table import table

__all__ = ["RNG", "ALGORITHMS", "Dice", "table"]
__version__ = "0.1.0"
