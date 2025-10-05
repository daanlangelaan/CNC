import argparse
from tabulate import tabulate
from cncapp.excel_import import read_cutlist
from cncapp.holes import extract_holes

def main():
    parser = argparse.ArgumentParser(
        description="cnc-profiles v0.3 – Excel-import + gatenextractie per zijde"
    )
    parser.add_argument("-f", "--file", default="sample_cutlist.xlsx", help="Pad naar Excelbestand")
    parser.add_argument("-s", "--sheet", default=0, help="Sheet naam of index (default: 0)")
    parser.add_argument("--max-rows", type=int, default=25, help="Maximaal aantal te tonen rijen (default: 25)")
    parser.add_argument("--export", default="", help="Exporteer genormaliseerde data (met gaten) naar CSV-pad")
    parser.add_argument("--show", choices=["flat", "json", "none"], default="flat",
                        help="Weergave van gaten: 'flat' (compact), 'json' (volledig), of 'none'")
    args = parser.parse_args()

    # sheet -> int of str
    sheet_arg = args.sheet
    try:
        sheet_arg = int(sheet_arg)
    except ValueError:
        pass

    try:
        data = read_cutlist(args.file, sheet_name=sheet_arg)
    except FileNotFoundError:
        print(f"[FOUT] Bestand niet gevonden: {args.file}")
        return
    except Exception as e:
        print(f"[FOUT] Kon Excel niet lezen: {e}")
        return

    df_raw = data["df"]  # bevat nog de 'zijde' + gatenkolommen
    print("=" * 100)
    print(f"Bestand : {args.file}")
    print(f"Sheet   : {data['sheet_name']}")
    if data["warnings"]:
        for w in data["warnings"]:
            print(f"[WAARSCHUWING] {w}")

    # Extract gaten per profiel
    try:
        dfh = extract_holes(df_raw)
    except Exception as e:
        print(f"[FOUT] Gatenextractie mislukte: {e}")
        return

    if dfh.empty:
        print("Geen profielen met gaten gevonden.")
        print("=" * 100)
        return

    # Kies kolommen voor tabelweergave
    base_cols = ["profile_name", "profiel_type", "orientatie", "length_mm", "qty"]
    show_cols = base_cols[:]
    if args.show == "flat":
        show_cols.append("holes_flat")
    elif args.show == "json":
        show_cols.append("holes_json")

    print("-" * 100)
    preview = dfh[show_cols].head(args.max_rows)
    print(tabulate(preview, headers="keys", tablefmt="github", showindex=False))
    if len(dfh) > len(preview):
        print(f"... ({len(dfh) - len(preview)} rijen niet getoond; gebruik --max-rows)")

    if args.export:
        try:
            dfh.to_csv(args.export, index=False)
            print(f"[EXPORT] Genormaliseerde data (met gaten) → {args.export}")
        except Exception as e:
            print(f"[FOUT] Export mislukt: {e}")

    print("=" * 100)
    print("Klaar. (v0.3 – holes)")
    
if __name__ == "__main__":
    main()
