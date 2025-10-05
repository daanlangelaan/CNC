import argparse
from tabulate import tabulate
from cncapp.excel_import import read_cutlist
from cncapp.holes import extract_holes
from cncapp.structure import flatten_to_long
from cncapp.gcode_gen import generate_all_profiles

def main():
    parser = argparse.ArgumentParser(description="cnc-profiles v1.0 – Excel->G-code (Mach3 .tap)")
    parser.add_argument("-f", "--file", default="sample_cutlist.xlsx", help="Pad naar Excelbestand")
    parser.add_argument("-s", "--sheet", default=0, help="Sheet naam of index (default: 0)")
    parser.add_argument("--preview", action="store_true", help="Toon console-preview i.p.v. meteen G-code")
    parser.add_argument("--export-dir", default="./out", help="Map voor .tap output")
    parser.add_argument("--one-file", action="store_true", help="Alle profielen in één .tap samenvoegen")
    parser.add_argument("--max-rows", type=int, default=15, help="Maximaal aantal rijen in preview")
    args = parser.parse_args()

    sheet_arg = args.sheet
    try:
        sheet_arg = int(sheet_arg)
    except ValueError:
        pass

    data = read_cutlist(args.file, sheet_name=sheet_arg)
    df_raw = data["df"]

    # 1) holes per profiel
    dfh = extract_holes(df_raw)
    if dfh.empty:
        print("Geen profielen met gaten gevonden.")
        return

    # 2) long-form voor interne logica / debug
    dfl = flatten_to_long(dfh)

    if args.preview:
        print("=" * 100)
        print(f"Bestand : {args.file}")
        print(f"Sheet   : {data['sheet_name']}")
        print(f"Aantal profielen met gaten : {len(dfh)}")
        print("-" * 100)
        from tabulate import tabulate
        print(tabulate(dfh.head(args.max_rows), headers="keys", tablefmt="github", showindex=False))
        if len(dfh) > args.max_rows:
            print(f"... ({len(dfh) - args.max_rows} profielen niet getoond)")
        print("=" * 100)
        return

    # 3) schrijf .tap (per profiel of gebundeld)
    path = generate_all_profiles(dfh, output_dir=args.export_dir, one_file=args.one_file)
    if path:
        print(f"[OK] G-code geschreven naar: {path}")
    else:
        print("[OK] G-code bestanden per profiel aangemaakt in:", args.export_dir)

if __name__ == "__main__":
    main()
