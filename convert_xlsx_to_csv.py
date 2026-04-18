# -*- coding: utf-8 -*-
"""
Convert specific .xlsx files in the result/ folder to .csv with utf-8-sig encoding.
Usage: run in the repository root (same folder as this script).
"""
import os
import sys
import pandas as pd

FILES = [
    "result/naver_stocks_2026-04-18.xlsx",
    "result/naver_stocks_devidend_2026-04-18.xlsx",
    "result/naver_stocks_kosdaq_2026-04-18.xlsx",
    "result/naver_stocks_kospi_2026-04-18.xlsx",
    "result/naver_stocks_total_2026-04-18.xlsx",
]

MAPPING = {
    "result/naver_stocks_2026-04-18.xlsx": "result/260418_naver_stocks_all.csv",
    "result/naver_stocks_devidend_2026-04-18.xlsx": "result/260418_naver_stocks_dividend.csv",
    "result/naver_stocks_kosdaq_2026-04-18.xlsx": "result/260418_naver_stocks_kosdaq.csv",
    "result/naver_stocks_kospi_2026-04-18.xlsx": "result/260418_naver_stocks_kospi.csv",
    "result/naver_stocks_total_2026-04-18.xlsx": "result/260418_naver_stocks_total.csv",
}


def convert_file(xlsx_path, csv_path):
    if not os.path.exists(xlsx_path):
        print(f"SKIP (not found): {xlsx_path}")
        return False

    try:
        # read first sheet
        df = pd.read_excel(xlsx_path, sheet_name=0)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"Converted: {xlsx_path} -> {csv_path}")
        return True
    except Exception as e:
        print(f"ERROR converting {xlsx_path}: {e}")
        return False


if __name__ == "__main__":
    ok = True
    for f in FILES:
        out = MAPPING.get(f, f.replace('.xlsx', '.csv'))
        res = convert_file(f, out)
        ok = ok and res
    if not ok:
        print("One or more files failed or were missing.")
        sys.exit(2)
    print("All done.")
