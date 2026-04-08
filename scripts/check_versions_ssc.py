"""
This script checks the previous version v1.0 versus the new version v1.1.

v1.0 follows from AIP directly.

v1.1 has two exports:
1. The new version of the library, which is the same as the one in the main branch of the repository.
2. The exports of soft-shell-calculator-tudelft.

Use the folder `data/test_files` to check the different versions.
Each folder contains:
- ./IML             - the .rgp files processed by soft-shell-calculator-lib
- ./Output.xlsx     - output of soft-shell-calculator-tudelft (v1.1)
- ./output_ssc.csv  - output of the previous version (v1.0)

One combined comparison Excel and aggregated comparison charts are written to
data/output/test_files/.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from soft_shell_calculator_lib.models.retaining_wall import RetainingWall
from soft_shell_calculator_lib.models.wooden_pile import WoodenPile

DATA_DIR = Path("data/test_files")
OUTPUT_DIR = Path("data/output/test_files")

# Metrics shared across all three sources.
SHARED_METRICS = [
    ("diameter_mm", "Diameter (mm)"),
    ("soft_shell_left_mm", "Soft shell left (mm)"),
    ("soft_shell_right_mm", "Soft shell right (mm)"),
]

# Metrics shared only by v1.1 and the library.
LIB_V11_METRICS = [
    ("annual_rings", "Annual rings (-)"),
    ("sapwood_mm", "Sapwood (mm)"),
]

VERSION_LABELS = {
    "v10": "v1.0 (AIP)",
    "v11": "v1.1 (TU Delft)",
    "lib": "Library",
}

VERSION_COLORS = {
    "v10": "#9c755f",
    "v11": "#4e79a7",
    "lib": "#59a14f",
}


def load_v10(folder: Path) -> pd.DataFrame:
    """Load v1.0 output from output_ssc.csv.

    Args:
        folder: Test folder containing output_ssc.csv.

    Returns:
        DataFrame indexed by measurement filename (with .rgp extension).
    """
    df = pd.read_csv(folder / "output_ssc.csv", sep=";", decimal=",")
    df = df.rename(
        columns={
            "Unnamed: 0": "measurement_id",
            "Left soft shell": "soft_shell_left_mm",
            "Right soft shell": "soft_shell_right_mm",
            "Left threshold": "left_threshold_mm",
            "Right threshold": "right_threshold_mm",
            "Berekende diameter": "diameter_mm",
        }
    )
    df["measurement_id"] = df["measurement_id"].str.strip()
    return df.set_index("measurement_id")


def load_v11(folder: Path) -> pd.DataFrame:
    """Load v1.1 output from Output.xlsx (TU Delft script).

    Args:
        folder: Test folder containing Output.xlsx.

    Returns:
        DataFrame indexed by measurement filename (with .rgp extension).
    """
    df = pd.read_excel(folder / "Output.xlsx")
    df = df.rename(
        columns={
            "Measurement ID": "measurement_id",
            "Estimated diameter (mm)": "diameter_mm",
            "Estimated number of annual rings": "annual_rings",
            "Estimated sapwood width (mm)": "sapwood_mm",
            "Estimated soft shell left (mm)": "soft_shell_left_mm",
            "Estimated soft shell right (mm)": "soft_shell_right_mm",
        }
    )
    df["measurement_id"] = df["measurement_id"].str.strip()
    return df.set_index("measurement_id")


def compute_lib(iml_folder: Path) -> pd.DataFrame:
    """Compute per-measurement results using the library.

    Loads all measurements via RetainingWall.from_directory, then wraps each
    RPDMeasurement in a single-measurement WoodenPile to obtain individual
    computed values.

    Args:
        iml_folder: Folder containing .rgp files.

    Returns:
        DataFrame indexed by measurement filename (with .rgp extension).
    """
    wall = RetainingWall.from_directory(iml_folder)

    rows = []
    for part in wall.construction_parts:
        for grouped_pile in part.wooden_piles:
            for measurement in grouped_pile.rpd_measurements:
                pile = WoodenPile(
                    id=measurement.identifier.pile_id,
                    rpd_measurements=[measurement],
                )
                filename = (
                    f"{measurement.identifier.retaining_wall_id}"
                    f"_{measurement.identifier.construction_part_id}"
                    f"_{measurement.identifier.pile_id}"
                    f"_{measurement.identifier.measurement_id}.rgp"
                )
                rows.append(
                    {
                        "measurement_id": filename,
                        "diameter_mm": pile.diameter,
                        "annual_rings": pile.number_of_annual_rings,
                        "sapwood_mm": pile.sapwood_thickness,
                        "soft_shell_left_mm": pile.soft_shell_entrance_thickness,
                        "soft_shell_right_mm": pile.soft_shell_exit_thickness,
                    }
                )

    df = pd.DataFrame(rows)
    df["measurement_id"] = df["measurement_id"].str.strip()
    return df.set_index("measurement_id")


def build_comparison(
    v10: pd.DataFrame, v11: pd.DataFrame, lib: pd.DataFrame
) -> pd.DataFrame:
    """Merge the three sources into a single wide comparison DataFrame.

    Args:
        v10: v1.0 results indexed by measurement_id.
        v11: v1.1 results indexed by measurement_id.
        lib: Library results indexed by measurement_id.

    Returns:
        Wide DataFrame with suffixes _lib, _v11, _v10, columns grouped by metric.
    """
    merged = (
        lib.add_suffix("_lib")
        .join(v11.add_suffix("_v11"), how="left")
        .join(v10.add_suffix("_v10"), how="left")
    )

    # Reorder: group related columns together, shared metrics first.
    ordered = []
    for base, _ in SHARED_METRICS:
        for suffix in ("_lib", "_v11", "_v10"):
            col = f"{base}{suffix}"
            if col in merged.columns:
                ordered.append(col)
    remaining = [c for c in merged.columns if c not in ordered]
    return merged[ordered + remaining]


def build_folder_summary(
    combined: pd.DataFrame,
    metrics: list[tuple[str, str]],
    versions: tuple[str, ...],
) -> pd.DataFrame:
    """Summarize min, mean, and max per folder for selected metrics.

    Args:
        combined: Comparison DataFrame indexed by folder and measurement_id.
        metrics: Metric name and label pairs.
        versions: Version suffixes to summarize.

    Returns:
        Long-form summary DataFrame.
    """
    rows: list[dict[str, float | str]] = []

    for folder, group in combined.groupby(level="folder"):
        for metric, label in metrics:
            for version in versions:
                column = f"{metric}_{version}"
                if column not in group.columns:
                    continue

                values = group[column].dropna()
                if values.empty:
                    continue

                rows.append(
                    {
                        "folder": str(folder),
                        "metric": metric,
                        "label": label,
                        "version": version,
                        "min": float(values.min()),
                        "mean": float(values.mean()),
                        "max": float(values.max()),
                    }
                )

    return pd.DataFrame(rows)


def save_clustered_column_charts(
    summary: pd.DataFrame,
    metrics: list[tuple[str, str]],
    versions: tuple[str, ...],
    output_dir: Path,
) -> None:
    """Save clustered column charts with min/mean/max per test object.

    Args:
        summary: Summary DataFrame from ``build_folder_summary``.
        metrics: Metric name and label pairs.
        versions: Version suffixes to include.
        output_dir: Directory to save PNG files into.
    """
    if summary.empty:
        return

    folders = sorted(summary["folder"].unique())
    x = np.arange(len(folders), dtype=float)
    width = 0.8 / max(len(versions), 1)
    offsets = (np.arange(len(versions)) - (len(versions) - 1) / 2) * width

    for metric, label in metrics:
        metric_summary = summary[summary["metric"] == metric]
        if metric_summary.empty:
            continue

        fig, ax = plt.subplots(figsize=(max(10, len(folders) * 1.2), 6))

        for idx, version in enumerate(versions):
            version_summary = (
                metric_summary[metric_summary["version"] == version]
                .set_index("folder")
                .reindex(folders)
            )
            present = version_summary["mean"].notna()
            if not present.any():
                continue

            means = version_summary.loc[present, "mean"].to_numpy(dtype=float)
            mins = version_summary.loc[present, "min"].to_numpy(dtype=float)
            maxs = version_summary.loc[present, "max"].to_numpy(dtype=float)
            positions = x[present.to_numpy()] + offsets[idx]

            ax.bar(
                positions,
                means,
                width=width,
                color=VERSION_COLORS[version],
                label=VERSION_LABELS[version],
                yerr=np.vstack((means - mins, maxs - means)),
                capsize=4,
                edgecolor="black",
                linewidth=0.5,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(folders, rotation=45, ha="right")
        ax.set_ylabel(label)
        ax.set_title(f"{label} by test object")
        ax.grid(axis="y", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / f"clustered_{metric}.png", dpi=150)
        plt.close(fig)


def process_folder(folder: Path) -> pd.DataFrame | None:
    """Run the full comparison pipeline for one test folder.

    Args:
        folder: One object folder under data/test_files/.

    Returns:
        Wide comparison DataFrame, or None if the folder is skipped.
    """
    iml_folder = folder / "IML"
    if not iml_folder.exists():
        print(f"  Skipping {folder.name} -- no IML subfolder found.")
        return None

    print(f"Processing {folder.name}...")

    v10 = load_v10(folder)
    v11 = load_v11(folder)
    lib = compute_lib(iml_folder)

    comparison = build_comparison(v10, v11, lib)

    return comparison


def main() -> None:
    """Process all test folders and write a single combined Excel file."""
    folders = sorted(p for p in DATA_DIR.iterdir() if p.is_dir())
    frames: dict[str, pd.DataFrame] = {}
    for folder in folders:
        df = process_folder(folder)
        if df is not None:
            frames[folder.name] = df

    if frames:
        combined = pd.concat(
            frames.values(),
            keys=frames.keys(),
            names=["folder", "measurement_id"],
        )
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        xlsx_path = OUTPUT_DIR / "comparison.xlsx"
        combined.to_excel(xlsx_path)
        print(f"Saved combined comparison to {xlsx_path}")

        shared_summary = build_folder_summary(
            combined,
            SHARED_METRICS,
            ("v10", "v11", "lib"),
        )
        save_clustered_column_charts(
            shared_summary,
            SHARED_METRICS,
            ("v10", "v11", "lib"),
            OUTPUT_DIR,
        )

        lib_v11_summary = build_folder_summary(
            combined,
            LIB_V11_METRICS,
            ("v11", "lib"),
        )
        save_clustered_column_charts(
            lib_v11_summary,
            LIB_V11_METRICS,
            ("v11", "lib"),
            OUTPUT_DIR,
        )
        print(f"Saved aggregated comparison charts to {OUTPUT_DIR}")

    print("Done.")


if __name__ == "__main__":
    main()
