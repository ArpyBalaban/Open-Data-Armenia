from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "exports"
PRODUCT_LOOKUP_PATH = BASE_DIR / "data" / "clean" / "exports_products.csv"
OUTPUT_PATH = BASE_DIR / "data" / "clean" / "exports_country_products.csv"

OUTPUT_COLUMNS = [
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

ERKAPR_FILE_PATTERN = re.compile(
    r"^vt_artar_exp_erkapr_(?P<year_from>\d{4})_(?P<year_to>\d{4})(?P<suffix>_Ikis)?\.(?P<ext>xls|xlsx)$",
    re.IGNORECASE,
)
PRODUCT_CODE_PATTERN = re.compile(r"^\d{4}$")

# Pandas reads the legacy ArmSCII-8 bytes in these files as Latin-1 style text.
# Translating the byte values back to Unicode Armenian lets us repair country
# names, units, and any text we derive from the workbook itself.
ARMSCII_TO_UNICODE = {
    0xA2: 0x00A7,
    0xA3: 0x0589,
    0xA4: 0x0029,
    0xA5: 0x0028,
    0xA6: 0x00BB,
    0xA7: 0x00AB,
    0xA8: 0x2014,
    0xA9: 0x002E,
    0xAA: 0x055D,
    0xAB: 0x002C,
    0xAC: 0x2013,
    0xAD: 0x058A,
    0xAE: 0x2026,
    0xAF: 0x055C,
    0xB0: 0x055B,
    0xB1: 0x055E,
    0xB2: 0x0531,
    0xB3: 0x0561,
    0xB4: 0x0532,
    0xB5: 0x0562,
    0xB6: 0x0533,
    0xB7: 0x0563,
    0xB8: 0x0534,
    0xB9: 0x0564,
    0xBA: 0x0535,
    0xBB: 0x0565,
    0xBC: 0x0536,
    0xBD: 0x0566,
    0xBE: 0x0537,
    0xBF: 0x0567,
    0xC0: 0x0538,
    0xC1: 0x0568,
    0xC2: 0x0539,
    0xC3: 0x0569,
    0xC4: 0x053A,
    0xC5: 0x056A,
    0xC6: 0x053B,
    0xC7: 0x056B,
    0xC8: 0x053C,
    0xC9: 0x056C,
    0xCA: 0x053D,
    0xCB: 0x056D,
    0xCC: 0x053E,
    0xCD: 0x056E,
    0xCE: 0x053F,
    0xCF: 0x056F,
    0xD0: 0x0540,
    0xD1: 0x0570,
    0xD2: 0x0541,
    0xD3: 0x0571,
    0xD4: 0x0542,
    0xD5: 0x0572,
    0xD6: 0x0543,
    0xD7: 0x0573,
    0xD8: 0x0544,
    0xD9: 0x0574,
    0xDA: 0x0545,
    0xDB: 0x0575,
    0xDC: 0x0546,
    0xDD: 0x0576,
    0xDE: 0x0547,
    0xDF: 0x0577,
    0xE0: 0x0548,
    0xE1: 0x0578,
    0xE2: 0x0549,
    0xE3: 0x0579,
    0xE4: 0x054A,
    0xE5: 0x057A,
    0xE6: 0x054B,
    0xE7: 0x057B,
    0xE8: 0x054C,
    0xE9: 0x057C,
    0xEA: 0x054D,
    0xEB: 0x057D,
    0xEC: 0x054E,
    0xED: 0x057E,
    0xEE: 0x054F,
    0xEF: 0x057F,
    0xF0: 0x0550,
    0xF1: 0x0580,
    0xF2: 0x0551,
    0xF3: 0x0581,
    0xF4: 0x0552,
    0xF5: 0x0582,
    0xF6: 0x0553,
    0xF7: 0x0583,
    0xF8: 0x0554,
    0xF9: 0x0584,
    0xFA: 0x0555,
    0xFB: 0x0585,
    0xFC: 0x0556,
    0xFD: 0x0586,
    0xFE: 0x02BC,
    0xFF: 0x0587,
}


def fix_armenian_text(value: object) -> object:
    if pd.isna(value):
        return value

    text = str(value).strip()
    if not text:
        return text

    return "".join(chr(ARMSCII_TO_UNICODE.get(ord(char), ord(char))) for char in text)


def iter_source_files() -> list[tuple[str, int, int, Path]]:
    files: list[tuple[str, int, int, Path]] = []

    for path in SOURCE_DIR.iterdir():
        if not path.is_file():
            continue

        match = ERKAPR_FILE_PATTERN.match(path.name)
        if not match:
            continue

        year_from = int(match.group("year_from"))
        year_to = int(match.group("year_to"))
        period_label = f"{year_from}-{year_to}"
        if match.group("suffix"):
            period_label = f"I կիսամյակ {period_label}"

        files.append((period_label, year_from, year_to, path))

    return sorted(files, key=lambda item: (item[1], item[2], item[0], item[3].name))


def load_product_name_lookup() -> dict[str, str]:
    if not PRODUCT_LOOKUP_PATH.exists():
        raise SystemExit(
            f"Product lookup file not found: {PRODUCT_LOOKUP_PATH}. "
            "Run scripts/parse_exports_products.py first."
        )

    lookup_df = pd.read_csv(PRODUCT_LOOKUP_PATH, dtype={"product_code": str, "product_name": str})
    lookup_df["product_code"] = lookup_df["product_code"].str.zfill(4)
    lookup_df["product_name"] = lookup_df["product_name"].fillna("").str.strip()
    lookup_df = lookup_df[lookup_df["product_name"] != ""].drop_duplicates(subset=["product_code"])
    return dict(zip(lookup_df["product_code"], lookup_df["product_name"]))


def is_country_row(row: pd.Series) -> bool:
    first_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
    if not first_cell or PRODUCT_CODE_PATTERN.fullmatch(first_cell):
        return False

    repaired = fix_armenian_text(first_cell)
    if repaired == "ԸՆԴԱՄԵՆԸ":
        return False

    return pd.isna(row.iloc[1:]).all()


def parse_one_file(
    period_label: str,
    year_from: int,
    year_to: int,
    path: Path,
    product_name_lookup: dict[str, str],
) -> pd.DataFrame:
    # Only Sheet1 contains data in this archive. The workbook has a nested
    # country -> product layout, so we track the most recent country header and
    # attach it to each following 4-digit product row.
    df = pd.read_excel(path, sheet_name=0, header=None)

    if df.shape[1] < 6:
        raise ValueError(f"expected at least 6 columns, found {df.shape[1]}")

    df = df.iloc[:, :6].copy()
    current_country: str | None = None
    rows: list[dict[str, object]] = []

    for _, row in df.iterrows():
        if is_country_row(row):
            current_country = str(fix_armenian_text(row.iloc[0])).strip()
            continue

        product_code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if not PRODUCT_CODE_PATTERN.fullmatch(product_code):
            continue

        if not current_country:
            continue

        unit = str(fix_armenian_text(row.iloc[1])).strip() if pd.notna(row.iloc[1]) else ""
        quantity_from = pd.to_numeric(row.iloc[2], errors="coerce")
        value_from = pd.to_numeric(row.iloc[3], errors="coerce")
        quantity_to = pd.to_numeric(row.iloc[4], errors="coerce")
        value_to = pd.to_numeric(row.iloc[5], errors="coerce")

        if unit == "":
            continue

        if pd.isna(quantity_from) and pd.isna(value_from) and pd.isna(quantity_to) and pd.isna(value_to):
            continue

        rows.append(
            {
                "period_label": period_label,
                "year_from": year_from,
                "year_to": year_to,
                "country_name": current_country,
                "product_code": product_code,
                # These workbooks expose product codes but not product names, so
                # we enrich from the clean exports product parser output.
                "product_name": product_name_lookup.get(product_code, ""),
                "unit": unit,
                "quantity_from": quantity_from,
                "value_from": value_from,
                "quantity_to": quantity_to,
                "value_to": value_to,
            }
        )

    if not rows:
        raise ValueError("no country-product rows found")

    result = pd.DataFrame(rows)
    result = result[result["product_name"] != ""].copy()
    if result.empty:
        raise ValueError("no rows matched product name lookup")

    return result[OUTPUT_COLUMNS]


def main() -> None:
    files = iter_source_files()
    if not files:
        raise SystemExit(f"No matching erkapr files found in {SOURCE_DIR}")

    product_name_lookup = load_product_name_lookup()
    frames: list[pd.DataFrame] = []

    for period_label, year_from, year_to, path in files:
        try:
            frames.append(parse_one_file(period_label, year_from, year_to, path, product_name_lookup))
        except Exception as exc:
            print(f"Warning: skipped {path.name}: {exc}")

    if not frames:
        raise SystemExit("No files were parsed successfully.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(
        ["year_from", "year_to", "period_label", "country_name", "product_code", "unit"]
    ).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {OUTPUT_PATH}")
    print(f"Dataframe shape: {combined.shape}")
    print(f"Columns: {list(combined.columns)}")
    print("First 10 rows:")
    print(combined.head(10).to_string(index=False))
    print(f"Distinct period_label values: {sorted(combined['period_label'].unique().tolist())}")
    sample_countries = combined["country_name"].drop_duplicates().head(10).tolist()
    print(f"Sample country_name values: {sample_countries}")


if __name__ == "__main__":
    main()
