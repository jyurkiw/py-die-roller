"""Tests for dieroller.table."""

import pytest
import dieroller
from dieroller.table import table


class TestTableBasics:
    def test_empty_size(self):
        t = table()
        assert t.size == 0

    def test_add_single(self):
        t = table()
        t.add("a")
        assert t.size == 1

    def test_add_multiple_in_one_call(self):
        t = table()
        t.add("a", "b", "c")
        assert t.size == 3

    def test_add_multiple_calls(self):
        t = table()
        t.add("x")
        t.add("y")
        assert t.size == 2

    def test_size_property_readonly(self):
        t = table()
        with pytest.raises(AttributeError):
            t.size = 5

    def test_repr(self):
        t = table()
        t.add("a", "b")
        assert repr(t) == "table(size=2)"


class TestTableRoll:
    def test_roll_returns_entry(self):
        t = table(seed=0)
        t.add("only")
        assert t.roll() == "only"

    def test_roll_uniform_single_entry(self):
        t = table(seed=42)
        t.add("x")
        assert t.roll() == "x"

    def test_roll_empty_raises(self):
        t = table()
        with pytest.raises(IndexError):
            t.roll()

    def test_roll_with_code(self):
        t = table(seed=0)
        t.add("a", "b", "c", "d", "e", "f")
        result = t.roll("1d6")
        assert result in ("a", "b", "c", "d", "e", "f")

    def test_roll_code_clamps_low(self):
        t = table(seed=0)
        t.add("a", "b", "c")
        # Force a result of -5 by using a modifier that would go negative
        # We can't easily force this, but we can test with a code that always
        # produces 1 (1d1) — check it stays in bounds.
        result = t.roll("1d1")
        assert result == "a"

    def test_roll_code_clamps_high(self):
        t = table(seed=0)
        t.add("a", "b")
        # A code that can produce values beyond size should clamp
        result = t.roll("1d100")
        assert result in ("a", "b")

    def test_roll_empty_with_code_raises(self):
        t = table()
        with pytest.raises(IndexError):
            t.roll("1d6")

    def test_roll_coverage(self):
        # Ensure all entries are reachable over many rolls
        t = table(seed=1)
        t.add("a", "b", "c", "d")
        seen = {t.roll() for _ in range(200)}
        assert seen == {"a", "b", "c", "d"}


class TestTableSubRangeRoll:
    def test_subrange_restricts_entries(self):
        # 1d3+2 gives [3, 5]; only entries at indices 3, 4, 5 should appear
        t = table(seed=0)
        t.add("a", "b", "c", "d", "e", "f")
        seen = {t.roll("1d3+2") for _ in range(300)}
        assert seen <= {"c", "d", "e"}
        assert seen == {"c", "d", "e"}

    def test_subrange_all_in_range_reachable(self):
        t = table(seed=2)
        t.add("a", "b", "c", "d", "e", "f")
        seen = {t.roll("1d4+2") for _ in range(300)}
        # 1d4+2 → [3, 6]; entries c, d, e, f should all appear
        assert seen == {"c", "d", "e", "f"}

    def test_subrange_clamps_negative(self):
        # 1d3-5 → [-4, -2], clamped to 1; always returns first entry
        t = table(seed=0)
        t.add("first", "second", "third")
        for _ in range(20):
            assert t.roll("1d3-5") == "first"

    def test_subrange_clamps_above_size(self):
        # 1d6+10 → [11, 16], clamped to size (3); always returns last entry
        t = table(seed=0)
        t.add("a", "b", "c")
        for _ in range(20):
            assert t.roll("1d6+10") == "c"


class TestTableSubTable:
    def test_sub_table_rolls_through(self):
        t = table(seed=5)
        sub = table(seed=5)
        sub.add("inner")
        t.add(sub)
        result = t.roll()
        assert result == "inner"

    def test_sub_table_not_returned_directly(self):
        t = table(seed=0)
        sub = table(seed=0)
        sub.add("deep")
        t.add(sub)
        result = t.roll()
        assert not isinstance(result, table)

    def test_mixed_entries_and_sub_table(self):
        t = table(seed=7)
        sub = table(seed=7)
        sub.add("dragon", "wyvern")
        t.add("goblin", sub, "troll")
        for _ in range(100):
            result = t.roll()
            assert result in ("goblin", "dragon", "wyvern", "troll")

    def test_mixed_all_values_reachable(self):
        # All leaf values (including sub-table entries) must be reachable
        t = table(seed=3)
        sub = table(seed=3)
        sub.add("dragon", "wyvern")
        t.add("goblin", sub, "troll")
        seen = {t.roll() for _ in range(500)}
        assert seen == {"goblin", "dragon", "wyvern", "troll"}

    def test_three_level_nesting(self):
        inner = table(seed=0)
        inner.add("deepest")
        mid = table(seed=0)
        mid.add(inner)
        outer = table(seed=0)
        outer.add(mid)
        assert outer.roll() == "deepest"

    def test_deep_nesting_never_returns_table(self):
        inner = table(seed=1)
        inner.add("leaf_a", "leaf_b")
        mid = table(seed=1)
        mid.add("mid_direct", inner)
        outer = table(seed=1)
        outer.add(mid, "outer_direct")
        for _ in range(200):
            result = outer.roll()
            assert not isinstance(result, table)
            assert result in ("leaf_a", "leaf_b", "mid_direct", "outer_direct")

    def test_deep_nesting_all_leaves_reachable(self):
        inner = table(seed=9)
        inner.add("leaf_a", "leaf_b")
        mid = table(seed=9)
        mid.add("mid_direct", inner)
        outer = table(seed=9)
        outer.add(mid, "outer_direct")
        seen = {outer.roll() for _ in range(1000)}
        assert seen == {"leaf_a", "leaf_b", "mid_direct", "outer_direct"}


class TestTableStr:
    def test_empty_table(self):
        t = table()
        assert str(t) == "(empty table)"

    def test_single_entry(self):
        t = table()
        t.add("alpha")
        assert str(t) == "1. alpha"

    def test_numbered_entries(self):
        t = table()
        t.add("a", "b", "c")
        lines = str(t).splitlines()
        assert lines[0].strip().startswith("1.")
        assert lines[1].strip().startswith("2.")
        assert lines[2].strip().startswith("3.")

    def test_sub_table_labeled(self):
        t = table()
        sub = table()
        sub.add("x")
        t.add("before", sub, "after")
        output = str(t)
        assert "[sub-table]" in output

    def test_wide_index_alignment(self):
        t = table()
        for i in range(10):
            t.add(str(i))
        output = str(t)
        # Entry 1 should be right-aligned to match entry 10
        assert " 1." in output
        assert "10." in output


class TestTableSubclass:
    def test_custom_roll_method(self):
        class AlwaysFirst(table):
            def _roll(self):
                return 1

        t = AlwaysFirst()
        t.add("first", "second", "third")
        for _ in range(10):
            assert t.roll() == "first"

    def test_custom_roll_with_dice(self):
        class D6Table(table):
            def _roll(self):
                return self._dice.roll("1d6")

        t = D6Table(seed=0)
        for i in range(1, 7):
            t.add(str(i))
        for _ in range(50):
            result = t.roll()
            assert result in [str(i) for i in range(1, 7)]

    def test_subclass_upper_half_subrange(self):
        # _roll constrains indices to the upper half
        class UpperHalfTable(table):
            def _roll(self):
                mid = self.size // 2 + 1
                return self._dice._rng.nextint(mid, self.size)

        t = UpperHalfTable(seed=4)
        t.add("a", "b", "c", "d", "e", "f")   # size 6; mid = 4
        seen = {t.roll() for _ in range(300)}
        assert seen <= {"d", "e", "f"}
        assert seen == {"d", "e", "f"}

    def test_subclass_dice_notation_subrange(self):
        # _roll uses dice notation to define a sub-range
        class TreasureTable(table):
            def _roll(self):
                return self._dice.roll("1d3+3")

        t = TreasureTable(seed=6)
        t.add("Copper", "Silver", "Gold", "Gem", "Artifact", "Legendary")
        seen = {t.roll() for _ in range(300)}
        assert seen <= {"Gem", "Artifact", "Legendary"}
        assert seen == {"Gem", "Artifact", "Legendary"}

    def test_explicit_code_overrides_roll_method(self):
        # Passing a dice code to roll() bypasses _roll entirely
        class AlwaysLast(table):
            def _roll(self):
                return self.size   # would always return last entry

        t = AlwaysLast(seed=0)
        t.add("a", "b", "c", "d", "e", "f")
        # Force entries 1–3 via explicit code
        seen = {t.roll("1d3") for _ in range(300)}
        assert seen <= {"a", "b", "c"}
        assert seen == {"a", "b", "c"}

    def test_subclass_with_nested_subtable(self):
        # Subclassed table rolling into a sub-table
        class LowerHalfTable(table):
            def _roll(self):
                return self._dice._rng.nextint(1, self.size // 2)

        sub = table(seed=5)
        sub.add("sub_x", "sub_y")

        t = LowerHalfTable(seed=5)
        t.add(sub, "plain")   # size 2; lower half = index 1 → always sub
        for _ in range(30):
            result = t.roll()
            assert result in ("sub_x", "sub_y")


class TestTableTopLevel:
    def test_exported_from_dieroller(self):
        assert hasattr(dieroller, "table")

    def test_in_all(self):
        assert "table" in dieroller.__all__

    def test_construction_via_dieroller(self):
        t = dieroller.table()
        t.add("a")
        assert t.size == 1
