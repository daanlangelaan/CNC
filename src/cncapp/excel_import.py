from __future__ import annotations
import pandas as pd
from typing import Dict, List, Tuple

# Verwachte basiskolommen (optioneel in v0.1, maar we geven waarschuwingen als ze ontbreken)
EXPECTED_COLUMNS = {
    "profile": ["profile", "profiel", "profile_id", "profiel_id", "id"],
    "length_mm": ["length_mm", "length", "l_mm", "l", "lengte", "lengte_mm"],
    "qty": ["qty", "aantal", "quantity", "q"],
}

def _normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Normaliseer kolomnamen naar een vaste set waar mogelijk.
    Returned: (df_met_hernoemde_kolommen, mapping_used, missing_expected_keys)
    """
    original_cols = [str(c).strip() for c in df.columns]
    lowered = [c.lower().strip() for c in original_cols]
    mapping: Dict[str, str] = {}  # source -> target
    used_targets: Dict[str, str] = {}  # target -> source

    for target, candidates in EXPECTED_COLUMNS.items():
        for idx, c in enumerate(lowered):
            if c in candidates:
                mapping[original_cols[idx]] = target
                used_targets[target] = original_cols[idx]
                break

    # Hernoem kolommen op basis van mapping
    df2 = df.rename(columns=mapping)

    # Welke expected targets missen we?
    missing = [t for t in EXPECTED_COLUMNS.keys() if t not in df2.columns]

    return df2, used_targets, missing

def read_cutlist(path: str, sheet_name: str | int | None = 0) -> Dict:
    """
    Lees een Excel-cutlist in (eerste sheet standaard). Geeft dict terug met:
      - df: pandas.DataFrame (met genormaliseerde kolommen waar mogelijk)
      - sheet_name: naam van het ingelezen blad
      - columns_original: originele kolommen
      - columns_final: uiteindelijke kolommen
      - normalized_mapping: mapping target->bron voor gevonden kolommen
      - missing_expected: lijst met ontbrekende expected kolommen (informatief in v0.1)
      - warnings: lijst met tekstuele waarschuwingen
    """
    xls = pd.ExcelFile(path)
    sheet_to_read = xls.sheet_names[sheet_name] if isinstance(sheet_name, int) else (sheet_name or xls.sheet_names[0])
    df = pd.read_excel(path, sheet_name=sheet_to_read)

    # Drop volledig lege rijen
    df = df.dropna(how="all").reset_index(drop=True)

    df_norm, used_targets, missing = _normalize_columns(df)

    warnings: List[str] = []
    if missing:
        warnings.append(
            "Let op: niet alle verwachte kolommen gevonden: "
            + ", ".join(missing)
            + " (v0.1 leest toch alles in; validatie is informatief)."
        )

    result = {
        "df": df_norm,
        "sheet_name": sheet_to_read,
        "columns_original": list(df.columns),
        "columns_final": list(df_norm.columns),
        "normalized_mapping": used_targets,  # target -> source
        "missing_expected": missing,
        "warnings": warnings,
    }
    return result
