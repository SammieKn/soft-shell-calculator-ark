"""Compare results across v10, v11_tudelft, and v11_viktor versions.

Produces:
- An Excel file with per-measurement comparison and per-rak summary
- Scatter plots, deviation histograms, and box plots per rak
"""

import csv
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "final_test"
OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "final_test" / "comparison_output"
)

RAKS = [
    "DYG0101",
    "DYG0201",
    "DYG0202",
    "HGG0202-01",
    "JLK0101",
    "JLK0102",
    "JLK0103",
    "JLK0204-01",
    "JLK0205",
]

COMPARE_COLUMNS = [
    "diameter",
    "soft_shell_left",
    "soft_shell_right",
]

# Human-readable labels for plots
VERSION_LABELS = {
    "v10": "v1.0 TU Delft",
    "v11_tudelft": "v1.1 TU Delft",
    "v11_viktor": "v1.1 VIKTOR",
}

METRIC_LABELS = {
    "diameter": "Diameter (mm)",
    "soft_shell_left": "Zachte schil links (mm)",
    "soft_shell_right": "Zachte schil rechts (mm)",
}


def _parse_dutch_decimal(value: str) -> float | None:
    """Convert Dutch decimal notation (comma) to float."""
    value = value.strip()
    if not value:
        return None
    return float(value.replace(",", "."))


def _extract_pile_from_measurement_id(measurement_id: str) -> str:
    """Extract pile number from measurement ID like 'DYG0101_CON.A_P1.100_BM059.rgp'.

    Returns the pile part, e.g. 'P1.100'.
    """
    # Remove path prefix if present (e.g. "IML JLK0102/")
    if "/" in measurement_id:
        measurement_id = measurement_id.split("/")[-1]
    parts = measurement_id.replace(".rgp", "").split("_")
    # Format: {rak}_{construction_part}_{pile}_{bm}
    # Pile is the third part (index 2)
    if len(parts) >= 4:
        return parts[2]
    return ""


def _extract_bm_from_measurement_id(measurement_id: str) -> str:
    """Extract BM number from measurement ID."""
    if "/" in measurement_id:
        measurement_id = measurement_id.split("/")[-1]
    parts = measurement_id.replace(".rgp", "").split("_")
    if len(parts) >= 4:
        return parts[3]
    return ""


def load_v10(rak: str) -> pd.DataFrame:
    """Load v10 CSV data for a given rak."""
    v10_dir = BASE_DIR / "v10" / rak
    if not v10_dir.exists():
        return pd.DataFrame()

    csv_files = list(v10_dir.glob("*.csv"))
    if not csv_files:
        return pd.DataFrame()

    rows = []
    with open(csv_files[0], encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        for row in reader:
            measurement_id = row[0]
            pile = _extract_pile_from_measurement_id(measurement_id)
            bm = _extract_bm_from_measurement_id(measurement_id)
            rows.append(
                {
                    "rak": rak,
                    "pile": pile,
                    "bm": bm,
                    "measurement_id": measurement_id,
                    "soft_shell_left_v10": _parse_dutch_decimal(row[1]),
                    "soft_shell_right_v10": _parse_dutch_decimal(row[2]),
                    "diameter_v10": _parse_dutch_decimal(row[5]),
                }
            )

    return pd.DataFrame(rows)


def load_v11_tudelft(rak: str) -> pd.DataFrame:
    """Load v11_tudelft Excel data for a given rak."""
    xlsx_path = BASE_DIR / "v11_tudelft" / rak / "Output.xlsx"
    if not xlsx_path.exists():
        return pd.DataFrame()

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        measurement_id = str(row[0])
        pile = _extract_pile_from_measurement_id(measurement_id)
        bm = _extract_bm_from_measurement_id(measurement_id)
        rows.append(
            {
                "rak": rak,
                "pile": pile,
                "bm": bm,
                "measurement_id_tudelft": measurement_id,
                "diameter_v11_tudelft": float(row[2]) if row[2] is not None else None,
                "sapwood_v11_tudelft": float(row[4]) if row[4] is not None else None,
                "soft_shell_left_v11_tudelft": (
                    float(row[5]) if row[5] is not None else None
                ),
                "soft_shell_right_v11_tudelft": (
                    float(row[6]) if row[6] is not None else None
                ),
            },
        )

    wb.close()
    return pd.DataFrame(rows)


def load_v11_viktor(rak: str) -> pd.DataFrame:
    """Load v11_viktor CSV data for a given rak."""
    csv_path = BASE_DIR / "v11_viktor" / "data" / rak / f"{rak}.csv"
    if not csv_path.exists():
        return pd.DataFrame()

    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pile = row["Pile id"]
            rows.append(
                {
                    "rak": rak,
                    "pile": pile,
                    "measurement_ids_viktor": row["Measurement ids"],
                    "measurement_count_viktor": int(row["Measurement count"]),
                    "diameter_v11_viktor": float(row["Diameter [mm]"]),
                    "sapwood_v11_viktor": float(row["Sapwood thickness [mm]"]),
                    "soft_shell_left_v11_viktor": float(
                        row["Soft shell entrance [mm]"]
                    ),
                    "soft_shell_right_v11_viktor": float(row["Soft shell exit [mm]"]),
                    "status_viktor": row["Status"],
                    "warnings_viktor": row["Warnings"],
                },
            )

    return pd.DataFrame(rows)


def merge_rak_data(rak: str) -> pd.DataFrame:
    """Merge all three versions for a given rak, joined on pile number."""
    df_v10 = load_v10(rak)
    df_tudelft = load_v11_tudelft(rak)
    df_viktor = load_v11_viktor(rak)

    if df_v10.empty and df_tudelft.empty:
        return pd.DataFrame()

    # Merge v10 and v11_tudelft on pile + bm (1:1 relationship)
    if not df_v10.empty and not df_tudelft.empty:
        df_merged = pd.merge(df_v10, df_tudelft, on=["rak", "pile", "bm"], how="outer")
    elif not df_v10.empty:
        df_merged = df_v10.copy()
    else:
        df_merged = df_tudelft.copy()

    # Merge v11_viktor on pile (1:n relationship - one viktor row per pile)
    if not df_viktor.empty:
        df_merged = pd.merge(df_merged, df_viktor, on=["rak", "pile"], how="outer")

    return df_merged


def compute_absolute_deviation(
    value: float | None, reference: float | None
) -> float | None:
    """Compute absolute deviation (value - reference) in mm.

    Returns None if either value is missing.
    """
    if value is None or reference is None or pd.isna(value) or pd.isna(reference):
        return None
    return value - reference


def add_deviation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add absolute deviation columns (mm) comparing versions."""
    for col in COMPARE_COLUMNS:
        col_v10 = f"{col}_v10"
        col_tudelft = f"{col}_v11_tudelft"
        col_viktor = f"{col}_v11_viktor"

        # v11_tudelft vs v10
        if col_v10 in df.columns and col_tudelft in df.columns:
            df[f"dev_mm_{col}_tudelft_vs_v10"] = df.apply(
                lambda row, c1=col_tudelft, c2=col_v10: compute_absolute_deviation(
                    row[c1], row[c2]
                ),
                axis=1,
            )

        # v11_viktor vs v10
        if col_v10 in df.columns and col_viktor in df.columns:
            df[f"dev_mm_{col}_viktor_vs_v10"] = df.apply(
                lambda row, c1=col_viktor, c2=col_v10: compute_absolute_deviation(
                    row[c1], row[c2]
                ),
                axis=1,
            )

        # v11_viktor vs v11_tudelft
        if col_tudelft in df.columns and col_viktor in df.columns:
            df[f"dev_mm_{col}_viktor_vs_tudelft"] = df.apply(
                lambda row, c1=col_viktor, c2=col_tudelft: compute_absolute_deviation(
                    row[c1], row[c2]
                ),
                axis=1,
            )

    return df


def create_summary_per_rak(df: pd.DataFrame) -> pd.DataFrame:
    """Create summary statistics per rak for absolute deviations."""
    deviation_cols = [c for c in df.columns if c.startswith("dev_mm_")]
    if not deviation_cols:
        return pd.DataFrame()

    summary_rows = []
    for rak in df["rak"].unique():
        rak_data = df[df["rak"] == rak]
        row = {"rak": rak, "n_measurements": len(rak_data)}

        for col in deviation_cols:
            values = rak_data[col].dropna()
            if len(values) > 0:
                row[f"{col}_mean"] = values.mean()
                row[f"{col}_median"] = values.median()
                row[f"{col}_std"] = values.std()
                row[f"{col}_min"] = values.min()
                row[f"{col}_max"] = values.max()
                row[f"{col}_abs_mean"] = values.abs().mean()
            else:
                row[f"{col}_mean"] = None
                row[f"{col}_median"] = None
                row[f"{col}_std"] = None
                row[f"{col}_min"] = None
                row[f"{col}_max"] = None
                row[f"{col}_abs_mean"] = None

        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


def _version_label(col_suffix: str) -> str:
    """Map column suffix to human-readable version label."""
    if col_suffix == "v10":
        return VERSION_LABELS["v10"]
    if col_suffix == "v11_tudelft":
        return VERSION_LABELS["v11_tudelft"]
    if col_suffix == "v11_viktor":
        return VERSION_LABELS["v11_viktor"]
    return col_suffix


def _metric_label(metric: str) -> str:
    """Map metric column base name to human-readable label."""
    return METRIC_LABELS.get(metric, metric)


def create_scatter_plots(df: pd.DataFrame, output_dir: Path) -> None:
    """Create scatter plots comparing versions (value vs value)."""
    comparisons = [
        ("diameter_v10", "diameter_v11_tudelft", "diameter", "v10", "v11_tudelft"),
        ("diameter_v10", "diameter_v11_viktor", "diameter", "v10", "v11_viktor"),
        (
            "diameter_v11_tudelft",
            "diameter_v11_viktor",
            "diameter",
            "v11_tudelft",
            "v11_viktor",
        ),
        (
            "soft_shell_left_v10",
            "soft_shell_left_v11_tudelft",
            "soft_shell_left",
            "v10",
            "v11_tudelft",
        ),
        (
            "soft_shell_left_v10",
            "soft_shell_left_v11_viktor",
            "soft_shell_left",
            "v10",
            "v11_viktor",
        ),
        (
            "soft_shell_left_v11_tudelft",
            "soft_shell_left_v11_viktor",
            "soft_shell_left",
            "v11_tudelft",
            "v11_viktor",
        ),
        (
            "soft_shell_right_v10",
            "soft_shell_right_v11_tudelft",
            "soft_shell_right",
            "v10",
            "v11_tudelft",
        ),
        (
            "soft_shell_right_v10",
            "soft_shell_right_v11_viktor",
            "soft_shell_right",
            "v10",
            "v11_viktor",
        ),
        (
            "soft_shell_right_v11_tudelft",
            "soft_shell_right_v11_viktor",
            "soft_shell_right",
            "v11_tudelft",
            "v11_viktor",
        ),
    ]

    for col_x, col_y, metric, ver_x, ver_y in comparisons:
        if col_x not in df.columns or col_y not in df.columns:
            continue

        valid = df[[col_x, col_y, "rak"]].dropna()
        if valid.empty:
            continue

        fig, ax = plt.subplots(figsize=(8, 6))

        for rak in valid["rak"].unique():
            rak_data = valid[valid["rak"] == rak]
            ax.scatter(rak_data[col_x], rak_data[col_y], label=rak, alpha=0.6, s=20)

        # y=x reference line
        all_vals = pd.concat([valid[col_x], valid[col_y]])
        min_val = all_vals.min()
        max_val = all_vals.max()
        ax.plot([min_val, max_val], [min_val, max_val], "k--", alpha=0.5, label="y = x")

        label_x = _version_label(ver_x)
        label_y = _version_label(ver_y)
        metric_name = _metric_label(metric)

        ax.set_xlabel(f"{metric_name} — {label_x}", fontsize=11)
        ax.set_ylabel(f"{metric_name} — {label_y}", fontsize=11)
        ax.set_title(
            f"{metric_name}\n{label_x} vs {label_y}", fontsize=13, fontweight="bold"
        )
        ax.legend(fontsize=8, loc="upper left", framealpha=0.9)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.3)

        filename = f"scatter_{metric}_{ver_x}_vs_{ver_y}.png"
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)


def _parse_deviation_col_name(col: str) -> tuple[str, str, str]:
    """Parse deviation column name to extract metric and version pair.

    E.g. 'dev_mm_diameter_viktor_vs_tudelft' -> ('diameter', 'v11_viktor', 'v11_tudelft')
    """
    # Format: dev_mm_{metric}_{ver1}_vs_{ver2}
    without_prefix = col.replace("dev_mm_", "")
    if "_viktor_vs_v10" in without_prefix:
        metric = without_prefix.replace("_viktor_vs_v10", "")
        return metric, "v11_viktor", "v10"
    if "_tudelft_vs_v10" in without_prefix:
        metric = without_prefix.replace("_tudelft_vs_v10", "")
        return metric, "v11_tudelft", "v10"
    if "_viktor_vs_tudelft" in without_prefix:
        metric = without_prefix.replace("_viktor_vs_tudelft", "")
        return metric, "v11_viktor", "v11_tudelft"
    return without_prefix, "", ""


def create_deviation_histograms(df: pd.DataFrame, output_dir: Path) -> None:
    """Create histograms of absolute deviations (mm)."""
    deviation_cols = [c for c in df.columns if c.startswith("dev_mm_")]

    for col in deviation_cols:
        values = df[col].dropna()
        if values.empty:
            continue

        metric, ver1, ver2 = _parse_deviation_col_name(col)
        metric_name = _metric_label(metric)
        label_1 = _version_label(ver1)
        label_2 = _version_label(ver2)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(values, bins=30, edgecolor="black", alpha=0.7, color="steelblue")
        ax.axvline(0, color="red", linestyle="--", alpha=0.7, label="Geen afwijking")
        ax.axvline(
            values.mean(),
            color="darkblue",
            linestyle="-",
            alpha=0.7,
            label=f"Gemiddelde: {values.mean():.1f} mm",
        )
        ax.set_xlabel(f"Afwijking {label_1} t.o.v. {label_2} (mm)", fontsize=11)
        ax.set_ylabel("Aantal metingen", fontsize=11)
        ax.set_title(
            f"{metric_name}\nAfwijking {label_1} t.o.v. {label_2}",
            fontsize=13,
            fontweight="bold",
        )
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis="y")

        filename = f"hist_{col}.png"
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)


def create_boxplots_per_rak(df: pd.DataFrame, output_dir: Path) -> None:
    """Create box plots of absolute deviation (mm) per rak."""
    deviation_cols = [c for c in df.columns if c.startswith("dev_mm_")]

    for col in deviation_cols:
        rak_groups = []
        rak_labels = []
        for rak in RAKS:
            values = df[df["rak"] == rak][col].dropna()
            if not values.empty:
                rak_groups.append(values.values)
                rak_labels.append(rak)

        if not rak_groups:
            continue

        metric, ver1, ver2 = _parse_deviation_col_name(col)
        metric_name = _metric_label(metric)
        label_1 = _version_label(ver1)
        label_2 = _version_label(ver2)

        fig, ax = plt.subplots(figsize=(10, 6))
        bp = ax.boxplot(rak_groups, tick_labels=rak_labels, patch_artist=True)
        for patch in bp["boxes"]:
            patch.set_facecolor("lightsteelblue")
        ax.axhline(0, color="red", linestyle="--", alpha=0.5, label="Geen afwijking")
        ax.set_xlabel("Rak", fontsize=11)
        ax.set_ylabel(f"Afwijking (mm)", fontsize=11)
        ax.set_title(
            f"{metric_name}\nAfwijking per rak: {label_1} t.o.v. {label_2}",
            fontsize=13,
            fontweight="bold",
        )
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend(fontsize=9)

        fig.tight_layout()
        fig.savefig(output_dir / f"boxplot_{col}.png", dpi=150)
        plt.close(fig)


def main() -> None:
    """Run the full comparison analysis."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Merge all raks
    all_data = []
    for rak in RAKS:
        print(f"Processing {rak}...")
        df_rak = merge_rak_data(rak)
        if not df_rak.empty:
            all_data.append(df_rak)

    if not all_data:
        print("No data found.")
        return

    df = pd.concat(all_data, ignore_index=True)
    df = add_deviation_columns(df)

    # Create summary
    df_summary = create_summary_per_rak(df)

    # Write Excel output
    excel_path = OUTPUT_DIR / "vergelijking_versies.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Vergelijking per meting", index=False)
        df_summary.to_excel(writer, sheet_name="Samenvatting per rak", index=False)

    print(f"\nExcel geschreven naar: {excel_path}")
    print(f"Totaal aantal rijen: {len(df)}")
    print(f"Rakken: {df['rak'].nunique()}")

    # Create plots
    print("\nPlots genereren...")
    create_scatter_plots(df, OUTPUT_DIR)
    create_deviation_histograms(df, OUTPUT_DIR)
    create_boxplots_per_rak(df, OUTPUT_DIR)

    print(f"Plots geschreven naar: {OUTPUT_DIR}")

    # Print quick summary
    print("\n=== Snelle samenvatting (afwijking in mm) ===")
    deviation_cols = [c for c in df.columns if c.startswith("dev_mm_")]
    for col in deviation_cols:
        values = df[col].dropna()
        if not values.empty:
            print(
                f"  {col}: "
                f"gemiddeld={values.mean():.1f} mm, "
                f"mediaan={values.median():.1f} mm, "
                f"std={values.std():.1f} mm, "
                f"|gem|={values.abs().mean():.1f} mm"
            )

    # Summary split by single vs multi-measurement
    if "measurement_count_viktor" in df.columns:
        print("\n=== Uitsplitsing: single vs multi-measurement palen ===")
        single = df[df["measurement_count_viktor"] == 1]
        multi = df[df["measurement_count_viktor"] > 1]

        for label, subset in [
            ("Single-measurement", single),
            ("Multi-measurement", multi),
        ]:
            if subset.empty:
                continue
            print(f"\n  {label} ({len(subset)} rijen):")
            for col in deviation_cols:
                values = subset[col].dropna()
                if not values.empty:
                    print(
                        f"    {col}: "
                        f"gem={values.mean():.1f} mm, "
                        f"mediaan={values.median():.1f} mm, "
                        f"|gem|={values.abs().mean():.1f} mm"
                    )


if __name__ == "__main__":
    main()
