import pandas as pd
from cncapp.excel_import import _normalize_columns

def test_normalize_columns_basic():
    df = pd.DataFrame({
        "Profiel": ["A", "B"],
        "Lengte_mm": [1000, 2000],
        "Aantal": [5, 2],
        "VrijeKolom": ["x", "y"]
    })
    df2, used_targets, missing = _normalize_columns(df)
    # Targets die we verwachten: profile, length_mm, qty
    assert "profile" in df2.columns
    assert "length_mm" in df2.columns
    assert "qty" in df2.columns
    assert isinstance(used_targets, dict)
    assert isinstance(missing, list)
