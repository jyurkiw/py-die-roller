"""Tests for dieroller.Dice."""

import pytest
from dieroller import Dice
from dieroller.dice import _parse, _apply_keep, _Segment


class TestDiceParse:
    def test_simple(self):
        segs, count, mod = _parse("1d6")
        assert segs == [_Segment(sides=6, keep=None)]
        assert count == 1
        assert mod == 0

    def test_implicit_count_defaults_to_one(self):
        segs, count, mod = _parse("d6")
        assert count == 1
        assert segs[0].sides == 6

    def test_multi_dice(self):
        segs, count, mod = _parse("3d8")
        assert count == 3
        assert segs[0].sides == 8

    def test_positive_modifier(self):
        _, _, mod = _parse("1d6+2")
        assert mod == 2

    def test_negative_modifier(self):
        _, _, mod = _parse("1d6-3")
        assert mod == -3

    def test_keep_highest_no_count(self):
        segs, _, _ = _parse("3d6kh")
        assert segs[0].keep == "kh"

    def test_keep_highest_with_count(self):
        segs, _, _ = _parse("5d6kh3")
        assert segs[0].keep == "kh3"

    def test_keep_lowest_no_count(self):
        segs, _, _ = _parse("3d20kl")
        assert segs[0].keep == "kl"

    def test_keep_lowest_with_count(self):
        segs, _, _ = _parse("4d8kl2")
        assert segs[0].keep == "kl2"

    def test_chained_two_segments(self):
        segs, count, mod = _parse("4d3d12kh4+9")
        assert count == 4
        assert len(segs) == 2
        assert segs[0] == _Segment(sides=3, keep=None)
        assert segs[1] == _Segment(sides=12, keep="kh4")
        assert mod == 9

    def test_chained_three_segments(self):
        segs, count, mod = _parse("4d3d12kh4d7+9")
        assert count == 4
        assert len(segs) == 3
        assert segs[2] == _Segment(sides=7, keep=None)
        assert mod == 9

    def test_no_d_raises(self):
        with pytest.raises(ValueError):
            _parse("6+2")

    def test_zero_sides_raises(self):
        with pytest.raises(ValueError):
            _parse("1d0")

    def test_fate_die_parsed(self):
        segs, count, mod = _parse("4df")
        assert count == 4
        assert segs == [_Segment(sides=0, keep=None, fate=True)]
        assert mod == 0

    def test_fate_die_uppercase(self):
        segs, _, _ = _parse("4dF")
        assert segs[0].fate is True

    def test_fate_die_with_single_modifier(self):
        _, _, mod = _parse("4df+3")
        assert mod == 3

    def test_fate_die_with_multiple_modifiers(self):
        segs, count, mod = _parse("4df+3+2+2+2")
        assert count == 4
        assert segs[0].fate is True
        assert mod == 9  # 3+2+2+2

    def test_multiple_modifiers_summed(self):
        _, _, mod = _parse("1d6+1+2+3")
        assert mod == 6


class TestApplyKeep:
    def test_none_returns_all(self):
        assert _apply_keep([1, 2, 3], None) == [1, 2, 3]

    def test_kh_keeps_highest_one(self):
        assert _apply_keep([1, 5, 3], "kh") == [5]

    def test_kh_with_count(self):
        assert _apply_keep([1, 5, 3, 4], "kh2") == [5, 4]

    def test_kl_keeps_lowest_one(self):
        assert _apply_keep([1, 5, 3], "kl") == [1]

    def test_kl_with_count(self):
        assert _apply_keep([1, 5, 3, 4], "kl2") == [1, 3]

    def test_keep_count_exceeds_pool_raises(self):
        with pytest.raises(ValueError):
            _apply_keep([1, 2], "kh5")


class TestDiceRoll:
    def test_returns_int(self):
        d = Dice(seed=1)
        assert isinstance(d.roll("1d6"), int)

    def test_d6_range(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 1 <= d.roll("1d6") <= 6

    def test_positive_modifier(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 3 <= d.roll("1d6+2") <= 8

    def test_negative_modifier(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 0 <= d.roll("1d6-1") <= 5

    def test_multi_dice_sum(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 3 <= d.roll("3d6") <= 18

    def test_keep_highest(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 3 <= d.roll("5d6kh3+2") <= 20

    def test_keep_lowest(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 8 <= d.roll("3d20kl+7") <= 27

    def test_implicit_count(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 1 <= d.roll("d6") <= 6

    def test_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll("2d6") for _ in range(20)] == [b.roll("2d6") for _ in range(20)]

    def test_chained_returns_int(self):
        d = Dice(seed=1)
        result = d.roll("4d3d12kh4d7+9")
        assert isinstance(result, int)

    def test_chained_modifier_applied(self):
        # With seed fixed we can verify the +9 is included by comparing
        # a roll with and without the modifier across identical seeds
        a = Dice(seed=7)
        b = Dice(seed=7)
        with_mod = a.roll("4d3d12kh4d7+9")
        without_mod = b.roll("4d3d12kh4d7")
        assert with_mod == without_mod + 9

    def test_invalid_code_raises(self):
        d = Dice(seed=1)
        with pytest.raises(ValueError):
            d.roll("notadice")

    def test_keep_exceeds_pool_raises(self):
        d = Dice(seed=1)
        with pytest.raises(ValueError):
            d.roll("2d6kh5")

    def test_fate_die_range(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert -1 <= d.roll("1df") <= 1

    def test_four_fate_dice_range(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert -4 <= d.roll("4df") <= 4

    def test_fate_all_values_reachable(self):
        d = Dice(seed=1)
        results = {d.roll("1df") for _ in range(300)}
        assert results == {-1, 0, 1}

    def test_fate_with_stacked_modifiers(self):
        # 4df+3+2+2+2: modifier totals 9, fate range [-4, 4], so result in [5, 13]
        d = Dice(seed=1)
        for _ in range(500):
            assert 5 <= d.roll("4df+3+2+2+2") <= 13

    def test_fate_seeded_reproducible(self):
        a = Dice(seed=77)
        b = Dice(seed=77)
        assert [a.roll("4df") for _ in range(20)] == [b.roll("4df") for _ in range(20)]

    def test_multiple_modifiers_on_normal_die(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert 7 <= d.roll("1d6+1+2+3") <= 12  # +6 modifier, range [7, 12]


class TestDiceSpawn:
    def test_returns_correct_count(self):
        d = Dice(seed=1)
        children = d.spawn(4)
        assert len(children) == 4

    def test_children_are_dice_instances(self):
        d = Dice(seed=1)
        for child in d.spawn(3):
            assert isinstance(child, Dice)

    def test_children_have_independent_streams(self):
        d = Dice(seed=1)
        children = d.spawn(4)
        results = [c.roll("1d100") for c in children]
        # All four independent streams should produce different values
        assert len(set(results)) > 1

    def test_same_seed_same_children(self):
        a = Dice(seed=99)
        b = Dice(seed=99)
        a_children = a.spawn(4)
        b_children = b.spawn(4)
        for ac, bc in zip(a_children, b_children):
            assert ac.roll("3d6") == bc.roll("3d6")
