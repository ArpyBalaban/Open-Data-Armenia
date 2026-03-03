from __future__ import annotations

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_PATH = CLEAN_DIR / "exports_country_products.csv"
IMPORTS_PATH = CLEAN_DIR / "imports_country_products.csv"

KEY_COLUMNS = ["period_label", "country_name", "product_code"]
EXPECTED_COLUMNS = [
    "period_label",
    "year_from",
    "year_to",
    "country_name",
    "product_code",
    "product_name",
    "unit",
    "quantity_from",
    "value_from",
    "quantity_to",
    "value_to",
]


def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV and ensure expected columns exist."""
    df = pd.read_csv(path)

    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{path.name} is missing expected columns: {missing}")

    return df


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def summarize_dataset(name: str, df: pd.DataFrame) -> None:
    """Print a validation report for one dataset."""
    print_section(name)

    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

    # Basic type cleanup for analysis
    numeric_cols = ["year_from", "year_to", "quantity_from", "value_from", "quantity_to", "value_to"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Basic null/blank normalization for text columns
    text_cols = ["period_label", "country_name", "product_code", "product_name", "unit"]
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()

    # Period info
    period_labels = sorted(df["period_label"].dropna().unique().tolist())
    print(f"\nDistinct period_label count: {len(period_labels)}")
    print(f"Period labels: {period_labels}")

    # Country info
    distinct_countries = df["country_name"].dropna()
    distinct_countries = distinct_countries[distinct_countries != ""].nunique()
    missing_country = df["country_name"].isna().sum() + (df["country_name"] == "").sum()

    print(f"\nDistinct country_name count: {distinct_countries}")
    print(f"Missing/blank country_name: {missing_country}")

    # Product info
    missing_product_name = df["product_name"].isna().sum() + (df["product_name"] == "").sum()
    missing_product_code = df["product_code"].isna().sum() + (df["product_code"] == "").sum()

    print(f"Missing/blank product_name: {missing_product_name}")
    print(f"Missing/blank product_code: {missing_product_code}")

    # Duplicates
    duplicate_count = df.duplicated(subset=KEY_COLUMNS).sum()
    print(f"\nDuplicate rows by {KEY_COLUMNS}: {duplicate_count}")

    # Warnings for suspicious subtotal rows
    suspicious_totals = df["country_name"].fillna("").str.contains("ԸՆԴԱՄԵՆԸ", case=False, na=False).sum()
    blank_countries = (df["country_name"].fillna("").str.strip() == "").sum()

    if suspicious_totals > 0:
        print(f"WARNING: Found {suspicious_totals} rows where country_name contains 'ԸՆԴԱՄԵՆԸ'")
    if blank_countries > 0:
        print(f"WARNING: Found {blank_countries} rows with blank country_name")

    # Top countries by value_to
    print("\nTop 10 countries by total value_to:")
    top_countries = (
        df.groupby("country_name", dropna=False)["value_to"]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .head(10)
    )
    print(top_countries.to_string())

    # Top product codes by value_to
    print("\nTop 10 product codes by total value_to:")
    top_products = (
        df.groupby(["product_code", "product_name"], dropna=False)["value_to"]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .head(10)
    )
    print(top_products.to_string())

    # Sample rows
    print("\nSample rows:")
    print(df.head(5).to_string(index=False))

    # Optional: show a few duplicate examples
    if duplicate_count > 0:
        print("\nSample duplicate rows:")
        dupes = df[df.duplicated(subset=KEY_COLUMNS, keep=False)].sort_values(KEY_COLUMNS).head(10)
        print(dupes.to_string(index=False))


def main() -> None:
    exports_df = load_csv(EXPORTS_PATH)
    imports_df = load_csv(IMPORTS_PATH)

    summarize_dataset("EXPORTS COUNTRY PRODUCTS", exports_df)
    summarize_dataset("IMPORTS COUNTRY PRODUCTS", imports_df)


if __name__ == "__main__":
    main()