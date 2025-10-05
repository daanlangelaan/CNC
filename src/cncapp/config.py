# Mach3-stijl G-code parameters en profielhoogte-logica

MACHINE_UNITS = "mm"   # G21
SPINDLE_RPM = 6000

# --- Profielhoogte per type ---
# 1) Directe mapping voor vaste types (override-waarde in mm)
PROFILE_HEIGHTS = {
    "20x20": 20.0,
    "20×20": 20.0,  # unicode x
    "20x40": 20.0,  # hoogte t.o.v. Z (meestal 20 mm bij 20x40-profiel)
    "20×40": 20.0,
    "40x40": 40.0,
    "40×40": 40.0,
}

# 2) Fallback-regel als type niet in mapping staat:
#    kies 'min' (kleinste dimensie van "AxB") of 'first' (eerste dimensie)
FALLBACK_RULE = "min"  # "min" of "first"

# 3) Extra (optioneel): per-profiel override op naam
PROFILE_HEIGHTS_BY_NAME = {
    # "Profiel 47": 20.0,
}

def resolve_profile_height(profiel_type: str | None, profile_name: str | None = None) -> float:
    """
    Bepaal PROFILE_HEIGHT (mm) o.b.v. profiel_type en/of profielnaam.
    Voorrang:
      1) PROFILE_HEIGHTS_BY_NAME[profile_name]
      2) PROFILE_HEIGHTS[profiel_type]
      3) FALLBACK_RULE op 'AxB' → min(A, B) of first(A, B)
      4) default 20.0 mm
    """
    # 1) per-naam override
    if profile_name:
        h = PROFILE_HEIGHTS_BY_NAME.get(str(profile_name).strip())
        if h:
            return float(h)

    # 2) directe mapping
    if profiel_type:
        key = str(profiel_type).strip().lower().replace("×", "x")
        if key in PROFILE_HEIGHTS:
            return float(PROFILE_HEIGHTS[key])

        # 3) fallback parse "AxB"
        if "x" in key:
            parts = key.split("x", 1)
            try:
                a = float(parts[0])
                b = float(parts[1])
                if FALLBACK_RULE == "first":
                    return a
                else:
                    return min(a, b)
            except Exception:
                pass

    # 4) default
    return 20.0


# --- Z-as referentie: Spoilboard is Z=0 ---
EXTRA_DEPTH = 1.0         # mm extra doorboren
Z_CLEAR_OFFSET = 15.0     # mm boven profiel als veilige Z (Zc = PROFILE_HEIGHT + Z_CLEAR_OFFSET)
Z_EXTRA_SOFT = 3.0        # soft plunge zone: laatste 3 mm langzamer

# Feeds
FEED_SOFT = 50.0          # mm/min (slow start/soft plunge)
FEED_DRILL = 150.0        # mm/min (normaal boren)

# Veilig wisselen
Y_CLEAR = 300.0           # vrije Y na zijde/profiel klaar
Z_PARK = 50.0             # extra park Z voor M0/rotatie

# Opmaak
COMMENT_PREFIX = "("      # Mach3-style comments "( ... )"
COMMENT_SUFFIX = ")"
# G-code parameters met Z=0 op ONDERKANT profiel en side-afhankelijke hoogtes

MACHINE_UNITS = "mm"   # G21
SPINDLE_RPM = 6000

# --- Profiel-type parsing / hoogtebepaling ---
PROFILE_HEIGHTS = {
    "20x20": (20.0, 20.0),   # (A,B) mm
    "20×20": (20.0, 20.0),
    "20x40": (20.0, 40.0),
    "20×40": (20.0, 40.0),
    "40x40": (40.0, 40.0),
    "40×40": (40.0, 40.0),
}
PROFILE_HEIGHTS_BY_NAME = {
    # "Profiel 47": (20.0, 40.0),
}

def _parse_type_dims(t: str) -> tuple[float, float] | None:
    t = t.strip().lower().replace("×", "x")
    if t in PROFILE_HEIGHTS:
        return PROFILE_HEIGHTS[t]
    if "x" in t:
        a, b = t.split("x", 1)
        try:
            return float(a), float(b)
        except Exception:
            return None
    return None

def resolve_side_height(profiel_type: str | None, profile_name: str | None, side_group: str) -> float:
    """
    side_group: 'TOP' of 'SIDE'
    - TOP  => gebruik de GROTE maat (profiel ligt plat, bovenkant op max)
    - SIDE => gebruik de KLEINE maat (profiel staat op zijkant)
    Fallback: 20 mm.
    """
    # per-naam override?
    if profile_name and profile_name in PROFILE_HEIGHTS_BY_NAME:
        dims = PROFILE_HEIGHTS_BY_NAME[profile_name]
    else:
        dims = _parse_type_dims(profiel_type or "") or (20.0, 20.0)

    small = min(dims)
    large = max(dims)
    return large if side_group.upper() == "TOP" else small

# --- Z-logica (Z=0 onderkant) ---
EXTRA_DEPTH = 1.0         # mm doorboren onder de onderkant
Z_CLEAR_ADD = 15.0        # mm boven oppervlak als safe height: Zc = side_height + 15
SOFT_MM = 3.0             # eerste 3 mm traag (vanaf oppervlak omlaag)

# Feeds
FEED_SOFT = 50.0          # mm/min (soft plunge)
FEED_DRILL = 150.0        # mm/min (rest van de diepte)

# Veilig wisselen
Y_CLEAR = 300.0           # vrije Y na zijde/profiel klaar
Z_PARK = 50.0             # extra park Z voor M0/rotatie (boven oppervlak)

# Opmaak
COMMENT_PREFIX = "("
COMMENT_SUFFIX = ")"
