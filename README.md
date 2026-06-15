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

## Dice notation

```python
from dieroller import Dice

d = Dice()           # seeded from OS entropy
d = Dice(seed=42)    # reproducible

# Roll notation — dice are summed
d.roll('3d6')         # roll 3d6, return total
d.roll('1d20+5')      # roll 1d20, add 5
d.roll('4d6kh3')      # roll 4d6, keep highest 3
d.roll('3d20kl+7')    # roll 3d20, keep lowest, add 7
d.roll('4df+3')       # 4 fate dice (+3 modifier), result in [-1, 7]
d.roll('4d3d12kh4+9') # chained: roll 4d3, use sum as count for d12kh4, add 9

# Pool notation — individual die results are kept separately
d.pool('12d6')              # list of 12 integers in [1, 6]
d.pool('4d6+1')             # list of 4 integers in [2, 7] (per-die +1)

# Pool with success threshold — returns a count of dice >= threshold
d.pool('4d6t4')             # e.g. [2, 4, 4, 6] → 3 successes
d.pool('12d6+1t4')          # per-die +1, then count results >= 4
d.pool('8d6+4d6+1t4')       # compound: 8d6 plain + 4d6 with per-die +1
d.pool('8d10+2+4d10-1t5')   # compound with mixed per-die modifiers

# Exploding rolls — re-roll and add when a die meets the threshold
d.roll('3d6e')              # explode on max (6); result can exceed 18
d.roll('3d6e5')             # explode on 5 or higher
d.roll('3d6e!')             # cascade: exploded dice can also explode
d.roll('3d6e5!')            # cascade explode on 5+
d.roll('4d6e!+3d8e7!')      # per-segment thresholds (chain roll)

# Imploding rolls — re-roll and subtract when a die meets the threshold
d.roll('3d6i')              # implode on min (1); result can be <= 0
d.roll('3d6i2')             # implode on 1 or 2

# Exploding pools — add an extra die to the pool for each triggered die
d.pool('12d6e')             # explode on 6; pool may grow beyond 12
d.pool('12d6et4')           # explode on 6, then count successes >= 4
d.pool('12d6t4e')           # threshold and explosion spec order is flexible
d.pool('8d6e+4d6+1e5t4')    # compound: each group has its own threshold

# Imploding pools — each triggered die negates one success
d.pool('4d6it3')            # implode on 1; each implode negates a success
d.pool('4d6e5i2t4')         # explode on 5+, implode on 1–2, threshold 4

# Spawn independent, non-overlapping streams (safe for parallel work)
workers = d.spawn(8)
results = [w.roll('3d6') for w in workers]
```

### Roll notation reference

| Pattern | Meaning |
|---|---|
| `XdY` | Roll X dice with Y sides, sum all |
| `XdY+Z` / `XdY-Z` | Roll and apply flat modifier |
| `XdYkhN` | Keep highest N dice |
| `XdYklN` | Keep lowest N dice |
| `XdYdZ` | Chain: use sum of first roll as count for second |
| `Xdf` | Fate/fudge dice; each die produces −1, 0, or 1 |
| `XdYe` | Explode on max: re-roll and add for each die that hits Y |
| `XdYeN` | Explode when raw result >= N |
| `XdYe!` / `XdYeN!` | Cascade explode: exploded dice can also explode |
| `XdYi` | Implode on min (1): re-roll and subtract |
| `XdYiN` | Implode when raw result <= N |
| `XdYeNiW` | Explode on N or higher **and** implode on W or lower |

Explosion and implosion are evaluated on **kept** dice only (after `kh`/`kl`
filtering). Discarded dice never trigger either mechanic. Implosion never
cascades.

### Pool notation reference

| Pattern | Meaning |
|---|---|
| `NdS` | Roll N dice, return list of results |
| `NdS+M` / `NdS-M` | Roll N dice, add/subtract M from each result |
| `NdStT` | Roll N dice, return count of results >= T |
| `NdS+MtT` | Per-die modifier, then success threshold |
| `N1dS+M+N2dS-MtT` | Compound pool with mixed per-die modifiers |
| `NdSe` / `NdSeN` | Explode on max (or N): add a die to the pool |
| `NdSe!` / `NdSeN!` | Cascade explode |
| `NdSi` / `NdSiN` | Implode on min/N: each implode negates one success |
| `NdSeNiW` | Explode on N or higher and implode on W or lower |

Pool explosion and implosion are evaluated on **raw** (pre-modifier) die
values. The success count from implosions is clamped at zero. The `tT`
threshold token may appear before or after the per-subpool `e`/`i` spec
(e.g. both `12d6et4` and `12d6t4e` are accepted).

## Tables

```python
import dieroller

# --- Flat table ---
t = dieroller.table()
t.add("Goblin", "Orc", "Troll", "Dragon", "Basilisk", "Wyvern")

print(t)
# 1. Goblin
# 2. Orc
# 3. Troll
# 4. Dragon
# 5. Basilisk
# 6. Wyvern

t.size         # 6
t.roll()       # uniform random entry from all 6

# --- Sub-range rolling ---
# Pass any dice notation; result is clamped to [1, size]
t.roll("1d6")      # equivalent to t.roll() — full range
t.roll("1d3+2")    # 1d3 + 2 → result in [3, 5]; only entries 3–5 selected
t.roll("1d4+2")    # result in [3, 6] — upper four entries only

# --- Nested / sub-tables ---
monsters = dieroller.table()
undead = dieroller.table()
undead.add("Skeleton", "Zombie", "Wight")

monsters.add("Goblin", undead, "Dragon")

print(monsters)
# 1. Goblin
# 2. [sub-table]
#      1. Skeleton
#      2. Zombie
#      3. Wight
# 3. Dragon

monsters.roll()   # "Goblin", "Skeleton", "Zombie", "Wight", or "Dragon"
                  # sub-tables are rolled recursively until a plain value is reached

# Nesting can be arbitrarily deep
outer = dieroller.table()
mid   = dieroller.table()
inner = dieroller.table()
inner.add("Ancient Red Dragon", "Tarrasque")
mid.add("Vampire", inner)
outer.add("Goblin", mid)
outer.roll()   # may return "Goblin", "Vampire", "Ancient Red Dragon", or "Tarrasque"

# --- Subclassed table ---
class MonsterTable(dieroller.table):
    """A specialised encounter table — inherits all behaviour as-is."""
    pass

mt = MonsterTable()
mt.add("Rat", "Wolf", "Bear", "Troll")
mt.roll()          # uniform random entry
mt.roll("1d4")     # same, explicitly driven by 1d4

# --- Subclassed table with _roll for sub-range rolling ---
# Override _roll to constrain which indices the table ever produces.
# roll() calls _roll() when no dice code is supplied.
class UpperHalfTable(dieroller.table):
    """Rolls only the upper half of the table (high-difficulty entries)."""
    def _roll(self):
        mid = self.size // 2 + 1
        return self._dice._rng.nextint(mid, self.size)

boss = UpperHalfTable(seed=42)
boss.add("Kobold", "Goblin", "Troll", "Dragon", "Tarrasque", "Balor")
boss.roll()   # always one of: "Troll", "Dragon", "Tarrasque", "Balor"

# Use dice notation inside _roll for readable sub-range definitions
class TreasureTable(dieroller.table):
    """Rolls 1d3+3 so only entries 4–6 are ever selected via _roll()."""
    def _roll(self):
        return self._dice.roll("1d3+3")

treasure = TreasureTable()
treasure.add("Copper", "Silver", "Gold", "Gem", "Artifact", "Legendary")
treasure.roll()         # always "Gem", "Artifact", or "Legendary"
treasure.roll("1d3")    # explicit code overrides _roll — entries 1–3 only
```

### Weighted entries

`add_weighted(item, weight)` inserts an entry `weight` times so it occupies
that many consecutive index slots.  A weight of N makes the entry N times as
likely as a weight-1 entry on a uniform roll.  It is exactly equivalent to
calling `add(item)` N times.

```python
import dieroller

loot = dieroller.table(seed=42)
loot.add_weighted("Gold coin", 5)   # 5 slots — common
loot.add_weighted("Gem",       3)   # 3 slots — uncommon
loot.add_weighted("Artifact",  1)   # 1 slot  — rare

loot.size    # 9  (5 + 3 + 1)
loot.roll()  # random entry

# The three lines above are exactly equivalent to:
loot2 = dieroller.table(seed=42)
loot2.add("Gold coin", "Gold coin", "Gold coin", "Gold coin", "Gold coin",
          "Gem", "Gem", "Gem",
          "Artifact")
```

| Entry       | Weight | Slots | Approx. frequency |
|-------------|--------|-------|-------------------|
| Gold coin   | 5      | 1–5   | ~56%              |
| Gem         | 3      | 6–8   | ~33%              |
| Artifact    | 1      | 9     | ~11%              |

Mix `add` and `add_weighted` freely — they both append to the same list:

```python
t = dieroller.table()
t.add("nothing")            # weight 1
t.add_weighted("silver", 3) # weight 3 — 3× as likely as "nothing"
t.add_weighted("gold",   1) # weight 1 — same probability as "nothing"
t.size   # 5
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
