"""Tests for dieroller.Dice."""

import pytest
from dieroller import Dice
from dieroller.dice import (
    _parse, _apply_keep, _Segment,
    _parse_pool, _count_successes, _SubPool,
    _parse_explode_implode,
)


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


class TestParsePool:
    def test_simple(self):
        sub_pools, threshold = _parse_pool("12d6")
        assert sub_pools == [_SubPool(count=12, sides=6, per_die_modifier=0)]
        assert threshold is None

    def test_with_threshold(self):
        sub_pools, threshold = _parse_pool("4d6t4")
        assert sub_pools == [_SubPool(count=4, sides=6, per_die_modifier=0)]
        assert threshold == 4

    def test_threshold_uppercase(self):
        _, threshold = _parse_pool("4d6T4")
        assert threshold == 4

    def test_positive_per_die_modifier(self):
        sub_pools, threshold = _parse_pool("12d6+1t4")
        assert sub_pools == [_SubPool(count=12, sides=6, per_die_modifier=1)]
        assert threshold == 4

    def test_negative_per_die_modifier(self):
        sub_pools, threshold = _parse_pool("4d10-1t5")
        assert sub_pools == [_SubPool(count=4, sides=10, per_die_modifier=-1)]
        assert threshold == 5

    def test_compound_pool_second_has_modifier(self):
        sub_pools, threshold = _parse_pool("8d6+4d6+1t4")
        assert len(sub_pools) == 2
        assert sub_pools[0] == _SubPool(count=8, sides=6, per_die_modifier=0)
        assert sub_pools[1] == _SubPool(count=4, sides=6, per_die_modifier=1)
        assert threshold == 4

    def test_compound_pool_both_have_modifiers(self):
        sub_pools, threshold = _parse_pool("8d10+2+4d10-1t5")
        assert len(sub_pools) == 2
        assert sub_pools[0] == _SubPool(count=8, sides=10, per_die_modifier=2)
        assert sub_pools[1] == _SubPool(count=4, sides=10, per_die_modifier=-1)
        assert threshold == 5

    def test_compound_pool_no_threshold(self):
        sub_pools, threshold = _parse_pool("8d6+4d6")
        assert len(sub_pools) == 2
        assert threshold is None

    def test_no_expression_raises(self):
        with pytest.raises(ValueError):
            _parse_pool("notapool")

    def test_no_expression_threshold_only_raises(self):
        with pytest.raises(ValueError):
            _parse_pool("t4")


class TestCountSuccesses:
    def test_mixed_results(self):
        assert _count_successes([2, 4, 4, 6], threshold=4) == 3

    def test_all_fail(self):
        assert _count_successes([1, 2, 3], threshold=4) == 0

    def test_all_succeed(self):
        assert _count_successes([4, 5, 6], threshold=4) == 3

    def test_empty_results(self):
        assert _count_successes([], threshold=4) == 0

    def test_exact_threshold_counts_as_success(self):
        assert _count_successes([4, 4, 4], threshold=4) == 3

    def test_one_below_threshold_excluded(self):
        assert _count_successes([3, 4], threshold=4) == 1


class TestDicePool:
    def test_no_threshold_returns_list(self):
        d = Dice(seed=1)
        result = d.pool("12d6")
        assert isinstance(result, list)

    def test_list_length(self):
        d = Dice(seed=1)
        assert len(d.pool("12d6")) == 12

    def test_list_element_range(self):
        d = Dice(seed=1)
        for _ in range(100):
            for val in d.pool("4d6"):
                assert 1 <= val <= 6

    def test_threshold_returns_int(self):
        d = Dice(seed=1)
        result = d.pool("4d6t4")
        assert isinstance(result, int)

    def test_success_count_in_range(self):
        d = Dice(seed=1)
        for _ in range(200):
            assert 0 <= d.pool("4d6t4") <= 4

    def test_per_die_modifier_shifts_range(self):
        d = Dice(seed=1)
        for _ in range(200):
            for val in d.pool("4d6+1"):
                assert 2 <= val <= 7

    def test_negative_per_die_modifier_shifts_range(self):
        d = Dice(seed=1)
        for _ in range(200):
            for val in d.pool("4d6-1"):
                assert 0 <= val <= 5

    def test_compound_pool_total_length(self):
        d = Dice(seed=1)
        assert len(d.pool("8d6+4d6")) == 12

    def test_compound_pool_success_count_in_range(self):
        d = Dice(seed=1)
        for _ in range(200):
            assert 0 <= d.pool("8d6+4d6+1t4") <= 12

    def test_compound_mixed_modifiers_success_range(self):
        d = Dice(seed=1)
        for _ in range(200):
            assert 0 <= d.pool("8d10+2+4d10-1t5") <= 12

    def test_seeded_reproducible_list(self):
        a = Dice(seed=55)
        b = Dice(seed=55)
        assert [a.pool("4d6") for _ in range(20)] == [b.pool("4d6") for _ in range(20)]

    def test_seeded_reproducible_successes(self):
        a = Dice(seed=55)
        b = Dice(seed=55)
        assert [a.pool("4d6t4") for _ in range(20)] == [b.pool("4d6t4") for _ in range(20)]

    def test_invalid_code_raises(self):
        d = Dice(seed=1)
        with pytest.raises(ValueError):
            d.pool("notapool")


class TestParseExplodeImplode:
    def test_no_specs(self):
        explode, cascade, implode = _parse_explode_implode('', '', 6)
        assert explode is None
        assert cascade is False
        assert implode is None

    def test_explode_defaults_to_sides(self):
        explode, cascade, implode = _parse_explode_implode('e', '', 6)
        assert explode == 6
        assert cascade is False

    def test_explode_explicit_threshold(self):
        explode, _, _ = _parse_explode_implode('e5', '', 6)
        assert explode == 5

    def test_explode_cascade(self):
        _, cascade, _ = _parse_explode_implode('e!', '', 6)
        assert cascade is True

    def test_explode_explicit_threshold_cascade(self):
        explode, cascade, _ = _parse_explode_implode('e5!', '', 6)
        assert explode == 5
        assert cascade is True

    def test_implode_defaults_to_one(self):
        _, _, implode = _parse_explode_implode('', 'i', 6)
        assert implode == 1

    def test_implode_explicit_threshold(self):
        _, _, implode = _parse_explode_implode('', 'i3', 6)
        assert implode == 3

    def test_both_present(self):
        explode, cascade, implode = _parse_explode_implode('e5!', 'i2', 10)
        assert explode == 5
        assert cascade is True
        assert implode == 2


class TestSegmentParseExplodeImplode:
    """Verify _parse wires explosion/implosion into _Segment correctly."""

    def test_explode_on_max(self):
        segs, _, _ = _parse('3d6e')
        assert segs[0].explode == 6
        assert segs[0].explode_cascade is False

    def test_explode_explicit(self):
        segs, _, _ = _parse('3d6e5')
        assert segs[0].explode == 5

    def test_explode_cascade(self):
        segs, _, _ = _parse('3d6e!')
        assert segs[0].explode == 6
        assert segs[0].explode_cascade is True

    def test_explode_explicit_cascade(self):
        segs, _, _ = _parse('3d8e7!')
        assert segs[0].explode == 7
        assert segs[0].explode_cascade is True

    def test_implode_on_min(self):
        segs, _, _ = _parse('3d6i')
        assert segs[0].implode == 1

    def test_implode_explicit(self):
        segs, _, _ = _parse('3d6i2')
        assert segs[0].implode == 2

    def test_explode_and_implode(self):
        segs, _, _ = _parse('3d6e5i2')
        assert segs[0].explode == 5
        assert segs[0].implode == 2

    def test_fate_dice_no_explode(self):
        segs, _, _ = _parse('4dfe')
        assert segs[0].explode is None
        assert segs[0].implode is None

    def test_modifier_still_parsed_after_explode(self):
        _, _, mod = _parse('3d6e+4')
        assert mod == 4

    def test_keep_and_explode(self):
        segs, _, _ = _parse('5d6kh3e')
        assert segs[0].keep == 'kh3'
        assert segs[0].explode == 6

    def test_chained_segments_independent_specs(self):
        segs, _, _ = _parse('4d6e!+3d8e7!')
        assert segs[0].explode == 6 and segs[0].explode_cascade is True
        assert segs[1].explode == 7 and segs[1].explode_cascade is True


class TestSubPoolParseExplodeImplode:
    """Verify _parse_pool wires explosion/implosion into _SubPool correctly."""

    def test_explode_on_max(self):
        sps, _ = _parse_pool('4d6e')
        assert sps[0].explode == 6
        assert sps[0].explode_cascade is False

    def test_explode_explicit(self):
        sps, _ = _parse_pool('4d10e8')
        assert sps[0].explode == 8

    def test_explode_cascade(self):
        sps, _ = _parse_pool('4d6e!')
        assert sps[0].explode_cascade is True

    def test_implode_on_min(self):
        sps, _ = _parse_pool('4d6i')
        assert sps[0].implode == 1

    def test_implode_explicit(self):
        sps, _ = _parse_pool('4d6i2')
        assert sps[0].implode == 2

    def test_threshold_before_explode_notation(self):
        # User-friendly ordering: tN then e (threshold spliced out first)
        sps, threshold = _parse_pool('12d6t4e')
        assert threshold == 4
        assert sps[0].explode == 6

    def test_threshold_after_explode_notation(self):
        # Preferred ordering: e then tN
        sps, threshold = _parse_pool('12d6et4')
        assert threshold == 4
        assert sps[0].explode == 6

    def test_compound_independent_explosion_specs(self):
        sps, threshold = _parse_pool('8d6e+4d6+1e5t4')
        assert sps[0].explode == 6
        assert sps[0].per_die_modifier == 0
        assert sps[1].explode == 5
        assert sps[1].per_die_modifier == 1
        assert threshold == 4

    def test_per_die_modifier_and_implode(self):
        sps, _ = _parse_pool('6d10+2i')
        assert sps[0].per_die_modifier == 2
        assert sps[0].implode == 1


class TestRollExplosion:
    def test_explode_can_exceed_max(self):
        d = Dice(seed=1)
        results = [d.roll('1d6e') for _ in range(500)]
        assert max(results) > 6

    def test_explode_explicit_threshold_can_exceed(self):
        d = Dice(seed=1)
        results = [d.roll('1d6e5') for _ in range(500)]
        assert max(results) > 6

    def test_no_explode_never_exceeds_max(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert d.roll('1d6') <= 6

    def test_cascade_produces_higher_max_than_single(self):
        # Cascade can stack unboundedly; single explode adds at most one die.
        # With enough rolls the cascade version should sometimes exceed 12.
        d = Dice(seed=2)
        results = [d.roll('1d6e!') for _ in range(1000)]
        assert max(results) > 12

    def test_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('3d6e') for _ in range(50)] == [b.roll('3d6e') for _ in range(50)]

    def test_cascade_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('3d6e!') for _ in range(50)] == [b.roll('3d6e!') for _ in range(50)]

    def test_modifier_applied_after_explosion(self):
        a = Dice(seed=7)
        b = Dice(seed=7)
        with_mod = a.roll('3d6e+5')
        without_mod = b.roll('3d6e')
        assert with_mod == without_mod + 5


class TestRollImplosion:
    def test_implode_can_go_below_min(self):
        d = Dice(seed=1)
        results = [d.roll('1d6i') for _ in range(500)]
        assert min(results) < 1

    def test_implode_explicit_threshold(self):
        d = Dice(seed=1)
        # implode on 1 or 2 — more implosions, should occasionally give <= 0
        results = [d.roll('1d6i2') for _ in range(500)]
        assert min(results) < 1

    def test_no_implode_always_at_least_one(self):
        d = Dice(seed=1)
        for _ in range(500):
            assert d.roll('1d6') >= 1

    def test_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('3d6i') for _ in range(50)] == [b.roll('3d6i') for _ in range(50)]

    def test_explode_and_implode_together(self):
        a = Dice(seed=13)
        b = Dice(seed=13)
        assert [a.roll('3d6e5i2') for _ in range(50)] == [b.roll('3d6e5i2') for _ in range(50)]


class TestDicePoolExplosion:
    def test_explode_can_grow_pool(self):
        d = Dice(seed=1)
        max_len = max(len(d.pool('4d6e')) for _ in range(500))
        assert max_len > 4

    def test_explode_explicit_threshold_grows_more(self):
        # Exploding on 5+ triggers more often than 6+
        d = Dice(seed=1)
        results_e5 = [len(d.pool('4d6e5')) for _ in range(300)]
        d2 = Dice(seed=1)
        results_e6 = [len(d2.pool('4d6e')) for _ in range(300)]
        assert sum(results_e5) >= sum(results_e6)

    def test_cascade_can_grow_further(self):
        d = Dice(seed=2)
        max_len = max(len(d.pool('4d6e!')) for _ in range(500))
        assert max_len > 5

    def test_no_explode_pool_size_fixed(self):
        d = Dice(seed=1)
        for _ in range(200):
            assert len(d.pool('4d6')) == 4

    def test_explode_with_threshold_returns_int(self):
        d = Dice(seed=1)
        assert isinstance(d.pool('4d6t4e'), int)

    def test_explode_success_count_can_exceed_initial_count(self):
        # Pool of 4d6 exploding on 6; successes >= 4. With many trials
        # and explosions, count > 4 should eventually occur.
        d = Dice(seed=3)
        counts = [d.pool('4d6t4e') for _ in range(500)]
        assert max(counts) > 4

    def test_seeded_reproducible(self):
        a = Dice(seed=55)
        b = Dice(seed=55)
        assert [a.pool('4d6e') for _ in range(20)] == [b.pool('4d6e') for _ in range(20)]

    def test_seeded_reproducible_with_threshold(self):
        a = Dice(seed=55)
        b = Dice(seed=55)
        assert [a.pool('4d6t4e') for _ in range(20)] == [b.pool('4d6t4e') for _ in range(20)]

    def test_compound_independent_explosion_thresholds(self):
        d = Dice(seed=1)
        result = d.pool('8d6e+4d6+1e5t4')
        assert isinstance(result, int)
        assert result >= 0


class TestDicePoolImplosion:
    def test_implode_reduces_successes(self):
        # Same seed: with implosion, success count should sometimes be lower
        d1 = Dice(seed=1)
        d2 = Dice(seed=1)
        no_impl = [d1.pool('4d6t3') for _ in range(200)]
        with_impl = [d2.pool('4d6it3') for _ in range(200)]
        assert any(a > b for a, b in zip(no_impl, with_impl))

    def test_implode_count_never_below_zero(self):
        d = Dice(seed=1)
        for _ in range(500):
            result = d.pool('4d6it3')
            assert result >= 0

    def test_implode_explicit_threshold(self):
        d = Dice(seed=1)
        result = d.pool('4d6i2t4')
        assert isinstance(result, int)
        assert result >= 0

    def test_implode_no_threshold_returns_list(self):
        # Without a threshold there are no successes to negate; raw list returned
        d = Dice(seed=1)
        result = d.pool('4d6i')
        assert isinstance(result, list)
        assert len(result) == 4

    def test_seeded_reproducible(self):
        a = Dice(seed=77)
        b = Dice(seed=77)
        assert [a.pool('4d6it4') for _ in range(20)] == [b.pool('4d6it4') for _ in range(20)]

    def test_compound_pool_with_implosion(self):
        d = Dice(seed=1)
        result = d.pool('8d6i+4d6+1e5t4')
        assert isinstance(result, int)
        assert result >= 0


class TestRollKeepAndExplode:
    """Regression suite for the keep-then-explode interaction.

    Defined behaviour: keep filtering (kh/kl) is applied *before* the
    explosion/implosion check.  Only the *kept* dice are inspected for
    explosion or implosion triggers; discarded dice never fire.
    """

    # --- explosion fires on the kept set, not the full roll ---

    def test_keep_high_explosion_can_fire(self):
        # 5d6kh3: without explosion max is 3*6 = 18.
        # With explosion on the 3 kept dice, result can exceed 18.
        d = Dice(seed=1)
        results = [d.roll('5d6kh3e') for _ in range(500)]
        assert max(results) > 18

    def test_keep_low_explosion_never_fires_in_practice(self):
        # 10d6kl1e: keep the single *lowest* die from 10d6, explode on 6.
        # P(min of 10d6 = 6) = (1/6)^10 ≈ 1.7e-8 — never observed in 500 rolls.
        # If explosion were triggered by *any* of the 10 dice this would fail.
        d = Dice(seed=1)
        results = [d.roll('10d6kle') for _ in range(500)]
        assert max(results) <= 6

    def test_keep_high_cascade_explosion_can_fire(self):
        d = Dice(seed=1)
        results = [d.roll('5d6kh3e!') for _ in range(500)]
        assert max(results) > 18

    # --- implosion fires on the kept set, not the full roll ---

    def test_keep_low_implosion_can_fire(self):
        # 5d6kl2i: keep the 2 *lowest* dice, implode on 1.
        # Lowest dice frequently roll 1, so implosion will sometimes reduce the total.
        d = Dice(seed=1)
        results = [d.roll('5d6kl2i') for _ in range(500)]
        assert min(results) < 2  # plain kl2 min is 2; implosion can push below

    def test_keep_high_implosion_never_fires_in_practice(self):
        # 10d6kh1i: keep the single *highest* die from 10d6, implode on 1.
        # P(max of 10d6 = 1) = (1/6)^10 — never observed in 500 rolls.
        d = Dice(seed=1)
        results = [d.roll('10d6khi') for _ in range(500)]
        assert min(results) >= 1

    # --- combined keep + explode + implode ---

    def test_keep_and_both_mechanics_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('5d6kh3e5i2') for _ in range(50)] == \
               [b.roll('5d6kh3e5i2') for _ in range(50)]

    # --- seeded regression pins ---

    def test_keep_high_explosion_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('5d6kh3e') for _ in range(50)] == \
               [b.roll('5d6kh3e') for _ in range(50)]

    def test_keep_low_explosion_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('5d6kl2e') for _ in range(50)] == \
               [b.roll('5d6kl2e') for _ in range(50)]

    def test_keep_high_implosion_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('5d6kh3i') for _ in range(50)] == \
               [b.roll('5d6kh3i') for _ in range(50)]

    def test_keep_low_implosion_seeded_reproducible(self):
        a = Dice(seed=42)
        b = Dice(seed=42)
        assert [a.roll('5d6kl2i') for _ in range(50)] == \
               [b.roll('5d6kl2i') for _ in range(50)]
