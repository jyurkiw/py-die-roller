"""Tests for dieroller.RNG."""

import pytest
from dieroller import RNG

_UINT64_MAX = 2**64 - 1


class TestNext:
    def test_returns_int(self):
        rng = RNG(seed=1)
        assert isinstance(next(rng), int)

    def test_value_is_uint64(self):
        rng = RNG(seed=1)
        value = next(rng)
        assert 0 <= value < 2**64

    def test_seeded_sequence_is_reproducible(self):
        a = RNG(seed=42)
        b = RNG(seed=42)
        assert [next(a) for _ in range(10)] == [next(b) for _ in range(10)]

    def test_different_seeds_produce_different_sequences(self):
        a = RNG(seed=1)
        b = RNG(seed=2)
        assert [next(a) for _ in range(10)] != [next(b) for _ in range(10)]

    def test_consecutive_calls_advance_sequence(self):
        rng = RNG(seed=7)
        results = [next(rng) for _ in range(100)]
        # All values should not be identical (astronomically unlikely with a working PRNG)
        assert len(set(results)) > 1

    def test_seed_zero_is_valid(self):
        # seed=0 must not be treated as None and silently re-seeded from entropy
        a = RNG(seed=0)
        b = RNG(seed=0)
        assert next(a) == next(b)

    @pytest.mark.parametrize("algorithm", ["pcg64", "philox", "sfc64"])
    def test_all_builtin_algorithms(self, algorithm):
        rng = RNG(seed=1, algorithm=algorithm)
        value = next(rng)
        assert 0 <= value < 2**64


class TestNextInt:
    def test_returns_int(self):
        rng = RNG(seed=1)
        assert isinstance(rng.nextint(1, 6), int)

    def test_d6_range(self):
        rng = RNG(seed=1)
        for _ in range(1000):
            assert 1 <= rng.nextint(1, 6) <= 6

    def test_single_value_range(self):
        rng = RNG(seed=1)
        assert rng.nextint(42, 42) == 42

    def test_default_min_is_zero(self):
        rng = RNG(seed=1)
        value = rng.nextint(max=10)
        assert 0 <= value <= 10

    def test_default_range_is_full_uint64(self):
        rng = RNG(seed=1)
        value = rng.nextint()
        assert 0 <= value <= _UINT64_MAX

    def test_max_boundary_is_inclusive(self):
        # With enough rolls, max value must appear at least once
        rng = RNG(seed=1)
        rolls = {rng.nextint(0, 1) for _ in range(200)}
        assert 1 in rolls

    def test_min_boundary_is_inclusive(self):
        rng = RNG(seed=1)
        rolls = {rng.nextint(0, 1) for _ in range(200)}
        assert 0 in rolls

    def test_seeded_sequence_is_reproducible(self):
        a = RNG(seed=99)
        b = RNG(seed=99)
        assert [a.nextint(1, 20) for _ in range(20)] == [b.nextint(1, 20) for _ in range(20)]

    def test_min_greater_than_max_raises(self):
        rng = RNG(seed=1)
        with pytest.raises(ValueError):
            rng.nextint(10, 5)

    def test_all_d6_faces_appear(self):
        rng = RNG(seed=1)
        rolls = {rng.nextint(1, 6) for _ in range(600)}
        assert rolls == {1, 2, 3, 4, 5, 6}


class TestNextFloat:
    def test_returns_float(self):
        rng = RNG(seed=1)
        assert isinstance(rng.nextfloat(), float)

    def test_value_in_unit_interval(self):
        rng = RNG(seed=1)
        for _ in range(1000):
            assert 0.0 <= rng.nextfloat() <= 1.0

    def test_zero_is_reachable(self):
        # nextint() == 0 maps to exactly 0.0
        rng = RNG.__new__(RNG)
        rng._algo = None
        rng._ss = None
        rng.nextint = lambda *_: 0
        assert rng.nextfloat() == 0.0

    def test_one_is_reachable(self):
        # nextint() == _UINT64_MAX maps to exactly 1.0
        rng = RNG.__new__(RNG)
        rng._algo = None
        rng._ss = None
        rng.nextint = lambda *_: _UINT64_MAX
        assert rng.nextfloat() == 1.0

    def test_seeded_sequence_is_reproducible(self):
        a = RNG(seed=5)
        b = RNG(seed=5)
        assert [a.nextfloat() for _ in range(20)] == [b.nextfloat() for _ in range(20)]

    def test_sequence_advances(self):
        rng = RNG(seed=3)
        results = [rng.nextfloat() for _ in range(100)]
        assert len(set(results)) > 1
