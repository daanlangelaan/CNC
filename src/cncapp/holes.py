from __future__ import annotations
import re
import json
import pandas as pd
from typing import Dict, List, Tuple

HOLE_RE = re.compile(r"\s*(\d+(?:\.\d+)?)\s*@\s*(\d+(?:\.\d+)?)\s*")

HEADER_COLS_CANON = {
    "name": ["profile", "profiel_naam"],
    "type": ["profiel_type", "type"],
    "orient": ["orientatie", "orientation"],
    "lenmm": ["length_mm", "lengte_mm"],
    "qty": ["qty", "aantal"],
    "side": ["zijde"]
}

def _find_col(df: pd.DataFrame, candidates: List[str]) -> str | None:
    low = {str(c).lower(): c for c in df.columns}
    for c in candidates:
        if c in low:
            return low[c]
    return None

def _std_side_label(s: str) -> str:
    """Zet 'BOVENKANT Y10' -> 'TOP_Y10', 'ZIJKANT Y30' -> 'SIDE_Y30'."""
    s = (s or "").strip().upper()
    if not s:
        return ""
    part = "TOP" if s.startswith("BOVENKANT") else ("SIDE" if s.startswith("ZIJKANT") else s.replace(" ", "_"))
    # plak eventuele Y.. of rest erachter
    tail = s.replace("BOVENKANT", "").replace("ZIJKANT", "").strip().replace(" ", "")
    return f"{part}_{tail}" if tail else part

def _parse_holes_row(vals: List) -> List[Tuple[float, float]]:
    holes: List[Tuple[float, float]] = []
    for v in vals:
        if pd.isna(v):
            continue
        m = HOLE_RE.match(str(v))
        if m:
            x = float(m.group(1))
            d = float(m.group(2))
            holes.append((x, d))
    return holes

def extract_holes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Leest de ruwe Excelstructuur (met kolom 'zijde' en de gatenkolommen rechts daarvan)
    en levert 1 rij per profiel met verzamelde gaten per zijde.

    Outputkolommen:
      - profile_name, profiel_type, orientatie, length_mm, qty
      - holes_json (JSON met {SIDE_LABEL: [{"x":..,"d":..}, ...]})
      - holes_flat (compacte string per zijde, bv. 'TOP_Y10: 390@4.3,711@4.3 | SIDE_Y10: ...')
    """
    name_col = _find_col(df, HEADER_COLS_CANON["name"])
    type_col = _find_col(df, HEADER_COLS_CANON["type"])
    orient_col = _find_col(df, HEADER_COLS_CANON["orient"])
    len_col = _find_col(df, HEADER_COLS_CANON["lenmm"])
    qty_col = _find_col(df, HEADER_COLS_CANON["qty"])
    side_col = _find_col(df, HEADER_COLS_CANON["side"])

    if not name_col or not len_col:
        raise ValueError("Benodigde kolommen ontbreken (profiel_naam/profile of length_mm/lengte_mm).")

    # alle kolommen rechts van 'zijde' bevatten mogelijke gaten
    possible_hole_cols: List[str] = []
    if side_col:
        side_idx = list(df.columns).index(side_col)
        possible_hole_cols = list(df.columns)[side_idx+1:]
    else:
        # fallback: alle kolommen die niet de headerkolommen zijn
        header_like = {c for c in [name_col, type_col, orient_col, len_col, qty_col] if c}
        possible_hole_cols = [c for c in df.columns if c not in header_like]

    # forward-fill van headerwaarden zodat subrijen dezelfde profielcontext krijgen
    work = df.copy()
    for c in [name_col, type_col, orient_col, len_col, qty_col]:
        if c:
            work[c] = work[c].ffill()

    # qty normaliseren
    if qty_col:
        work[qty_col] = pd.to_numeric(work[qty_col], errors="coerce").fillna(1).astype(int)

    records = []
    # we aggregeren per profielnaam + lengte (unieke header)
    # subgroup = alle rijen tot het volgende profielheaderblok
    # We nemen gewoon alle rijen met dezelfde ffilled name & len.
    group_cols = [name_col, len_col]
    if type_col: group_cols.append(type_col)
    if orient_col: group_cols.append(orient_col)
    if qty_col: group_cols.append(qty_col)

    grouped = work.groupby(group_cols, dropna=False, sort=False)

    for keys, g in grouped:
        # headershow: alleen opnemen als er holes zijn
        holes_by_side: Dict[str, List[Tuple[float, float]]] = {}

        for _, row in g.iterrows():
            side_val = str(row.get(side_col, "")).strip() if side_col else ""
            if side_val == "" or side_val.lower().startswith("nan"):
                # kan een pure header-rij zijn; die draagt geen gaten
                continue
            side_label = _std_side_label(side_val)
            vals = [row.get(c, None) for c in possible_hole_cols]
            parsed = _parse_holes_row(vals)
            if parsed:
                holes_by_side.setdefault(side_label, []).extend(parsed)

        if not holes_by_side:
            # geen gaten -> overslaan (zoals jij wilt)
            continue

        # bouw outputrij
        key_map = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)))
        rec = {
            "profile_name": key_map.get(name_col),
            "profiel_type": key_map.get(type_col),
            "orientatie": key_map.get(orient_col),
            "length_mm": float(key_map.get(len_col)) if key_map.get(len_col) is not None else None,
            "qty": int(key_map.get(qty_col)) if key_map.get(qty_col) is not None else 1,
        }

        # json + compacte string
        holes_json = {side: [{"x": x, "d": d} for (x, d) in lst] for side, lst in holes_by_side.items()}
        rec["holes_json"] = json.dumps(holes_json, ensure_ascii=False)

        flat_parts = []
        for side, lst in holes_by_side.items():
            flat = ",".join([f"{x:g}@{d:g}" for (x, d) in lst])
            flat_parts.append(f"{side}: {flat}")
        rec["holes_flat"] = " | ".join(flat_parts)

        records.append(rec)

    out = pd.DataFrame.from_records(records)
    # sorteer optisch op profielnaam
    if "profile_name" in out.columns:
        out = out.sort_values(by=["profile_name"], kind="stable")
    return out.reset_index(drop=True)
