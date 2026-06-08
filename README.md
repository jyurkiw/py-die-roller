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

# Raw 64-bit unsigned integer (next value in the PRNG sequence)
next(rng)                       # e.g. 13831296847929757231

# Random integer with inclusive bounds
rng.nextint(1, 6)               # d6 roll: value in [1, 6]
rng.nextint(1, 20)              # d20 roll: value in [1, 20]
rng.nextint()                   # full uint64 range [0, 2**64 - 1]

# Random float in [0.0, 1.0] inclusive
rng.nextfloat()                 # e.g. 0.7502661

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

## Running the tests

Install the package and pytest, then run the suite:

```bash
uv pip install .
uv pip install pytest
pytest tests
```

**Important:** `uv pip install .` must be re-run every time you make changes to
the library code, since the package is installed from source. Forgetting this
means pytest will test the previously installed version, not your latest edits.

To avoid running the install step manually each time, consider automating it —
for example with a `Makefile` target, a shell alias, or a pre-test hook in your
editor or CI configuration.

## Requirements

- Python >= 3.8
- NumPy >= 1.17
- `randomgen` >= 1.23 (optional, for Xoshiro256)
