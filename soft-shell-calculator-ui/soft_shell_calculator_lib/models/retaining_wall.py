"""Module defining the RetainingWall class."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import io
import requests
import zipfile

from soft_shell_calculator_lib.models.construction_part import ConstructionPart
from soft_shell_calculator_lib.models.rpd_measurement import RPDMeasurement
from soft_shell_calculator_lib.models.wooden_pile import WoodenPile
from soft_shell_calculator_lib.utils import get_logger

from ui_app.services.upload_service import _extract_zip_archive

from .wachtwoord import SERVICE_ACCOUNT_NAME, SERVICE_ACCOUNT_SECRET

logger = get_logger(__name__)


@dataclass
class RetainingWall:
    """A retaining wall composed of construction parts, each containing wooden piles.

    Attributes:
        id: Identifier for this retaining wall (e.g. 'DYG0101').
        construction_parts: List of construction parts belonging to this wall.
    """

    id: str
    construction_parts: list[ConstructionPart]

    @classmethod
    def from_directory(cls, path: Path) -> RetainingWall:
        """Load a RetainingWall from a directory of .rgp measurement files.

        When the directory contains files from multiple retaining walls, only
        the first wall (alphabetically by ID) is returned. Use
        :meth:`from_directory_multi` to obtain all walls.

        Args:
            path: Directory containing .rgp measurement files.

        Returns:
            A fully assembled RetainingWall instance.

        Raises:
            ValueError: If no valid .rgp files are found in the directory.
        """
        walls = cls.from_directory_multi(path)
        if len(walls) > 1:
            wall_ids = [w.id for w in walls]
            logger.warning(
                "Multiple retaining walls found in '%s': %s. "
                "Use from_directory_multi() to obtain all walls. "
                "Returning the first wall ('%s').",
                path,
                wall_ids,
                walls[0].id,
            )
        return walls[0]

    @classmethod
    def from_directory_multi(cls, path: Path) -> list[RetainingWall]:
        """Load one RetainingWall per unique wall ID from a directory of .rgp files.

        Scans the directory for all .rgp files, loads each as an RPDMeasurement,
        groups them first by ``retaining_wall_id``, then into WoodenPiles and
        ConstructionParts within each wall group.

        Files whose names do not follow the naming convention are skipped with
        a warning.

        Args:
            path: Directory containing .rgp measurement files.

        Returns:
            List of RetainingWall instances, one per unique retaining-wall ID,
            sorted alphabetically by wall ID.

        Raises:
            ValueError: If no .rgp files are found or no valid measurements
                could be loaded from the directory.
        """
        rgp_files = sorted(path.glob("*.rgp"))
        if not rgp_files:
            raise ValueError(f"No .rgp files found in '{path}'.")

        # Load measurements, skipping files with malformed names or content
        measurements: list[RPDMeasurement] = []
        for rgp_file in rgp_files:
            try:
                measurements.append(RPDMeasurement.from_rgp_file(rgp_file))
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping '%s': %s", rgp_file.name, exc)

        if not measurements:
            raise ValueError(f"No valid measurements could be loaded from '{path}'.")

        # Group measurements by retaining_wall_id
        wall_measurement_groups: dict[str, list[RPDMeasurement]] = defaultdict(list)
        for m in measurements:
            wall_measurement_groups[m.identifier.retaining_wall_id].append(m)

        walls: list[RetainingWall] = []
        for wall_id, wall_measurements in sorted(wall_measurement_groups.items()):
            # Group measurements by pile key → WoodenPile
            pile_groups: dict[tuple[str, str, str], list[RPDMeasurement]] = defaultdict(
                list
            )
            for m in wall_measurements:
                pile_groups[m.identifier.pile_key].append(m)

            # Group WoodenPiles by construction_part_id → ConstructionPart
            part_groups: dict[str, list[WoodenPile]] = defaultdict(list)
            for pile_key, pile_measurements in pile_groups.items():
                _, construction_part_id, pile_id = pile_key
                pile = WoodenPile(id=pile_id, rpd_measurements=pile_measurements)
                part_groups[construction_part_id].append(pile)

            construction_parts = [
                ConstructionPart(id=part_id, wooden_piles=piles)
                for part_id, piles in sorted(part_groups.items())
            ]
            walls.append(cls(id=wall_id, construction_parts=construction_parts))

        return walls

    @classmethod
    def from_measurements(
        cls, measurements: list[RPDMeasurement]
    ) -> list["RetainingWall"]:
        """Assemble RetainingWall instances from pre-loaded measurements.

        Groups the measurements by retaining-wall ID, then by pile and
        construction part — identical logic to :meth:`from_directory_multi`
        but without file I/O.

        Args:
            measurements: List of already-parsed RPDMeasurement objects.

        Returns:
            List of RetainingWall instances sorted alphabetically by wall ID.

        Raises:
            ValueError: If the measurements list is empty.
        """
        if not measurements:
            raise ValueError("No measurements provided.")

        wall_measurement_groups: dict[str, list[RPDMeasurement]] = defaultdict(list)
        for m in measurements:
            wall_measurement_groups[m.identifier.retaining_wall_id].append(m)

        walls: list[RetainingWall] = []
        for wall_id, wall_measurements in sorted(wall_measurement_groups.items()):
            pile_groups: dict[tuple[str, str, str], list[RPDMeasurement]] = defaultdict(
                list
            )
            for m in wall_measurements:
                pile_groups[m.identifier.pile_key].append(m)

            part_groups: dict[str, list[WoodenPile]] = defaultdict(list)
            for pile_key, pile_measurements in pile_groups.items():
                _, construction_part_id, pile_id = pile_key
                pile = WoodenPile(id=pile_id, rpd_measurements=pile_measurements)
                part_groups[construction_part_id].append(pile)

            construction_parts = [
                ConstructionPart(id=part_id, wooden_piles=piles)
                for part_id, piles in sorted(part_groups.items())
            ]
            walls.append(cls(id=wall_id, construction_parts=construction_parts))

        return walls

    @classmethod
    def from_aip(cls, kademuur_id: str) -> list[RetainingWall]:
        """Load a RetainingWall from a directory of .rgp measurement files obtained via API from AIP.

        Args:
            kademuur_id: ID of kademuur in AIP.

        Returns:
            A fully assembled RetainingWall instance.

        Raises:
            ValueError: If no valid .rgp files are found.
        """
        if kademuur_id is None:
            raise ValueError("Geen naam opgegeven.")

        # haal de data op
        token = token_uit_bmi()

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "",  # met de standaard User-Agent van requests krijg je een 403
        }

        # maak de url
        url = f"https://aip.amsterdam.nl/rest/survey?filter[objectCode]={rak}&filter[inspectionStandardType]=amsterdamBridgePoles&take=99"

        # doe de request
        resp = requests.get(url, headers=headers)

        # zoek het bestand Boorweerstandsmeting
        data = resp.json()["data"]
        for survey in data:
            if "boorweerstandsmeting" in survey["description"].lower():
                # vind de id van het bestand
                survey_id = survey["id"]
                url = f"https://aip.amsterdam.nl/rest/asset?filter[surveyId]={survey_id}&take=99"
                resp = requests.get(url, headers=headers)

                # bepaal welk bestand de zip is
                for i, d in enumerate(resp.json()["data"]):
                    if d["name"].lower().endswith("zip"):
                        zip_i = i

                # download het bestand
                url = resp.json()["data"][zip_i]["url"]

                # deze API geeft geen resultaten bij gebruik van een authorization
                resp = requests.get(url, headers={"User-Agent": ""})

                # maak er een zipfile van
                rgp_files_zip = zipfile.ZipFile(io.BytesIO(resp.content))

        # begin inlezen
        with TemporaryDirectory() as temp_dir_str:
            rgp_files = _extract_zip_archive(rgp_files_zip, temp_dir_str)
        # Load measurements, skipping files with malformed names or content
        measurements: list[RPDMeasurement] = []
        for rgp_file in rgp_files:
            try:
                measurements.append(RPDMeasurement.from_rgp_file(rgp_file))
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping '%s': %s", rgp_file.name, exc)

        # Group measurements by retaining_wall_id
        wall_measurement_groups: dict[str, list[RPDMeasurement]] = defaultdict(list)
        for m in measurements:
            wall_measurement_groups[m.identifier.retaining_wall_id].append(m)

        walls: list[RetainingWall] = []
        for wall_id, wall_measurements in sorted(wall_measurement_groups.items()):
            # Group measurements by pile key → WoodenPile
            pile_groups: dict[tuple[str, str, str], list[RPDMeasurement]] = defaultdict(
                list
            )
            for m in wall_measurements:
                pile_groups[m.identifier.pile_key].append(m)

            # Group WoodenPiles by construction_part_id → ConstructionPart
            part_groups: dict[str, list[WoodenPile]] = defaultdict(list)
            for pile_key, pile_measurements in pile_groups.items():
                _, construction_part_id, pile_id = pile_key
                pile = WoodenPile(id=pile_id, rpd_measurements=pile_measurements)
                part_groups[construction_part_id].append(pile)

            construction_parts = [
                ConstructionPart(id=part_id, wooden_piles=piles)
                for part_id, piles in sorted(part_groups.items())
            ]
            walls.append(cls(id=wall_id, construction_parts=construction_parts))

        return walls


def token_uit_bmi():
    token_headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    token_data = {
        "client_id": SERVICE_ACCOUNT_NAME,
        "client_secret": SERVICE_ACCOUNT_SECRET,
        "grant_type": "client_credentials",
    }
    token_url = "https://iam.amsterdam.nl/auth/realms/BMI/protocol/openid-connect/token"
    token_resp = requests.post(token_url, headers=token_headers, data=token_data)

    return token_resp.json()["access_token"]
