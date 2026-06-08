# py-die-roller

A small, fast PRNG wrapper for Monte Carlo simulation and game development.
Defaults to PCG64 via NumPy's modern `Generator` interface with a
`SeedSequence`-based seeding strategy.

## Installation

```bash
# Base install (PCG64, Philox, SFC64)
pip install git+https://github.com/username/py-die-roller.git

# With Xoshiro256 support
pip install "git+https://github.com/username/py-die-roller.git#egg=py-die-roller[extended]"
```

## Usage

```python
from dieroller import RNG

# Seeded from OS entropy
rng = RNG()

# Reproducible
rng = RNG(seed=42)

# Choose algorithm
rng = RNG(algorithm="philox")   # good for parallel Monte Carlo
rng = RNG(algorithm="sfc64")    # fastest, good for game dev
rng = RNG(algorithm="xoshiro256")  # requires extended install

# Generate values via the underlying numpy Generator
rng.gen.random()                # float in [0, 1)
rng.gen.integers(0, 100)        # random int
rng.gen.standard_normal()       # gaussian sample

# Reseed in place
rng.reseed()                    # fresh OS entropy
rng.reseed(seed=99)             # known seed

# Spawn independent, non-overlapping streams (e.g. for parallel work)
workers = rng.spawn(8)
results = [w.gen.random(1000) for w in workers]
```

## Algorithms

| Name         | Period    | Notes                                  |
|--------------|-----------|----------------------------------------|
| `pcg64`      | 2¹²⁸      | Default. Best all-round quality.       |
| `philox`     | 2¹²⁸      | Counter-based. Ideal for parallel MC.  |
| `sfc64`      | ~2¹⁶⁴     | Fastest. Good for game dev.            |
| `xoshiro256` | 2²⁵⁶ − 1 | Requires `extended` install.           |

## Requirements

- Python >= 3.8
- NumPy >= 1.17
- `randomgen` >= 1.23 (optional, for Xoshiro256)
