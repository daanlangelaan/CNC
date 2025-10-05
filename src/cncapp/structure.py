from __future__ import annotations
import json
import pandas as pd
from typing import Dict, List

def expand_holes_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Breidt een dataframe met kolom 'holes_json' uit naar aparte kolommen per zijde.
    """
    out = df.copy()
    if "holes_json" not in out.columns:
        raise ValueError("Kolom 'holes_json' ontbreekt; voer eerst extract_holes() uit.")

    # parse JSON
    all_sides: List[str] = []
    parsed_json: List[Dict] = []
    for j in out["holes_json"]:
        try:
            data = json.loads(j)
            parsed_json.append(data)
            all_sides.extend(data.keys())
        except Exception:
            parsed_json.append({})
    unique_sides = sorted(set(all_sides))

    # Voeg per zijde een kolom toe
    for side in unique_sides:
        out[f"holes_{side.lower()}"] = [
            ",".join([f"{h['x']}@{h['d']}" for h in parsed_json[i].get(side, [])])
            for i in range(len(out))
        ]
    return out


def flatten_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Zet dataframe om naar long-form: één rij per gat.
    Verwacht kolom 'holes_json'.
    """
    rows = []
    for _, row in df.iterrows():
        try:
            holes = json.loads(row["holes_json"])
        except Exception:
            holes = {}
        for side, lst in holes.items():
            for h in lst:
                rows.append({
                    "profile_name": row.get("profile_name"),
                    "profiel_type": row.get("profiel_type"),
                    "orientatie": row.get("orientatie"),
                    "length_mm": row.get("length_mm"),
                    "qty": row.get("qty"),
                    "side": side,
                    "x_mm": h["x"],
                    "d_mm": h["d"]
                })
    return pd.DataFrame(rows)
