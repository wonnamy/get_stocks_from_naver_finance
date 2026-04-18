# get_stocks_from_naver_finance

네이버 금융에서 KOSPI/KOSDAQ 전 종목의 재무 데이터를 수집하고, 가치주 및 배당주 종목군을 자동으로 선별하는 도구입니다.

---

## 프로젝트 구조

```
get_stocks_from_naver_finance/
├── gathering_stock_from_naver_finance.py  # 네이버 금융 스크래핑
├── filter_value_stocks.py                 # 저평가(가치주) 종목 필터링
├── filter_dividend_stocks.py              # 배당주 종목 필터링
├── convert_xlsx_to_csv.py                 # xlsx → csv 변환 유틸리티
├── scraping/                              # 스크래핑 원본 CSV 저장
└── filtered/                              # 필터링 결과 CSV 저장
```

---

## 스크립트 설명

### 1. `gathering_stock_from_naver_finance.py` — 데이터 수집

네이버 금융 종목 분석 페이지에서 KOSPI/KOSDAQ 전 종목의 재무 데이터를 Selenium으로 수집합니다.

**출력 파일 (`scraping/` 폴더):**
| 파일명 | 내용 |
|--------|------|
| `YYMMDD_naver_stocks_kospi.csv` | KOSPI 종목 재무 데이터 |
| `YYMMDD_naver_stocks_kosdaq.csv` | KOSDAQ 종목 재무 데이터 |
| `YYMMDD_naver_stocks_total.csv` | KOSPI + KOSDAQ 통합 |
| `YYMMDD_naver_stocks_dividend.csv` | 배당 관련 데이터 |
| `YYMMDD_naver_stocks_all.csv` | total + dividend 병합 |

**실행:**
```bash
python gathering_stock_from_naver_finance.py
```

---

### 2. `filter_value_stocks.py` — 저평가 종목 필터링

4가지 밸류에이션 지표(PER·PBR·POR·PSR) 랭킹 평균으로 저평가 종목을 선별합니다.

**필터링 단계:**
1. 영업이익 > 0 종목만 유지
2. PER_NEW(현재가/주당순이익), POR(시가총액/영업이익), PSR(시가총액/매출액) 계산
3. PER_NEW·PBR·POR·PSR 각각 오름차순 랭킹 후 평균(`Rank_SUM`)으로 정렬
4. 상위 200개 선정
5. 품질 필터 적용: 시가총액 > 1000억 / ROE > 5% / 유보율 > 100% / 영업이익증가율 ≥ -5% / 매출액증가율 ≥ -5%

**출력 파일 (`filtered/` 폴더):**
| 파일명 | 내용 |
|--------|------|
| `YYMMDD_ranking_value_stocks.csv` | 영업이익 > 0 필터 후 전체 랭킹 (검증용) |
| `YYMMDD_filtered_value_stocks.csv` | 최종 저평가 종목군 |

**실행:**
```bash
python filter_value_stocks.py
```

---

### 3. `filter_dividend_stocks.py` — 배당 종목 필터링

시가배당율(배당금/현재가) 기준으로 안정적인 배당 종목을 선별합니다.

**필터링 단계:**
1. 매출액·영업이익 > 0 종목만 유지
2. 과거 3년 연속 배당 실시 종목만 유지
3. 배당 안정성: 최근 배당이 전년 대비 20% 이상 감소한 종목 제거
4. 기준월이 전년도 12월 이후인 종목만 유지 (최신 배당 데이터 보장)
5. 시가배당율 내림차순 정렬 후 상위 200개 선정
6. 품질 필터 적용: 시가총액 > 1000억 / ROE > 5%(리츠 자동 제외) / 유보율 > 100% / 시가배당율 > 3% / 영업이익증가율 ≥ -5% / 매출액증가율 ≥ -5%

**출력 파일 (`filtered/` 폴더):**
| 파일명 | 내용 |
|--------|------|
| `YYMMDD_ranking_dividend_stocks.csv` | 품질 필터 전 전체 랭킹 (검증용) |
| `YYMMDD_filtered_dividend_stocks.csv` | 최종 배당 종목군 |

**실행:**
```bash
python filter_dividend_stocks.py
```

---

## 실행 순서

```bash
# 1. 데이터 수집 (Chrome 브라우저 필요, 소요 시간: 수십 분)
python gathering_stock_from_naver_finance.py

# 2. 저평가 종목 필터링
python filter_value_stocks.py

# 3. 배당 종목 필터링
python filter_dividend_stocks.py
```

---

## 주요 컬럼 설명

| 컬럼 | 설명 |
|------|------|
| `PER_NEW` | 현재가 / 주당순이익 (직접 계산) |
| `PBR` | 주가순자산비율 (네이버 제공) |
| `POR` | 시가총액 / 영업이익 |
| `PSR` | 시가총액 / 매출액 |
| `Rank_SUM` | PER·PBR·POR·PSR 랭킹 평균 (낮을수록 저평가) |
| `시가배당율` | 배당금 / 현재가 × 100 (%) |
| `유보율` | 잉여금 / 납입자본금 × 100 (%) |

---

## 요구사항

```bash
pip install selenium pandas beautifulsoup4 requests
```

- Python 3.9 이상
- Chrome 브라우저 및 ChromeDriver (버전 일치 필요)
