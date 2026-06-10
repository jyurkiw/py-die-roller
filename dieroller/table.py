"""
Rollable lookup tables with optional sub-table nesting.

Exports :class:`table`, which holds an ordered list of entries and supports
random selection using either a uniform roll over the full range or any dice
notation string understood by :class:`~dieroller.dice.Dice`.
"""

from .dice import Dice


class table:
    """
    An ordered rollable lookup table.

    Entries are stored in insertion order and addressed with 1-based indices.
    Any entry may itself be a :class:`table`, which is rolled recursively when
    selected.

    :param seed: Integer seed for reproducible results.  ``None`` seeds from
        OS entropy.
    :type seed: int or None
    :param algorithm: Bit-generator algorithm passed to
        :class:`~dieroller.dice.Dice`.  One of ``'pcg64'`` (default),
        ``'philox'``, ``'sfc64'``, or ``'xoshiro256'``.
    :type algorithm: str

    Usage::

        import dieroller

        # Flat table
        t = dieroller.table()
        t.add('Goblin', 'Orc', 'Troll', 'Dragon')
        print(t)           # numbered listing
        t.size             # 4
        t.roll()           # random entry (uniform)
        t.roll('1d4')      # same, driven by 1d4 notation

        # Sub-tables
        monsters = dieroller.table()
        undead = dieroller.table()
        undead.add('Skeleton', 'Zombie', 'Wight')
        monsters.add('Goblin', undead, 'Dragon')
        monsters.roll()    # may return 'Goblin', a roll on undead, or 'Dragon'

        # Custom roll logic via subclass
        class d6_table(dieroller.table):
            def _roll(self):
                return self._dice.roll('1d6')

        t6 = d6_table()
        t6.add(*range(1, 7))
        t6.roll()          # always driven by 1d6
    """

    def __init__(self, seed=None, algorithm="pcg64"):
        self._entries = []
        self._dice = Dice(seed=seed, algorithm=algorithm)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, *values):
        """
        Append one or more entries to the table.

        Each value is appended in order.  Values may be any object, including
        nested :class:`table` instances.

        :param values: One or more entries to append.

        Example::

            t = table()
            t.add('Goblin')
            t.add('Orc', 'Troll')       # add multiple at once
            sub = table()
            sub.add('Dragon', 'Wyvern')
            t.add(sub)                  # nested table
        """
        for v in values:
            self._entries.append(v)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def size(self):
        """
        Number of entries currently in the table.

        :type: int

        Example::

            t = table()
            t.add('a', 'b', 'c')
            t.size  # 3
        """
        return len(self._entries)

    # ------------------------------------------------------------------
    # Rolling
    # ------------------------------------------------------------------

    def _roll(self) -> int:
        """
        Return a 1-based index into the table.

        The base implementation selects uniformly at random across
        ``[1, size]``.  Override this method in a subclass to change how the
        table is indexed — for example, to use a weighted or biased
        distribution.

        :returns: A 1-based integer index in ``[1, size]``.
        :rtype: int
        :raises IndexError: If the table is empty.

        Subclass example::

            class d6_table(table):
                def _roll(self):
                    return self._dice.roll('1d6')
        """
        if not self._entries:
            raise IndexError("Cannot roll on an empty table")
        return self._dice._rng.nextint(1, len(self._entries))

    def roll(self, code: str = None):
        """
        Select a random entry from the table and return it.

        When *code* is given, it is evaluated as a dice notation string (see
        :class:`~dieroller.dice.Dice`) and the result is used as a 1-based
        index, clamped to ``[1, size]``.  When *code* is omitted,
        :meth:`_roll` provides the index (default: uniform over the full
        range).

        If the selected entry is itself a :class:`table`, it is rolled
        recursively until a non-table value is reached.

        :param code: Optional dice notation string such as ``'1d6'``,
            ``'1d20+2'``, or ``'2d6kh'``.  ``None`` delegates to
            :meth:`_roll`.
        :type code: str or None
        :returns: The selected entry, or the result of recursively rolling a
            nested :class:`table`.
        :raises IndexError: If the table is empty.

        Examples::

            t = table()
            t.add('a', 'b', 'c', 'd', 'e', 'f')

            t.roll()          # uniform random entry
            t.roll('1d6')     # same range, driven by 1d6
            t.roll('1d6+3')   # bias toward higher entries, clamped to [1, 6]
        """
        if not self._entries:
            raise IndexError("Cannot roll on an empty table")

        if code is not None:
            raw = self._dice.roll(code)
            idx = max(1, min(raw, len(self._entries)))
        else:
            idx = self._roll()

        entry = self._entries[idx - 1]
        if isinstance(entry, table):
            return entry.roll()
        return entry

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self):
        """
        Return a numbered listing of all entries.

        Sub-tables are rendered inline with one level of indentation.

        :rtype: str
        """
        if not self._entries:
            return "(empty table)"

        width = len(str(self.size))
        lines = []
        for i, entry in enumerate(self._entries, 1):
            prefix = f"{i:{width}}. "
            if isinstance(entry, table):
                sub_lines = str(entry).splitlines()
                lines.append(f"{prefix}[sub-table]")
                indent = " " * (width + 2)
                lines.extend(f"{indent}{sl}" for sl in sub_lines)
            else:
                lines.append(f"{prefix}{entry}")
        return "\n".join(lines)

    def __repr__(self):
        return f"table(size={self.size})"
