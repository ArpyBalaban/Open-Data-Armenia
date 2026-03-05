from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from babel import Locale
from babel.core import get_global


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"

EXPORTS_COUNTRY_PRODUCTS_PATH = CLEAN_DIR / "exports_country_products.csv"
IMPORTS_COUNTRY_PRODUCTS_PATH = CLEAN_DIR / "imports_country_products.csv"
EXPORTS_PRODUCTS_PATH = CLEAN_DIR / "exports_products.csv"
IMPORTS_PRODUCTS_PATH = CLEAN_DIR / "imports_products.csv"

COUNTRY_OUTPUT_PATH = CLEAN_DIR / "country_translations.csv"
PRODUCT_OUTPUT_PATH = CLEAN_DIR / "product_translations.csv"
HS_REFERENCE_PATH = BASE_DIR / "data" / "reference" / "harmonized-system.csv"

ARMENIAN_WORD_RE = re.compile(r"[\u0531-\u0587]+")

# Country names that do not map cleanly via CLDR Armenian territory names.
COUNTRY_OVERRIDES = {
    "Անհայտ երկիր": {"country_name_en": "Unknown country", "iso3": ""},
    "ԵՎՐՈՊԱԿԱՆ ՄԻՈՒԹՅՈՒՆ": {"country_name_en": "European Union", "iso3": ""},
    "Թայվան, Չինաստանի նահանգ": {"country_name_en": "Taiwan", "iso3": "TWN"},
    "Իրանի Իսլամական Հանրապետություն": {"country_name_en": "Iran", "iso3": "IRN"},
    "Լիբիական Արաբական Ջամահիրիա": {"country_name_en": "Libya", "iso3": "LBY"},
    "Մոլդովայի Հանրապետություն": {"country_name_en": "Moldova", "iso3": "MDA"},
    "ՆՀՀ Մակեդոնիա": {"country_name_en": "North Macedonia", "iso3": "MKD"},
    "Պաղեստինյան տարածք, գրավյալ": {"country_name_en": "Palestine", "iso3": "PSE"},
    "Սիրիայի Արաբական Հանրապետություն": {"country_name_en": "Syria", "iso3": "SYR"},
    "Տանզանիայի Միացյալ Հանրապետություն": {"country_name_en": "Tanzania", "iso3": "TZA"},
    "Կորեա, ԺԺՀ": {"country_name_en": "North Korea", "iso3": "PRK"},
    "Կորեայի Հանրապետություն": {"country_name_en": "South Korea", "iso3": "KOR"},
    "Սեն Մարտին (Նիդերլանդներ)": {"country_name_en": "Sint Maarten (Dutch part)", "iso3": "SXM"},
    "Վիրջինյան Կղզիներ (ԱՄՆ)": {"country_name_en": "U.S. Virgin Islands", "iso3": "VIR"},
    "Անգիլիա": {"country_name_en": "Anguilla", "iso3": "AIA"},
    "Բահամներ": {"country_name_en": "Bahamas", "iso3": "BHS"},
    "Բերմուդա": {"country_name_en": "Bermuda", "iso3": "BMU"},
    "Բրունեյ Դարուսսալամ": {"country_name_en": "Brunei Darussalam", "iso3": "BRN"},
    "Էրիտրեա": {"country_name_en": "Eritrea", "iso3": "ERI"},
    "Լիխտենշտայն": {"country_name_en": "Liechtenstein", "iso3": "LIE"},
    "Կաբո-Վերդե": {"country_name_en": "Cabo Verde", "iso3": "CPV"},
    "Կայմանի Կղզիներ": {"country_name_en": "Cayman Islands", "iso3": "CYM"},
    "Կոմորներ": {"country_name_en": "Comoros", "iso3": "COM"},
    "Կոնգոյի Ժողովրդավարական Հանրապետություն": {
        "country_name_en": "Democratic Republic of the Congo",
        "iso3": "COD",
    },
    "Կոստա-Ռիկա": {"country_name_en": "Costa Rica", "iso3": "CRI"},
    "Կոտ-դ՛Իվուար": {"country_name_en": "Cote d'Ivoire", "iso3": "CIV"},
    "Հաիթի": {"country_name_en": "Haiti", "iso3": "HTI"},
    "Հարավային Աֆրիկա": {"country_name_en": "South Africa", "iso3": "ZAF"},
    "Հոնկոնգ": {"country_name_en": "Hong Kong", "iso3": "HKG"},
    "Ղըրղզստան": {"country_name_en": "Kyrgyzstan", "iso3": "KGZ"},
    "Մակաո": {"country_name_en": "Macao", "iso3": "MAC"},
    "Մավրիկիա": {"country_name_en": "Mauritius", "iso3": "MUS"},
    "Մյանմա": {"country_name_en": "Myanmar", "iso3": "MMR"},
    "Նիդերլանդներ": {"country_name_en": "Netherlands", "iso3": "NLD"},
    "Չեխիայի Հանրապետություն": {"country_name_en": "Czech Republic", "iso3": "CZE"},
    "Չերնոգորիա": {"country_name_en": "Montenegro", "iso3": "MNE"},
    "Պապուա-Նոր Գվինեա": {"country_name_en": "Papua New Guinea", "iso3": "PNG"},
    "Պուերտո-Ռիկո": {"country_name_en": "Puerto Rico", "iso3": "PRI"},
    "Ջամայկա": {"country_name_en": "Jamaica", "iso3": "JAM"},
    "Ռուսաստանի Դաշնություն": {"country_name_en": "Russian Federation", "iso3": "RUS"},
    "Սան Տոմե եւ Պրինսիպի": {"country_name_en": "Sao Tome and Principe", "iso3": "STP"},
    "Սան Տոմե և Պրինսիպի": {"country_name_en": "Sao Tome and Principe", "iso3": "STP"},
    "Սեյշելյներ": {"country_name_en": "Seychelles", "iso3": "SYC"},
    "Սողոմոնյան Կղզիներ": {"country_name_en": "Solomon Islands", "iso3": "SLB"},
    "Սուրբ Հեղինե": {"country_name_en": "Saint Helena", "iso3": "SHN"},
    "Սվազիլենդ": {"country_name_en": "Eswatini", "iso3": "SWZ"},
    "Ֆարերյան Կղզիներ": {"country_name_en": "Faroe Islands", "iso3": "FRO"},
}

# High-value phrase-level translations for product labels. Longer phrases are
# applied first, then word-level mapping and transliteration fill the gaps.
PHRASE_TRANSLATIONS = {
    "Խոշոր եղջրավոր անասուններ կենդանի": "Live bovine animals",
    "Խոշոր եղջրավոր անասունի միս թարմ կամ պաղեցրած": "Fresh or chilled bovine meat",
    "Խոշոր եղջրավոր անասունի միս` սառեցրած": "Frozen bovine meat",
    "Ընտանի թռչնի միս եւ մսամթերք": "Poultry meat and edible offal",
    "Ոչխարի կամ այծի միս": "Sheep or goat meat",
    "Ձուկ թարմ կամ պաղեցրած": "Fresh or chilled fish",
    "Ձուկ սառեցրած": "Frozen fish",
    "Կաթ եւ սերուցք": "Milk and cream",
    "Թռչնի ձու կճեպով": "Bird eggs in shell",
    "Կարագ; կաթնային մածուկ": "Butter and dairy spreads",
    "Պանիր եւ կաթնաշոռ": "Cheese and curd",
    "Բանջարեղեն, մրգեր, ընկուզեղեն պաhածոյացված քացախով": "Vegetables, fruit and nuts preserved in vinegar",
    "Հագուստ եւ հագուստի պարագաներ": "Apparel and clothing accessories",
    "Սարքեր եւ ապարատուրա ավտոմատ կարգավորման կամ ղեկավարման": "Automatic regulating or controlling instruments",
    "Հոսանքափոխարկիչ էլեկտրական, կոճ ինդուկտիվության եւ դրոսել": "Electrical transformers, inductors and chokes",
    "Լոլիկի մածուկ": "Tomato paste",
}

WORD_TRANSLATIONS = {
    "այլ": "other",
    "կամ": "or",
    "եւ": "and",
    "և": "and",
    "ոչ": "not",
    "նման": "similar",
    "դրանց": "their",
    "մասեր": "parts",
    "համար": "for",
    "արտադրանք": "products",
    "իրեր": "articles",
    "բնական": "natural",
    "արհեստական": "artificial",
    "սինթետիկ": "synthetic",
    "կենդանի": "live",
    "կենդանիներ": "animals",
    "միս": "meat",
    "ձուկ": "fish",
    "կաթ": "milk",
    "պանիր": "cheese",
    "կարագ": "butter",
    "մածուն": "yogurt",
    "թարմ": "fresh",
    "պաղեցրած": "chilled",
    "սառեցրած": "frozen",
    "մշակած": "processed",
    "թռչնի": "poultry",
    "ձու": "eggs",
    "պատրաստի": "prepared",
    "պահածոյացված": "preserved",
    "խտացրած": "concentrated",
    "փոշի": "powder",
    "ճարպ": "fat",
    "ձեթ": "oil",
    "շաքար": "sugar",
    "ալյուր": "flour",
    "հաց": "bread",
    "մեքենա": "machine",
    "մեքենաներ": "machines",
    "սարք": "device",
    "սարքեր": "devices",
    "սարքավորում": "equipment",
    "ապարատ": "apparatus",
    "ապարատուրա": "apparatus",
    "էլեկտրական": "electrical",
    "օպտիկ": "optical",
    "քիմիական": "chemical",
    "մետաղ": "metal",
    "մետաղից": "of metal",
    "պլաստմասսայից": "of plastics",
    "պողպատից": "of steel",
    "կաշվից": "of leather",
    "թղթից": "of paper",
    "ստվարաթղթից": "of cardboard",
    "գործվածք": "fabric",
    "հագուստ": "clothing",
    "կոշիկ": "footwear",
    "կոշիկի": "footwear",
    "գրիչներ": "pens",
    "մատիտներ": "pencils",
    "գործիք": "tool",
    "գործիքներ": "tools",
    "խողովակ": "pipe",
    "խողովակներ": "pipes",
    "շինարարական": "construction",
    "կենցաղային": "household",
    "տեխնիկական": "technical",
    "արդյունաբերական": "industrial",
    "գյուղատնտեսական": "agricultural",
    "դիրքի": "heading",
    "դիրքերում": "headings",
    "բացի": "excluding",
    "ներառյալ": "including",
}

# Armenian -> Latin transliteration fallback (deterministic).
ARMENIAN_TO_LATIN = {
    "Ա": "A",
    "Բ": "B",
    "Գ": "G",
    "Դ": "D",
    "Ե": "Ye",
    "Զ": "Z",
    "Է": "E",
    "Ը": "Y",
    "Թ": "T",
    "Ժ": "Zh",
    "Ի": "I",
    "Լ": "L",
    "Խ": "Kh",
    "Ծ": "Ts",
    "Կ": "K",
    "Հ": "H",
    "Ձ": "Dz",
    "Ղ": "Gh",
    "Ճ": "Ch",
    "Մ": "M",
    "Յ": "Y",
    "Ն": "N",
    "Շ": "Sh",
    "Ո": "Vo",
    "Չ": "Ch",
    "Պ": "P",
    "Ջ": "J",
    "Ռ": "R",
    "Ս": "S",
    "Վ": "V",
    "Տ": "T",
    "Ր": "R",
    "Ց": "Ts",
    "Ւ": "V",
    "Փ": "P",
    "Ք": "Q",
    "Օ": "O",
    "Ֆ": "F",
    "և": "ev",
    "ա": "a",
    "բ": "b",
    "գ": "g",
    "դ": "d",
    "ե": "e",
    "զ": "z",
    "է": "e",
    "ը": "y",
    "թ": "t",
    "ժ": "zh",
    "ի": "i",
    "լ": "l",
    "խ": "kh",
    "ծ": "ts",
    "կ": "k",
    "հ": "h",
    "ձ": "dz",
    "ղ": "gh",
    "ճ": "ch",
    "մ": "m",
    "յ": "y",
    "ն": "n",
    "շ": "sh",
    "ո": "o",
    "չ": "ch",
    "պ": "p",
    "ջ": "j",
    "ռ": "r",
    "ս": "s",
    "վ": "v",
    "տ": "t",
    "ր": "r",
    "ց": "ts",
    "ւ": "v",
    "փ": "p",
    "ք": "q",
    "օ": "o",
    "ֆ": "f",
}


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_hy(text: str) -> str:
    text = normalize_spaces(text)
    text = text.replace("եւ", "և")
    return text


def transliterate_hy(text: str) -> str:
    return "".join(ARMENIAN_TO_LATIN.get(ch, ch) for ch in text)


def apply_phrase_translations(text: str) -> tuple[str, int]:
    updated = text
    hits = 0
    for src in sorted(PHRASE_TRANSLATIONS.keys(), key=len, reverse=True):
        if src in updated:
            updated = updated.replace(src, PHRASE_TRANSLATIONS[src])
            hits += 1
    return updated, hits


def translate_product_name(text: str) -> tuple[str, int]:
    text = normalize_spaces(text)
    text, hits = apply_phrase_translations(text)

    def replace_word(match: re.Match[str]) -> str:
        nonlocal hits
        word = match.group(0)
        normalized = word.replace("եւ", "և")
        if normalized in WORD_TRANSLATIONS:
            hits += 1
            return WORD_TRANSLATIONS[normalized]
        return transliterate_hy(normalized)

    translated = re.sub(r"[\u0531-\u0587]+", replace_word, text)
    translated = normalize_spaces(translated)
    return translated, hits


def build_iso2_to_iso3_map() -> dict[str, str]:
    aliases = get_global("territory_aliases")
    iso2_candidates: dict[str, list[str]] = defaultdict(list)

    for alpha3, mapped in aliases.items():
        if (
            len(alpha3) == 3
            and alpha3.isalpha()
            and isinstance(mapped, list)
            and len(mapped) == 1
            and len(mapped[0]) == 2
            and mapped[0].isalpha()
        ):
            iso2_candidates[mapped[0]].append(alpha3)

    iso2_to_iso3: dict[str, str] = {}
    for iso2, candidates in iso2_candidates.items():
        preferred = [c for c in candidates if c[:2] == iso2]
        if preferred:
            iso2_to_iso3[iso2] = sorted(preferred)[0]
        else:
            iso2_to_iso3[iso2] = sorted(candidates)[0]

    return iso2_to_iso3


def build_country_lookup(unique_countries: list[str]) -> tuple[pd.DataFrame, list[str]]:
    hy_locale = Locale.parse("hy")
    en_locale = Locale.parse("en")
    iso2_to_iso3 = build_iso2_to_iso3_map()

    hy_name_to_iso2: dict[str, str] = {}
    for iso2, hy_name in hy_locale.territories.items():
        hy_name_to_iso2[normalize_hy(str(hy_name))] = iso2

    rows: list[dict[str, str]] = []
    uncertain: list[str] = []

    for country_am in unique_countries:
        normalized = normalize_hy(country_am)

        if normalized in COUNTRY_OVERRIDES:
            override = COUNTRY_OVERRIDES[normalized]
            rows.append(
                {
                    "country_name_am": country_am,
                    "country_name_en": override["country_name_en"],
                    "iso3": override["iso3"],
                }
            )
            continue

        iso2 = hy_name_to_iso2.get(normalized)
        if iso2:
            country_name_en = normalize_spaces(str(en_locale.territories.get(iso2, "")))
            iso3 = iso2_to_iso3.get(iso2, "")
            rows.append(
                {
                    "country_name_am": country_am,
                    "country_name_en": country_name_en if country_name_en else transliterate_hy(country_am),
                    "iso3": iso3,
                }
            )
            if not country_name_en or not iso3:
                uncertain.append(country_am)
            continue

        rows.append(
            {
                "country_name_am": country_am,
                "country_name_en": transliterate_hy(country_am),
                "iso3": "",
            }
        )
        uncertain.append(country_am)

    df = pd.DataFrame(rows).sort_values("country_name_am").reset_index(drop=True)
    return df, uncertain


def pick_representative_armenian_name(group: pd.Series) -> str:
    # Deterministic selection if multiple Armenian names appear for one code:
    # highest frequency first, then shortest label, then lexicographic order.
    # In current cleaned data each product code maps to a single Armenian name.
    counts = Counter(name.strip() for name in group.dropna().astype(str) if name.strip())
    if not counts:
        return ""

    ranked = sorted(counts.items(), key=lambda x: (-x[1], len(x[0]), x[0]))
    return ranked[0][0]


def load_hs_4digit_reference() -> pd.DataFrame:
    if not HS_REFERENCE_PATH.exists():
        raise SystemExit(
            f"HS reference file not found: {HS_REFERENCE_PATH}. "
            "Download data/reference/harmonized-system.csv first."
        )

    hs_df = pd.read_csv(HS_REFERENCE_PATH, dtype={"hscode": str, "description": str, "level": int})
    hs_df["hscode"] = hs_df["hscode"].astype(str).str.zfill(4)
    hs_df = hs_df[hs_df["level"] == 4].copy()
    hs_df["description"] = hs_df["description"].astype(str).str.strip()
    hs_df = hs_df[hs_df["description"] != ""]
    hs_df = hs_df.drop_duplicates(subset=["hscode"], keep="first")
    return hs_df[["hscode", "description"]]


def build_product_lookup(product_df: pd.DataFrame, hs_4digit_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], int]:
    grouped = (
        product_df.groupby("product_code", as_index=False)["product_name_am"]
        .apply(pick_representative_armenian_name)
        .rename(columns={"product_name_am": "product_name_am"})
    )
    grouped["product_name_am"] = grouped["product_name_am"].astype(str).str.strip()

    merged = grouped.merge(hs_4digit_df, how="left", left_on="product_code", right_on="hscode")
    matched_count = int(merged["description"].notna().sum())

    missing_codes = sorted(merged.loc[merged["description"].isna(), "product_code"].astype(str).tolist())
    merged["product_name_en"] = merged["description"]
    merged.loc[merged["product_name_en"].isna(), "product_name_en"] = (
        merged["product_name_am"] + " (NEEDS REVIEW)"
    )

    df = merged[["product_code", "product_name_am", "product_name_en"]]
    df = df.sort_values("product_code").reset_index(drop=True)
    return df, missing_codes, matched_count


def main() -> None:
    exports_country_products = pd.read_csv(EXPORTS_COUNTRY_PRODUCTS_PATH)
    imports_country_products = pd.read_csv(IMPORTS_COUNTRY_PRODUCTS_PATH)
    exports_products = pd.read_csv(EXPORTS_PRODUCTS_PATH, dtype={"product_code": str})
    imports_products = pd.read_csv(IMPORTS_PRODUCTS_PATH, dtype={"product_code": str})

    unique_countries = sorted(
        set(exports_country_products["country_name"].dropna().astype(str).map(normalize_spaces))
        | set(imports_country_products["country_name"].dropna().astype(str).map(normalize_spaces))
    )

    product_source = pd.concat(
        [
            exports_products[["product_code", "product_name"]].rename(columns={"product_name": "product_name_am"}),
            imports_products[["product_code", "product_name"]].rename(columns={"product_name": "product_name_am"}),
        ],
        ignore_index=True,
    )
    product_source["product_code"] = product_source["product_code"].astype(str).str.zfill(4)
    product_source["product_name_am"] = product_source["product_name_am"].astype(str).str.strip()

    hs_4digit_df = load_hs_4digit_reference()
    country_df, country_uncertain = build_country_lookup(unique_countries)
    product_df, missing_product_codes, matched_product_codes = build_product_lookup(product_source, hs_4digit_df)

    COUNTRY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    country_df.to_csv(COUNTRY_OUTPUT_PATH, index=False)
    product_df.to_csv(PRODUCT_OUTPUT_PATH, index=False)

    print(f"Saved {COUNTRY_OUTPUT_PATH}")
    print(f"Saved {PRODUCT_OUTPUT_PATH}")
    print()

    print(f"country_translations shape: {country_df.shape}")
    print(f"product_translations shape: {product_df.shape}")
    print(f"Unique countries: {country_df['country_name_am'].nunique()}")
    print(f"Unique product codes: {product_df['product_code'].nunique()}")
    print(f"Rows with blank iso3: {(country_df['iso3'].astype(str).str.strip() == '').sum()}")
    print(f"Product codes matched to HS descriptions: {matched_product_codes}")
    print(f"Product codes missing HS descriptions (NEEDS REVIEW): {len(missing_product_codes)}")
    print()

    print("country_translations first 10 rows:")
    print(country_df.head(10).to_string(index=False))
    print()

    print("product_translations first 10 rows:")
    print(product_df.head(10).to_string(index=False))
    print()

    if country_uncertain:
        print("Warning: country translations needing manual review:")
        for name in country_uncertain[:30]:
            print(f" - {name}")
        if len(country_uncertain) > 30:
            print(f" ... and {len(country_uncertain) - 30} more")
        print()

    if missing_product_codes:
        print("Warning: missing HS description for product_code values:")
        for code in missing_product_codes[:100]:
            print(f" - {code}")
        if len(missing_product_codes) > 100:
            print(f" ... and {len(missing_product_codes) - 100} more")


if __name__ == "__main__":
    main()
