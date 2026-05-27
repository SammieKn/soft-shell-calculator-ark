"""Tests for RetainingWall.from_directory, from_directory_multi, and from_measurements."""

import json
from pathlib import Path

import pytest

from soft_shell_calculator_lib.models.retaining_wall import RetainingWall
from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from tests.conftest import make_rgp_bytes


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


class TestRetainingWallFromDirectoryMulti:
    def _write_rgp(self, directory: Path, filename: str, content: bytes) -> None:
        (directory / filename).write_bytes(content)

    def test_single_wall_returns_one_element_list(self, tmp_path: Path) -> None:
        """A directory with one wall's files should return a list with one wall."""
        for pile_id in ("P1.1", "P1.2"):
            filename, content = make_rgp_bytes(
                wall_id="DYG0101", pile_id=pile_id, measurement_id="BM001"
            )
            self._write_rgp(tmp_path, filename, content)

        walls = RetainingWall.from_directory_multi(tmp_path)

        assert len(walls) == 1
        assert walls[0].id == "DYG0101"

    def test_two_walls_return_two_elements(self, tmp_path: Path) -> None:
        """A directory with files from two walls should return two RetainingWalls."""
        filename_a, content_a = make_rgp_bytes(
            wall_id="AAA0001", pile_id="P1.1", measurement_id="BM001"
        )
        filename_b, content_b = make_rgp_bytes(
            wall_id="ZZZ9999", pile_id="P1.1", measurement_id="BM001"
        )
        self._write_rgp(tmp_path, filename_a, content_a)
        self._write_rgp(tmp_path, filename_b, content_b)

        walls = RetainingWall.from_directory_multi(tmp_path)

        assert len(walls) == 2

    def test_two_walls_have_correct_ids(self, tmp_path: Path) -> None:
        """Wall IDs should match the retaining-wall prefix in filenames."""
        filename_a, content_a = make_rgp_bytes(
            wall_id="LEG0402", pile_id="P2.24", measurement_id="BM065"
        )
        filename_b, content_b = make_rgp_bytes(
            wall_id="LYG0902", pile_id="P1.1", measurement_id="BM108"
        )
        self._write_rgp(tmp_path, filename_a, content_a)
        self._write_rgp(tmp_path, filename_b, content_b)

        walls = RetainingWall.from_directory_multi(tmp_path)
        wall_ids = {w.id for w in walls}

        assert wall_ids == {"LEG0402", "LYG0902"}

    def test_walls_are_sorted_alphabetically(self, tmp_path: Path) -> None:
        """Returned walls are ordered alphabetically by wall ID."""
        for wall_id in ("ZZZ9999", "AAA0001", "MMM0500"):
            filename, content = make_rgp_bytes(
                wall_id=wall_id, pile_id="P1.1", measurement_id="BM001"
            )
            self._write_rgp(tmp_path, filename, content)

        walls = RetainingWall.from_directory_multi(tmp_path)

        assert [w.id for w in walls] == ["AAA0001", "MMM0500", "ZZZ9999"]

    def test_measurements_are_assigned_to_correct_wall(self, tmp_path: Path) -> None:
        """Each measurement is assigned only to its own retaining wall."""
        for pile_id in ("P1.1", "P1.2"):
            filename, content = make_rgp_bytes(
                wall_id="LEG0402", pile_id=pile_id, measurement_id="BM001"
            )
            self._write_rgp(tmp_path, filename, content)
        filename, content = make_rgp_bytes(
            wall_id="LYG0902", pile_id="P1.1", measurement_id="BM001"
        )
        self._write_rgp(tmp_path, filename, content)

        walls = RetainingWall.from_directory_multi(tmp_path)
        by_id = {w.id: w for w in walls}

        leg_total = sum(
            len(pile.rpd_measurements)
            for part in by_id["LEG0402"].construction_parts
            for pile in part.wooden_piles
        )
        lyg_total = sum(
            len(pile.rpd_measurements)
            for part in by_id["LYG0902"].construction_parts
            for pile in part.wooden_piles
        )
        assert leg_total == 2
        assert lyg_total == 1

    def test_raises_on_empty_directory(self, tmp_path: Path) -> None:
        """Should raise ValueError when no .rgp files are found."""
        with pytest.raises(ValueError, match="No .rgp files"):
            RetainingWall.from_directory_multi(tmp_path)

    def test_from_directory_returns_first_alphabetical_wall(
        self, tmp_path: Path
    ) -> None:
        """from_directory should return the first alphabetical wall when multiple exist."""
        filename_a, content_a = make_rgp_bytes(
            wall_id="AAA0001", pile_id="P1.1", measurement_id="BM001"
        )
        filename_b, content_b = make_rgp_bytes(
            wall_id="ZZZ9999", pile_id="P1.1", measurement_id="BM001"
        )
        self._write_rgp(tmp_path, filename_a, content_a)
        self._write_rgp(tmp_path, filename_b, content_b)

        wall = RetainingWall.from_directory(tmp_path)

        assert wall.id == "AAA0001"


class TestRetainingWallFromMeasurements:
    def _load_measurements(
        self, tmp_path: Path, specs: list[tuple[str, str, str]]
    ) -> list[RPDMeasurement]:
        """Write .rgp files and parse them into RPDMeasurement objects."""
        measurements = []
        for wall_id, pile_id, measurement_id in specs:
            filename, content = make_rgp_bytes(
                wall_id=wall_id, pile_id=pile_id, measurement_id=measurement_id
            )
            path = tmp_path / filename
            path.write_bytes(content)
            measurements.append(RPDMeasurement.from_rgp_file(path))
        return measurements

    def test_single_wall_from_measurements(self, tmp_path: Path) -> None:
        """Should assemble one wall from pre-loaded measurements."""
        measurements = self._load_measurements(
            tmp_path,
            [
                ("DYG0101", "P1.1", "BM001"),
                ("DYG0101", "P1.2", "BM002"),
            ],
        )

        walls = RetainingWall.from_measurements(measurements)

        assert len(walls) == 1
        assert walls[0].id == "DYG0101"

    def test_two_walls_from_measurements(self, tmp_path: Path) -> None:
        """Should split measurements into separate walls by ID."""
        measurements = self._load_measurements(
            tmp_path,
            [
                ("LEG0402", "P1.1", "BM001"),
                ("LYG0902", "P1.1", "BM002"),
            ],
        )

        walls = RetainingWall.from_measurements(measurements)

        assert len(walls) == 2
        assert {w.id for w in walls} == {"LEG0402", "LYG0902"}

    def test_walls_sorted_alphabetically(self, tmp_path: Path) -> None:
        measurements = self._load_measurements(
            tmp_path,
            [
                ("ZZZ9999", "P1.1", "BM001"),
                ("AAA0001", "P1.1", "BM002"),
            ],
        )

        walls = RetainingWall.from_measurements(measurements)

        assert [w.id for w in walls] == ["AAA0001", "ZZZ9999"]

    def test_measurements_grouped_into_piles(self, tmp_path: Path) -> None:
        """Two measurements with the same pile key should end up in one WoodenPile."""
        measurements = self._load_measurements(
            tmp_path,
            [
                ("DYG0101", "P1.1", "BM001"),
                ("DYG0101", "P1.1", "BM002"),
            ],
        )

        walls = RetainingWall.from_measurements(measurements)
        pile = walls[0].construction_parts[0].wooden_piles[0]

        assert len(pile.rpd_measurements) == 2

    def test_raises_on_empty_list(self) -> None:
        with pytest.raises(ValueError, match="No measurements"):
            RetainingWall.from_measurements([])

    def test_equivalent_to_from_directory_multi(
        self, all_rgp_paths: list[Path]
    ) -> None:
        """from_measurements with manually loaded files should produce the same result as from_directory_multi."""
        directory = all_rgp_paths[0].parent
        walls_from_dir = RetainingWall.from_directory_multi(directory)

        measurements = [RPDMeasurement.from_rgp_file(p) for p in all_rgp_paths]
        walls_from_measurements = RetainingWall.from_measurements(measurements)

        assert len(walls_from_dir) == len(walls_from_measurements)
        for wd, wm in zip(walls_from_dir, walls_from_measurements):
            assert wd.id == wm.id
            assert len(wd.construction_parts) == len(wm.construction_parts)
