# -*- coding: utf-8 -*-

import pandas as pd
import os
import glob

# --------------------------------------------------
# 경로 설정
# --------------------------------------------------
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SCRAPING_DIR = os.path.join(BASE_DIR, "scraping")
FILTERED_DIR = os.path.join(BASE_DIR, "filtered")

# 가장 최근 *_naver_stocks_total.csv 파일을 자동 탐지
candidates = sorted(glob.glob(os.path.join(SCRAPING_DIR, "*_naver_stocks_total.csv")))
if not candidates:
    raise FileNotFoundError(f"scraping/ 폴더에 *_naver_stocks_total.csv 파일이 없습니다.")
INPUT_CSV   = candidates[-1]
DATE_PREFIX = os.path.basename(INPUT_CSV).split("_")[0]          # e.g. "260419"
os.makedirs(FILTERED_DIR, exist_ok=True)
OUTPUT_CSV  = os.path.join(FILTERED_DIR, f"{DATE_PREFIX}_filtered_value_stocks.csv")
RANKING_CSV = os.path.join(FILTERED_DIR, f"{DATE_PREFIX}_ranking_value_stocks.csv")


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
print(f"▶ 로딩 완료: {df.shape[0]}개 종목")

# 숫자형 변환
numeric_cols = ["시가총액", "영업이익", "매출액", "현재가", "주당순이익", "PER", "PBR", "ROE", "유보율", "영업이익증가율", "매출액증가율"]
for col in numeric_cols:
    df[col] = clean_numeric(df[col])

# 영업이익·시가총액·매출액 결측치 → 0
df[["영업이익", "시가총액", "매출액"]] = df[["영업이익", "시가총액", "매출액"]].fillna(0)

# 영업이익 <= 0 종목 제거
before = df.shape[0]
df = df[df["영업이익"] > 0].copy()
print(f"▶ 영업이익 <= 0 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")


# ==================================================
# Phase 2. 지표 계산 (POR, PSR)
# ==================================================
print("\n" + "=" * 60)
print("Phase 2. 지표 계산 (POR, PSR)")
print("=" * 60)

# PER_NEW = 현재가 / 주당순이익  (낮을수록 저평가, 0·음수·결측 → 999)
df["PER_NEW"] = (df["현재가"] / df["주당순이익"].replace(0, float("nan"))).replace(
    [float("inf"), float("-inf")], float("nan")
)
df["PER_NEW"] = df["PER_NEW"].apply(lambda x: x if (pd.notna(x) and x > 0) else float("nan")).fillna(999)

# POR = 시가총액 / 영업이익  (낮을수록 저평가)
df["POR"] = df["시가총액"] / df["영업이익"]

# PSR = 시가총액 / 매출액    (낮을수록 저평가, 매출액=0이면 inf → 999 처리)
df["PSR"] = (df["시가총액"] / df["매출액"].replace(0, float("nan"))).replace(
    float("inf"), float("nan")
)

# PBR·PSR 결측치 → 999  (랭킹 최하위 처리)
df["PBR"] = df["PBR"].fillna(999)
df["PSR"] = df["PSR"].fillna(999)

print(f"▶ PER_NEW 범위: min={df[df['PER_NEW']<999]['PER_NEW'].min():.2f}, max={df[df['PER_NEW']<999]['PER_NEW'].max():.2f}")
print(f"▶ POR 범위: min={df['POR'].min():.2f}, max={df['POR'].max():.2f}")
print(f"▶ PSR 범위: min={df['PSR'].min():.2f}, max={df['PSR'].max():.2f}")


# ==================================================
# Phase 3. 랭킹 & 상위 200개 선정
# ==================================================
print("\n" + "=" * 60)
print("Phase 3. 랭킹 & 상위 200개 선정")
print("=" * 60)

for metric in ["PER_NEW", "PBR", "POR", "PSR"]:
    df[f"Rank_{metric}"] = df[metric].rank(method="min", ascending=True)

df["Rank_SUM"] = (df["Rank_PER_NEW"] + df["Rank_PBR"] + df["Rank_POR"] + df["Rank_PSR"]) / 4
df = df.sort_values("Rank_SUM", ascending=True).reset_index(drop=True)

# 검증용: 영업이익 > 0 필터 후 전체 랭킹 저장
df.to_csv(RANKING_CSV, index=False, encoding="utf-8-sig")
print(f"▶ 랭킹 전체 저장 완료: {RANKING_CSV} ({df.shape[0]}개)")

df = df.head(200).copy()
print(f"▶ 상위 200개 선정 완료")


# ==================================================
# Phase 4. 품질 필터
# ==================================================
print("\n" + "=" * 60)
print("Phase 4. 품질 필터")
print("=" * 60)

# ROE·유보율 결측치 → 0 (필터에서 자동 제거)
df["ROE"]  = df["ROE"].fillna(0)
df["유보율"] = df["유보율"].fillna(0)

before = df.shape[0]
df = df[df["시가총액"] > 1000].copy()
print(f"▶ 시가총액 <= 1000억 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

before = df.shape[0]
df = df[df["ROE"] > 5].copy()
print(f"▶ ROE <= 5 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

before = df.shape[0]
df = df[df["유보율"] > 100].copy()
print(f"▶ 유보율 <= 100% 제거: {before - df.shape[0]}개 제거 → {df.shape[0]}개 잔여")

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
display_cols = ["종목명", "PER_NEW", "PBR", "POR", "PSR", "Rank_SUM", "시가총액", "ROE", "유보율"]
print(df[display_cols].head(10).to_string(index=False))
