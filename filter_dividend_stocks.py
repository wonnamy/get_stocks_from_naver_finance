# -*- coding: utf-8 -*-

import pandas as pd
import os
import glob
import datetime

# --------------------------------------------------
# 경로 설정
# --------------------------------------------------
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SCRAPING_DIR = os.path.join(BASE_DIR, "scraping")
FILTERED_DIR = os.path.join(BASE_DIR, "filtered")

# 가장 최근 *_naver_stocks_all.csv 파일을 자동 탐지
candidates = sorted(glob.glob(os.path.join(SCRAPING_DIR, "*_naver_stocks_all.csv")))
if not candidates:
    raise FileNotFoundError("scraping/ 폴더에 *_naver_stocks_all.csv 파일이 없습니다.")
INPUT_CSV   = candidates[-1]
DATE_PREFIX = os.path.basename(INPUT_CSV).split("_")[0]   # e.g. "260419"
os.makedirs(FILTERED_DIR, exist_ok=True)
OUTPUT_CSV  = os.path.join(FILTERED_DIR, f"{DATE_PREFIX}_filtered_dividend_stocks.csv")
RANKING_CSV = os.path.join(FILTERED_DIR, f"{DATE_PREFIX}_ranking_dividend_stocks.csv")

# 기준: 작년 12월 (YY.MM 형식 실수, e.g. 25.12)
today = datetime.date.today()
last_dec_threshold = float(f"{str(today.year - 1)[-2:]}.12")   # e.g. 25.12


def clean_numeric(series: pd.Series) -> pd.Series:
    """쉼표 제거 후 float 변환. 변환 불가한 값은 NaN 반환."""
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


# ==================================================
# Phase 1. 데이터 로딩 & 전처리
# ==================================================
print("=" * 60)
print("Phase 1. 데이터 로딩 & 전처리")
print("=" * 60)

df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
df.columns = df.columns.str.strip()   # ' 유보율' → '유보율'
print(f"▶ 로딩 완료: {df.shape[0]}개 종목  ({INPUT_CSV})")

# 숫자형 변환
numeric_cols = [
    "시가총액", "매출액", "영업이익", "현재가",
    "배당금", "ROE", "유보율", "기준월",
    "1년전", "2년전", "3년전",
    "영업이익증가율", "매출액증가율",
]
for col in numeric_cols:
    df[col] = clean_numeric(df[col])

# 결측치 → 0
df = df.fillna(0)
print(f"▶ 결측치 0 처리 완료")


# ==================================================
# Phase 2. 기초 필터
# ==================================================
print("\n" + "=" * 60)
print("Phase 2. 기초 필터")
print("=" * 60)

# 매출액 <= 0 또는 영업이익 <= 0 제거
before = df.shape[0]
df = df[(df["매출액"] > 0) & (df["영업이익"] > 0)].copy()
print(f"▶ 매출액/영업이익 <= 0 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# 1년전·2년전·3년전 배당이 모두 있는 종목만 유지
before = df.shape[0]
df = df[(df["1년전"] > 0) & (df["2년전"] > 0) & (df["3년전"] > 0)].copy()
print(f"▶ 과거 3년 배당 없는 종목 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# 배당 안정성: 1년전이 2년전 대비 20% 이상 감소한 종목 제거
before = df.shape[0]
df = df[df["1년전"] >= df["2년전"] * 0.8].copy()
print(f"▶ 배당 안정성 (1년전 < 2년전×0.8) 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# 기준월이 작년 12월 이전인 종목 제거
before = df.shape[0]
df = df[df["기준월"] >= last_dec_threshold].copy()
print(f"▶ 기준월 < {last_dec_threshold} 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")


# ==================================================
# Phase 3. 시가배당율 계산 & 랭킹 저장
# ==================================================
print("\n" + "=" * 60)
print("Phase 3. 시가배당율 계산 & 랭킹 저장")
print("=" * 60)

# 시가배당율(%) = 배당금 / 현재가 * 100  (현재가=0 방어, 소수점 그대로 유지)
df["시가배당율"] = (
    df["배당금"] / df["현재가"].replace(0, float("nan")) * 100
).fillna(0)

df = df.sort_values("시가배당율", ascending=False).reset_index(drop=True)

df.to_csv(RANKING_CSV, index=False, encoding="utf-8-sig")
print(f"▶ 랭킹 전체 저장 완료: {RANKING_CSV} ({df.shape[0]}개)")
print(f"▶ 시가배당율 범위: min={df['시가배당율'].min():.2f}%, max={df['시가배당율'].max():.2f}%")


# ==================================================
# Phase 4. 상위 200개 선정
# ==================================================
print("\n" + "=" * 60)
print("Phase 4. 상위 200개 선정")
print("=" * 60)

df = df.head(200).copy()
print(f"▶ 상위 200개 선정 완료")


# ==================================================
# Phase 5. 품질 필터
# ==================================================
print("\n" + "=" * 60)
print("Phase 5. 품질 필터")
print("=" * 60)

# 시가총액 <= 1000억 제거
before = df.shape[0]
df = df[df["시가총액"] > 1000].copy()
print(f"▶ 시가총액 <= 1000억 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# ROE <= 5 제거 (리츠는 ROE=0으로 처리되어 자동 제거)
before = df.shape[0]
df = df[df["ROE"] > 5].copy()
print(f"▶ ROE <= 5 제거 (리츠 포함): {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# 유보율 <= 100% 제거
before = df.shape[0]
df = df[df["유보율"] > 100].copy()
print(f"▶ 유보율 <= 100% 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# 시가배당율 <= 3% 제거
before = df.shape[0]
df = df[df["시가배당율"] > 3].copy()
print(f"▶ 시가배당율 <= 3% 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

# 영업이익증가율·매출액증가율 결측치 → 0 (필터에서 자동 제거)
df["영업이익증가율"] = df["영업이익증가율"].fillna(0)
df["매출액증가율"]  = df["매출액증가율"].fillna(0)

before = df.shape[0]
df = df[df["영업이익증가율"] >= -5].copy()
print(f"▶ 영업이익증가율 < -5% 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

before = df.shape[0]
df = df[df["매출액증가율"] >= -5].copy()
print(f"▶ 매출액증가율 < -5% 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")


# ==================================================
# 결과 저장
# ==================================================
print("\n" + "=" * 60)
print("결과 저장")
print("=" * 60)

df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
print(f"▶ 저장 완료: {OUTPUT_CSV}")
print(f"▶ 최종 종목 수: {df.shape[0]}개")

print("\n▶ 상위 10개 종목:")
display_cols = ["종목명", "시가배당율", "배당금", "현재가", "시가총액", "ROE", "유보율", "기준월", "1년전", "2년전", "3년전"]
print(df[display_cols].head(10).to_string(index=False))
