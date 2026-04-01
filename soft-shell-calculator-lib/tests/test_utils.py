"""Tests for utility functions in the utils module."""

import pytest

from soft_shell_calculator_lib.utils import pair_similar_names


class TestPairSimilarNames:
    def test_pairs_similar_names(self) -> None:
        """Names differing only in a suffix should be paired."""
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.A_P1.1_BM078",
        ]
        pairs = pair_similar_names(names)
        assert len(pairs) == 1
        assert set(pairs[0]) == set(names)

    def test_does_not_pair_dissimilar_names(self) -> None:
        """Names with low similarity should not be paired."""
        names = ["measurement_alpha", "completely_different_xyz"]
        pairs = pair_similar_names(names)
        assert len(pairs) == 0

    def test_each_name_used_at_most_once(self) -> None:
        """A name should appear in at most one pair."""
        names = ["pile_A_left", "pile_A_right", "pile_A_centre"]
        pairs = pair_similar_names(names)
        used = [name for pair in pairs for name in pair]
        assert len(used) == len(set(used))

    def test_empty_input_returns_empty(self) -> None:
        assert pair_similar_names([]) == []

    def test_single_name_returns_empty(self) -> None:
        assert pair_similar_names(["only_one"]) == []

    def test_custom_threshold_stricter(self) -> None:
        """A higher threshold should produce fewer or equal pairs."""
        names = ["measurement_01_A", "measurement_01_B", "measurement_02_X"]
        pairs_loose = pair_similar_names(names, threshold=0.5)
        pairs_strict = pair_similar_names(names, threshold=0.99)
        assert len(pairs_strict) <= len(pairs_loose)

    def test_custom_threshold_lower_matches_more(self) -> None:
        """A threshold of 0.0 should pair everything possible."""
        names = ["abc", "xyz", "pqr", "lmn"]
        pairs = pair_similar_names(names, threshold=0.0)
        assert len(pairs) == 2  # all four paired into two pairs

    def test_returns_list_of_tuples(self) -> None:
        names = ["pile_001_north", "pile_001_south"]
        result = pair_similar_names(names)
        assert isinstance(result, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in result)

    def test_real_rpd_filenames(self) -> None:
        """Similar RPD filenames from the same pole session should be paired."""
        # These two names differ only in the final BM number and are clearly a pair.
        # The third name is sufficiently different that it should remain unpaired.
        names = [
            "DYG0101_CON.A_P1.1_BM077",
            "DYG0101_CON.A_P1.1_BM078",
            "DYG0202_CON.B_P2.5_BM099",
        ]
        pairs = pair_similar_names(names, threshold=0.8)
        # BM077 and BM078 differ only in the last digit — should pair
        assert len(pairs) == 1
        assert set(pairs[0]) == {"DYG0101_CON.A_P1.1_BM077", "DYG0101_CON.A_P1.1_BM078"}
