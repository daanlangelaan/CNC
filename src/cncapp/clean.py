from __future__ import annotations
import re
import pandas as pd

KEEP_COLS_CANDIDATES = [
    "profile", "profiel_naam",
    "profiel_type", "orientatie",
    "length_mm", "qty",
]

HOLE_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\s*@\s*\d+(?:\.\d+)?\b")

def _drop_unnamed_and_empty_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df.columns if not str(c).lower().startswith("unnamed")]
    df = df[cols]
    df = df.dropna(axis=1, how="all")
    return df

def _select_core_columns(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in KEEP_COLS_CANDIDATES if c in df.columns]
    return df[existing] if existing else df

def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    if "qty" in df.columns:
        df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(1).astype(int)
    if "length_mm" in df.columns:
        df["length_mm"] = pd.to_numeric(df["length_mm"], errors="coerce")
    return df

def _name_col(df: pd.DataFrame) -> str | None:
    if "profile" in df.columns: return "profile"
    if "profiel_naam" in df.columns: return "profiel_naam"
    return None

def _has_hole_string(val) -> bool:
    if pd.isna(val): 
        return False
    s = str(val)
    if "@" in s and HOLE_TOKEN_RE.search(s):
        return True
    return False

def _profiles_with_holes(df_raw: pd.DataFrame) -> pd.Series:
    """
    Bepaal per profiel (op basis van 'profile' of 'profiel_naam') of er ergens
    in de bijbehorende sub-rijen een gat voorkomt (waarde zoals '390.0@4.3').
    We forward-fillen de profielnaam zodat sub-rijen eronder eraan gekoppeld worden.
    """
    namecol = _name_col(df_raw)
    if not namecol:
        # Geen naamkolom; neem alles mee
        return pd.Series([True] * len(df_raw), index=df_raw.index)

    # Forward-fill de naam zodat sub-rijen eronder dezelfde 'groep' krijgen
    gdf = df_raw.copy()
    gdf[namecol] = gdf[namecol].ffill()

    # Kolommen die mogelijk gaten bevatten = alle kolommen behalve de kernvelden
    hole_candidate_cols = [c for c in gdf.columns if c not in KEEP_COLS_CANDIDATES]

    # Markeer per rij of er een gat staat
    row_has_hole = gdf[hole_candidate_cols].applymap(_has_hole_string).any(axis=1)

    # Per profiel: heeft één van de rijen in de groep een gat?
    has_holes_per_profile = row_has_hole.groupby(gdf[namecol]).any()

    # Map terug naar rijen: alleen de hoofdrij (waar length en naam staat) willen we straks tonen
    # We geven een booleaanse mask terug voor de hoofdrijen die een gat hebben.
    # Hoofdrij ≈ de rij waar naam NIET NaN is en length_mm niet NaN is.
    is_header_row = gdf[namecol].notna() & (gdf["length_mm"].notna() if "length_mm" in gdf.columns else True)
    header_with_holes = is_header_row & gdf[namecol].map(lambda n: has_holes_per_profile.get(n, False))
    return header_with_holes

def _filter_noise_rows_keep_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Houd alleen de 'hoofdrijen' (naam aanwezig + geldige lengte). Sub-rijen
    zoals BOVENKANT/ZIJKANT worden niet getoond in de uiteindelijke tabel.
    """
    name_col = _name_col(df)
    if name_col is None:
        return df
    if "length_mm" not in df.columns:
        return df[df[name_col].notna()].copy()
    return df[df[name_col].notna() & df["length_mm"].notna()].copy()

def clean_cutlist(df: pd.DataFrame, keep_only_with_holes: bool = False) -> tuple[pd.DataFrame, list[str]]:
    """
    Retourneert (geschoond_df, warnings)

    Stappen:
      1) Kolommen opschonen (Unnamed en lege kolommen weg)
      2) Types coerced (qty -> int, length_mm -> numeric)
      3) (optioneel) Alleen profielen met gaten behouden (detectie via '@' in sub-rijen)
      4) Alleen hoofdrijen tonen (geen BOVENKANT/ZIJKANT-rijen)
    """
    warnings: list[str] = []
    before_rows = len(df)
    before_cols = list(df.columns)

    # 1) kolommen
    df1 = _drop_unnamed_and_empty_cols(df.copy())

    # 2) types
    df1 = _coerce_types(df1)

    # 3) alleen profielen met gaten (op basis van _profiles_with_holes over de RUWE structuur)
    if keep_only_with_holes:
        mask_headers_with_holes = _profiles_with_holes(df1)
        # We tonen na stap 4 toch alleen headers; hier filteren we alvast op headers+holes:
        df1 = df1[mask_headers_with_holes].copy()

    # 4) alleen hoofdrijen houden voor output
    df1 = _filter_noise_rows_keep_headers(df1)
    df1 = _select_core_columns(df1).reset_index(drop=True)

    # waarschuwingen
    after_rows = len(df1)
    removed_cols = set(before_cols) - set(df1.columns)
    if removed_cols:
        warnings.append(f"Verwijderde kolommen: {sorted(removed_cols)}")
    if after_rows < before_rows:
        warnings.append(f"Gefilterd van {before_rows} naar {after_rows} rijen.")

    return df1, warnings
