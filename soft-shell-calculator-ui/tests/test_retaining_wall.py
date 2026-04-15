"""Tests for RetainingWall.from_directory."""

from pathlib import Path

import pytest

from soft_shell_calculator_lib.models.retaining_wall import RetainingWall


class TestRetainingWallFromDirectory:
    def test_loads_from_real_directory(self, all_rgp_paths: list[Path]) -> None:
        """Should assemble a RetainingWall from the test dataset directory."""
        directory = all_rgp_paths[0].parent
        wall = RetainingWall.from_directory(directory)
        assert isinstance(wall, RetainingWall)

    def test_wall_id_matches_files(self, all_rgp_paths: list[Path]) -> None:
        """Wall id should match the retaining wall id in the filenames."""
        directory = all_rgp_paths[0].parent
        expected_id = all_rgp_paths[0].stem.split("_")[0]
        wall = RetainingWall.from_directory(directory)
        assert wall.id == expected_id

    def test_has_construction_parts(self, all_rgp_paths: list[Path]) -> None:
        directory = all_rgp_paths[0].parent
        wall = RetainingWall.from_directory(directory)
        assert len(wall.construction_parts) > 0

    def test_construction_parts_have_piles(self, all_rgp_paths: list[Path]) -> None:
        directory = all_rgp_paths[0].parent
        wall = RetainingWall.from_directory(directory)
        for part in wall.construction_parts:
            assert len(part.wooden_piles) > 0

    def test_all_measurements_are_assigned(self, all_rgp_paths: list[Path]) -> None:
        """Total number of measurements across all piles should equal file count."""
        directory = all_rgp_paths[0].parent
        wall = RetainingWall.from_directory(directory)
        total = sum(
            len(pile.rpd_measurements)
            for part in wall.construction_parts
            for pile in part.wooden_piles
        )
        assert total == len(all_rgp_paths)

    def test_raises_on_empty_directory(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="No .rgp files"):
            RetainingWall.from_directory(tmp_path)
