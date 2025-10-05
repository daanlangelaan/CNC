from __future__ import annotations
import os, json
from typing import Dict, List
import pandas as pd

from cncapp.config import (
    MACHINE_UNITS, SPINDLE_RPM, EXTRA_DEPTH, Z_CLEAR_ADD, SOFT_MM,
    FEED_SOFT, FEED_DRILL, Y_CLEAR, Z_PARK, COMMENT_PREFIX, COMMENT_SUFFIX,
    resolve_side_height
)

def _c(s: str) -> str:
    return f"{COMMENT_PREFIX}{s}{COMMENT_SUFFIX}"

def _emit_header(g: List[str], profile_name: str, profile_type: str | None, length_mm: float):
    g.append(_c(f"{profile_name} - {profile_type or ''} L={length_mm:.1f} mm").replace("  ", " ").strip())
    g.append("G90 G94 G91.1 G40 G49 G17")
    g.append("G21" if MACHINE_UNITS.lower() == "mm" else "G20")
    g.append("G28 G91 Z0.")
    g.append("G90")
    g.append("G54")
    g.append(f"S{int(SPINDLE_RPM)} M3")

def _emit_end(g: List[str]):
    g.append("M9")
    g.append("M5")
    g.append("G28 G91 Z0.")
    g.append("G90")
    g.append("G28 G91 X0. Y0.")
    g.append("G90")
    g.append("M30")

def _parse_y(label: str) -> float:
    s = str(label).upper()
    if "Y" in s:
        tail = s.split("Y", 1)[1]
        num = ""
        for ch in tail:
            if ch.isdigit() or ch in ".,": num += "." if ch == "," else ch
            else: break
        try: return float(num) if num else 0.0
        except: return 0.0
    return 0.0

def _group_sides(holes: Dict[str, List[Dict]]) -> Dict[str, Dict[str, List[Dict]]]:
    groups: Dict[str, Dict[str, List[Dict]]] = {"TOP": {}, "SIDE": {}}
    for lbl, lst in holes.items():
        u = str(lbl).upper()
        if u.startswith("TOP"): groups["TOP"][lbl] = lst
        elif u.startswith("SIDE"): groups["SIDE"][lbl] = lst
        else:
            groups.setdefault("OTHER", {})[lbl] = lst
    return {k: v for k, v in groups.items() if v}

def _drill_sequence(g: List[str], x: float, side_height: float):
    """
    Z=0 onderkant. Oppervlak (start boren) = +side_height.
    Soft plunge: eerste SOFT_MM traag vanaf het oppervlak.
    Einddiepte: Zb = -EXTRA_DEPTH (onder de onderkant).
    """
    z_surface = side_height
    z_soft_end = z_surface - SOFT_MM
    z_final = -EXTRA_DEPTH
    # Naar X, soft plunge, dan normaal boren
    g.append(f"G0 X{x:.3f}")
    g.append(f"G1 Z{z_soft_end:.3f} F{FEED_SOFT:g}")
    g.append(f"G1 Z{z_final:.3f} F{FEED_DRILL:g}")

def _emit_top(g: List[str], side_map: Dict[str, List[Dict]], profile_type: str | None):
    # Bovenkant gebruikt de GROTE maat → side_height
    side_height = resolve_side_height(profile_type, None, "TOP")
    zc = side_height + Z_CLEAR_ADD
    g.append(_c(f"BEWERKING: BOVENKANT (hoogte={side_height:g} -> Zc={zc:g})"))
    g.append(_c("Klem profiel in"))
    g.append(f"G0 Z{zc:.3f}")
    for lbl, holes in side_map.items():
        y = _parse_y(lbl)
        g.append(f"G0 X0.000 Y{y:.3f}")
        for i, h in enumerate(sorted(holes, key=lambda hh: float(hh['x']))):
            x = float(h["x"]); d = float(h["d"])
            g.append(_c(f"HOLE {i+1} dia={d:g}"))
            _drill_sequence(g, x, side_height)
            g.append(f"G0 Z{zc:.3f}")
    g.append(f"G0 X0.000 Y{Y_CLEAR:.3f}")

def _emit_side(g: List[str], side_map: Dict[str, List[Dict]], profile_type: str | None):
    # Zijkant gebruikt de KLEINE maat → side_height
    side_height = resolve_side_height(profile_type, None, "SIDE")
    zc = side_height + Z_CLEAR_ADD
    g.append(_c(f"BEWERKING: ZIJKANT (hoogte={side_height:g} -> Zc={zc:g})"))
    g.append(_c("Draai profiel X om naar zijkant"))
    g.append("M5")
    g.append(f"G0 Z{Z_PARK:.3f}")
    g.append("M0 (<<< DRAAI PROFIEL MANUEEL >>>)")
    g.append(f"S{int(SPINDLE_RPM)} M3")
    g.append(f"G0 Z{zc:.3f}")
    for lbl in sorted(side_map.keys(), key=_parse_y):
        y = _parse_y(lbl)
        holes = side_map[lbl]
        g.append(_c(f"ZIJKANT RIJ: {lbl}"))
        g.append(f"G0 X0.000 Y{y:.3f}")
        for i, h in enumerate(sorted(holes, key=lambda hh: float(hh['x']))):
            x = float(h["x"]); d = float(h["d"])
            g.append(_c(f"HOLE {i+1} dia={d:g}"))
            _drill_sequence(g, x, side_height)
            g.append(f"G0 Z{zc:.3f}")
    g.append(f"G0 X0.000 Y{Y_CLEAR:.3f}")

def generate_gcode_for_profile(row: Dict, output_dir: str) -> str:
    name = str(row.get("profile_name") or "Profiel")
    ptype = (row.get("profiel_type") or "") and str(row.get("profiel_type"))
    length = float(row.get("length_mm") or 0)
    holes = json.loads(row["holes_json"]) if isinstance(row.get("holes_json"), str) else (row.get("holes_json") or {})

    g: List[str] = []
    _emit_header(g, name, ptype, length)

    groups = _group_sides(holes)
    if "TOP" in groups: _emit_top(g, groups["TOP"], ptype)
    if "SIDE" in groups: _emit_side(g, groups["SIDE"], ptype)
    if "OTHER" in groups: _emit_side(g, groups["OTHER"], ptype)

    _emit_end(g)

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{name.replace(' ', '_')}.tap")
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        f.write("\n".join(g) + "\n")
    return path

def generate_all_profiles(df: pd.DataFrame, output_dir: str, one_file: bool = False) -> str | None:
    if one_file:
        g_all: List[str] = []
        for _, r in df.iterrows():
            tmp = dict(r)
            name = str(tmp.get("profile_name") or "Profiel")
            ptype = (tmp.get("profiel_type") or "") and str(tmp.get("profiel_type"))
            length = float(tmp.get("length_mm") or 0)
            holes = json.loads(tmp["holes_json"]) if isinstance(tmp.get("holes_json"), str) else (tmp.get("holes_json") or {})
            _emit_header(g_all, name, ptype, length)
            groups = _group_sides(holes)
            if "TOP" in groups: _emit_top(g_all, groups["TOP"], ptype)
            if "SIDE" in groups: _emit_side(g_all, groups["SIDE"], ptype)
            if "OTHER" in groups: _emit_side(g_all, groups["OTHER"], ptype)
            _emit_end(g_all)
            g_all.append("")
        os.makedirs(output_dir, exist_ok=True)
        p = os.path.join(output_dir, "all_profiles.tap")
        with open(p, "w", encoding="ascii", errors="ignore") as f:
            f.write("\n".join(g_all) + "\n")
        return p
    else:
        last = None
        for _, r in df.iterrows():
            last = generate_gcode_for_profile(dict(r), output_dir)
        return last
