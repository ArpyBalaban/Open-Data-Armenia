from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "goods of social significance"
OUTPUT_PATH = BASE_DIR / "data" / "clean" / "essential_goods.csv"

FILE_PATTERN = re.compile(
    r"^hv_imp_goods_(?P<year>\d{4})_(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.(?P<ext>xls|xlsx)$",
    re.IGNORECASE,
)

MONTH_TO_NUMBER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

OUTPUT_COLUMNS = [
    "year",
    "month",
    "product_code",
    "product_name",
    "quantity_tons",
    "import_value",
    "customs_amount",
]

# The source files store Armenian labels with broken legacy-font glyphs.
# This dataset uses a small fixed product list, so we repair only the known
# repeated labels and leave anything unknown unchanged.
PRODUCT_NAME_FIXES = {
    "ÂéãÝÇ ÙÇë": "թռչնի միս",
    "Î³ñ³·": "կարագ",
    "´³Ý³Ý": "բանան",
    "Ü³ñÇÝç": "նարինջ",
    "òáñ»Ý": "ցորեն",
    "²ÉÛáõñ": "ալյուր",
    "´ñÇÝÓ": "բրինձ",
    "ÐÝ¹Ï³Ó³í³ñ": "հնդկաձավար",
    "Ò»Ã": "ձեթ",
    "Ø³ñ·³ñÇÝ": "մարգարին",
    "Þ³ù³ñ³í³½, ÑáõÙù": "շաքարավազ, հումք",
    "Ø³ÝÏ³Ï³Ý ëÝáõÝ¹": "մանկական սնունդ",
    "¸»Õáñ³Ûù": "դեղորայք",
    "´»Ý½ÇÝ": "բենզին",
    "¸Ç½. í³é»ÉÇù": "դիզ. վառելիք",
}


def iter_source_files() -> list[tuple[int, int, Path]]:
    files: list[tuple[int, int, Path]] = []

    for path in SOURCE_DIR.iterdir():
        if not path.is_file():
            continue

        match = FILE_PATTERN.match(path.name)
        if not match:
            continue

        year = int(match.group("year"))
        if year < 2018:
            continue

        month = MONTH_TO_NUMBER[match.group("month").lower()]
        files.append((year, month, path))

    return sorted(files, key=lambda item: (item[0], item[1], item[2].name))


def normalize_product_code(value: object) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.endswith(".0"):
        text = text[:-2]

    return text


def load_one_file(path: Path, year: int, month: int) -> pd.DataFrame:
    # These files use Sheet1 for the product table. Header rows are metadata,
    # so we read raw cells and isolate rows that look like actual data.
    df = pd.read_excel(path, sheet_name="Sheet1", header=None)

    if df.shape[1] < 6:
        raise ValueError(f"expected at least 6 columns, found {df.shape[1]}")

    df = df.iloc[:, :6].copy()
    df.columns = [
        "product_code",
        "unused",
        "product_name",
        "quantity_tons",
        "import_value",
        "customs_amount",
    ]

    df = df.drop(columns=["unused"])

    df["quantity_tons"] = pd.to_numeric(df["quantity_tons"], errors="coerce")
    df["import_value"] = pd.to_numeric(df["import_value"], errors="coerce")
    df["customs_amount"] = pd.to_numeric(df["customs_amount"], errors="coerce")

    # Keep only the main product rows and discard metadata/header rows.
    df = df[
        df["product_name"].notna()
        & df["quantity_tons"].notna()
        & df["import_value"].notna()
    ].copy()

    if df.empty:
        raise ValueError("no product rows found after filtering")

    df["product_name"] = df["product_name"].astype(str).str.strip()
    df = df[df["product_name"] != ""].copy()
    df["product_name"] = df["product_name"].replace(PRODUCT_NAME_FIXES)

    df["product_code"] = df["product_code"].apply(normalize_product_code)
    df.insert(0, "month", month)
    df.insert(0, "year", year)

    return df[OUTPUT_COLUMNS]


def main() -> None:
    files = iter_source_files()
    if not files:
        raise SystemExit(f"No matching files found in {SOURCE_DIR}")

    frames: list[pd.DataFrame] = []

    for year, month, path in files:
        try:
            frames.append(load_one_file(path, year, month))
        except Exception as exc:
            print(f"Warning: skipped {path.name}: {exc}")

    if not frames:
        raise SystemExit("No files were parsed successfully.")

    combined = pd.concat(frames, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {OUTPUT_PATH}")
    print(f"Final dataframe shape: {combined.shape}")
    print(f"Columns: {list(combined.columns)}")
    print("First 5 rows:")
    print(combined.head().to_string(index=False))


if __name__ == "__main__":
    main()
