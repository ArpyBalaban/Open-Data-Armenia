from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "foreign trade 2002-2022"
OUTPUT_PATH = BASE_DIR / "data" / "clean" / "trade_overview.csv"

OUTPUT_COLUMNS = ["year", "exports", "imports", "balance", "turnover"]

# This first parser intentionally uses only the canonical full-year "ynd"
# workbooks. Exact filename matching keeps out partial-year variants such as
# Ier / Ikis / I-IX / IIIer and avoids country/product/transport breakdowns.
CUCANISH_PATTERN = re.compile(r"^vt_ynd_cucanish_(\d{4})\.(xls|xlsx)$", re.IGNORECASE)
ARTAR_PATTERN = re.compile(
    r"^vt_artar_ynd_(\d{4})(?:_(\d{4}))?\.(xls|xlsx)$",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


def find_candidate_files() -> list[Path]:
    files: list[Path] = []

    for path in SOURCE_DIR.rglob("*"):
        if not path.is_file():
            continue

        name = path.name
        if CUCANISH_PATTERN.match(name) or ARTAR_PATTERN.match(name):
            files.append(path)

    return sorted(files)


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def find_year_columns(df: pd.DataFrame, minimum_matches: int) -> list[tuple[int, int]]:
    for _, row in df.head(12).iterrows():
        matches: list[tuple[int, int]] = []
        for col_idx, value in enumerate(row):
            text = clean_text(value)
            match = YEAR_PATTERN.search(text)
            if match:
                matches.append((col_idx, int(match.group())))

        if len(matches) >= minimum_matches:
            return matches

    raise ValueError("could not locate year headers")


def parse_numeric(value: object) -> float | None:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return None
    return float(number)


def extract_cucanish_rows(df: pd.DataFrame) -> list[dict[str, float | int]]:
    year_columns = find_year_columns(df, minimum_matches=6)[:6]

    candidates: list[tuple[str, pd.Series]] = []
    for _, row in df.iterrows():
        label = clean_text(row.iloc[0])
        numeric_count = sum(parse_numeric(row.iloc[col_idx]) is not None for col_idx, _ in year_columns[:4])
        if label and numeric_count >= 4:
            candidates.append((label, row))

    if not candidates:
        raise ValueError("no summary row found in cucanish file")

    # Older files sometimes include a final "total" row after the main trade row.
    # When it exists we prefer that grand total; otherwise we keep the first
    # numeric summary row.
    total_keywords = ("ընդամեն", "ÀÝ¹³Ù", "Ý¹³Ù")
    selected_row = candidates[0][1]
    for label, row in candidates:
        if any(keyword in label for keyword in total_keywords):
            selected_row = row
            break

    left_year = year_columns[1][1]
    right_year = year_columns[3][1]

    left_exports = parse_numeric(selected_row.iloc[year_columns[0][0]])
    right_exports = parse_numeric(selected_row.iloc[year_columns[1][0]])
    left_imports = parse_numeric(selected_row.iloc[year_columns[2][0]])
    right_imports = parse_numeric(selected_row.iloc[year_columns[3][0]])

    if None in (left_exports, right_exports, left_imports, right_imports):
        raise ValueError("missing exports/imports values in cucanish file")

    return [
        {
            "year": left_year,
            "exports": left_exports,
            "imports": left_imports,
            "balance": left_exports - left_imports,
            "turnover": left_exports + left_imports,
        },
        {
            "year": right_year,
            "exports": right_exports,
            "imports": right_imports,
            "balance": right_exports - right_imports,
            "turnover": right_exports + right_imports,
        },
    ]


def extract_artar_rows(df: pd.DataFrame) -> list[dict[str, float | int]]:
    year_columns = find_year_columns(df, minimum_matches=2)[:2]

    summary_rows: list[pd.Series] = []
    for _, row in df.iterrows():
        label = clean_text(row.iloc[0])
        left_value = parse_numeric(row.iloc[year_columns[0][0]])
        right_value = parse_numeric(row.iloc[year_columns[1][0]])
        if label and left_value is not None and right_value is not None:
            summary_rows.append(row)

    if len(summary_rows) < 3:
        raise ValueError("expected export/import/balance rows")

    exports_row, imports_row, balance_row = summary_rows[:3]

    left_year = year_columns[0][1]
    right_year = year_columns[1][1]

    left_exports = parse_numeric(exports_row.iloc[year_columns[0][0]])
    right_exports = parse_numeric(exports_row.iloc[year_columns[1][0]])
    left_imports = parse_numeric(imports_row.iloc[year_columns[0][0]])
    right_imports = parse_numeric(imports_row.iloc[year_columns[1][0]])
    left_balance = parse_numeric(balance_row.iloc[year_columns[0][0]])
    right_balance = parse_numeric(balance_row.iloc[year_columns[1][0]])

    if None in (
        left_exports,
        right_exports,
        left_imports,
        right_imports,
        left_balance,
        right_balance,
    ):
        raise ValueError("missing exports/imports/balance values in artar file")

    return [
        {
            "year": left_year,
            "exports": left_exports,
            "imports": left_imports,
            "balance": left_balance,
            "turnover": left_exports + left_imports,
        },
        {
            "year": right_year,
            "exports": right_exports,
            "imports": right_imports,
            "balance": right_balance,
            "turnover": right_exports + right_imports,
        },
    ]


def parse_one_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, header=None)
    name = path.name

    if CUCANISH_PATTERN.match(name):
        rows = extract_cucanish_rows(df)
        family_priority = 1
    elif ARTAR_PATTERN.match(name):
        rows = extract_artar_rows(df)
        family_priority = 2
    else:
        raise ValueError("unsupported file pattern")

    result = pd.DataFrame(rows)
    result["source_file"] = str(path.relative_to(BASE_DIR))
    result["family_priority"] = family_priority
    result["path_depth"] = -len(path.relative_to(BASE_DIR).parts)
    return result


def main() -> None:
    files = find_candidate_files()
    if not files:
        raise SystemExit(f"No matching files found in {SOURCE_DIR}")

    frames: list[pd.DataFrame] = []

    for path in files:
        try:
            frames.append(parse_one_file(path))
        except Exception as exc:
            print(f"Warning: skipped {path.relative_to(BASE_DIR)}: {exc}")

    if not frames:
        raise SystemExit("No files were parsed successfully.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["year"] >= 2002].copy()

    # Some years appear in multiple comparison files. Prefer the newer artar
    # family over the older cucanish family, then prefer the shallower path
    # when the workbook is duplicated elsewhere in the archive.
    combined = combined.sort_values(["year", "family_priority", "path_depth"])
    combined = combined.drop_duplicates(subset=["year"], keep="last")

    for column in OUTPUT_COLUMNS:
        combined[column] = pd.to_numeric(combined[column], errors="coerce")

    combined = combined.sort_values("year")[OUTPUT_COLUMNS].reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {OUTPUT_PATH}")
    print(f"Dataframe shape: {combined.shape}")
    print(f"Columns: {list(combined.columns)}")
    print("First 10 rows:")
    print(combined.head(10).to_string(index=False))
    print(f"Min year: {int(combined['year'].min())}")
    print(f"Max year: {int(combined['year'].max())}")


if __name__ == "__main__":
    main()
