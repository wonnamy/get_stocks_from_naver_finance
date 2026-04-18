# -*- coding: utf-8 -*-

# Selenium, Pandas, BeautifulSoup 불러오기
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pandas as pd
from bs4 import BeautifulSoup
import requests
import urllib.request
import os
import re
import time
import datetime


# -------------------------------
# 브라우저 초기화
# -------------------------------
def init_driver():
    chrome_options = Options()
    # 필요 시 주석 해제해서 헤드리스로 사용
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(3)
    return driver


# -------------------------------
# 공용 유틸 (안전 클릭 / 표 대기)
# -------------------------------
def wait_for_table(driver, timeout=10):
    """시세 표(table.type_2)가 뜰 때까지 대기"""
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.type_2")))


def safe_click(driver, by, value, timeout=10, retries=3, backoff=0.3):
    """
    DOM 재랜더링이 잦은 페이지에서 안전하게 클릭하는 헬퍼.
    - element_to_be_clickable로 fresh 핸들을 매번 가져옴
    - stale/intercepted/timeout 발생 시 짧은 백오프 뒤 재시도
    """
    last_err = None
    for _ in range(retries):
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            el.click()
            return True
        except (StaleElementReferenceException, ElementClickInterceptedException, TimeoutException) as e:
            last_err = e
            time.sleep(backoff)
    raise last_err


def click_apply_and_wait(driver):
    """
    '적용하기(fieldSubmit)' 클릭 후,
    - 이전 표 staleness 대기
    - 새 표 표시 대기
    """
    wait = WebDriverWait(driver, 10)

    try:
        old_table = driver.find_element(By.CSS_SELECTOR, "table.type_2")
    except Exception:
        old_table = None

    safe_click(driver, By.XPATH, "//a[@href='javascript:fieldSubmit()']/img")

    if old_table is not None:
        try:
            wait.until(EC.staleness_of(old_table))
        except TimeoutException:
            # 내부만 업데이트 되는 경우도 있어 무시
            pass

    wait_for_table(driver, timeout=10)
    return driver


# -------------------------------
# 페이지 열기/옵션 설정
# -------------------------------
def open_sise(driver):
    driver.get("http://finance.naver.com/sise/sise_market_sum.nhn")
    wait_for_table(driver)
    return driver


def click_default(driver):
    """
    초기화 버튼 클릭 후, 기본 체크된 것들 해제
    사이트 기본값 변경에 대비하여 안전 클릭 사용
    """
    safe_click(driver, By.XPATH, "//a[@href='javascript:fieldDefault()']/img")
    time.sleep(0.2)  # 아주 짧은 안정화 대기

    # 기본 선택 해제 (페이지 기본값에 맞게 조절)
    for opt in ("option1", "option15", "option21", "option4", "option6", "option12"):
        try:
            safe_click(driver, By.ID, opt)
        except Exception:
            # 존재하지 않거나 이미 해제돼 있을 수 있음
            pass
    return driver


def click_first(driver):
    # 거래량, 거래대금, 전일거래량, 외국인비율, 상장주식수
    for opt in ("option1", "option3", "option9", "option15", "option21"):
        safe_click(driver, By.ID, opt)
    click_apply_and_wait(driver)
    return driver


def click_second(driver):
    # 시가총액, 자산총계, 부채총계, 매출액, 매출액증가율
    for opt in ("option4", "option10", "option16", "option22", "option25"):
        safe_click(driver, By.ID, opt)
    click_apply_and_wait(driver)
    return driver


def click_third(driver):
    # 영업이익, 영업이익증가율, 당기순이익, 주당순이익, 보통주배당금
    for opt in ("option5", "option11", "option17", "option23", "option26"):
        safe_click(driver, By.ID, opt)
    click_apply_and_wait(driver)
    return driver


def click_fourth(driver):
    # PER, ROE, ROA, PBR, 유보율
    for opt in ("option6", "option12", "option18", "option24", "option27"):
        safe_click(driver, By.ID, opt)
    click_apply_and_wait(driver)
    return driver


def select_options(num, driver):
    click_default(driver)
    if num == 1:
        click_first(driver)
    elif num == 2:
        click_second(driver)
    elif num == 3:
        click_third(driver)
    elif num == 4:
        click_fourth(driver)
    return driver


# -------------------------------
# 데이터 컬럼/파싱/후처리
# -------------------------------
def create_column():
    columns = [
        ["N", "종목명", "현재가", "전일비", "등락률", "액면가", "거래량", "거래대금", "전일거래량", "상장주식수", "외국인비율"],
        ["N", "종목명", "현재가", "전일비", "등락률", "액면가", "시가총액", "매출액", "자산총계", "부채총계", "매출액증가율"],
        ["N", "종목명", "현재가", "전일비", "등락률", "액면가", "영업이익", "당기순이익", "주당순이익", "보통주배당금", "영업이익증가율"],
        ["N", "종목명", "현재가", "전일비", "등락률", "액면가", "PER", "ROE", "ROA", "PBR", " 유보율"],
    ]
    return columns


def del_unnecessary(df):
    # 병합용 '종목명' 외에 중복/불필요 컬럼 제거
    for c in ("N", "현재가", "전일비", "등락률", "액면가"):
        if c in df.columns:
            del df[c]


def save_csv(df, fileName):
    df.to_csv(fileName, index=False, encoding='utf-8-sig')


# -------------------------------
# 핵심: 시세 데이터 수집 (안정화 버전)
# -------------------------------
def gathering_naver_stocks(driver, sosok, page):
    """
    KOSPI/KOSDAQ 시가총액 페이지에서 4가지 옵션 세트를 적용해
    표가 갱신될 때마다 파싱하여 하나의 DataFrame으로 병합.
    stale element를 피하기 위해:
      - safe_click
      - click_apply_and_wait (staleness + 새 표 대기)
      - 표 존재 대기 후 page_source 파싱
    """
    try:
        columns = create_column()
        df = pd.DataFrame()

        pg_num = f"http://finance.naver.com/sise/sise_market_sum.nhn?sosok={sosok}&page={page}"
        print(f"URL: {pg_num}")
        driver.get(pg_num)

        # 페이지 로딩 후 표가 뜰 때까지 대기
        wait_for_table(driver)

        for num in range(1, 5):
            # 옵션 세트 적용 (내부에서 적용 후 표 재랜더링 완료까지 대기)
            select_options(num, driver)

            # 표가 안정되었으니 파싱
            soup = BeautifulSoup(driver.page_source, "lxml")
            table = soup.find("table", attrs={"class": "type_2"})
            # print(f"Table found: {table is not None}")
            if table is None:
                print("Table not found on page")
                continue

            res = []
            table_rows = table.find_all("tr")
            for tr in table_rows:
                td = tr.find_all("td")
                row = [t.text.strip() for t in td if t.text.strip()]
                if row:
                    row = row[: len(columns[num - 1])]
                    if len(row) == len(columns[num - 1]):
                        res.append(row)

            cur_df = pd.DataFrame(res, columns=columns[num - 1])
            # print(f"DataFrame created with {len(cur_df)} rows")

            if not df.empty:
                del_unnecessary(cur_df)
                df = pd.merge(df, cur_df, on="종목명", how="inner")
            else:
                df = cur_df

        return df

    except Exception as e:
        print("An error occurred: ", e)
        return None


# -------------------------------
# 배당 데이터 수집
# -------------------------------
def get_dividend_data():
    url = "https://finance.naver.com/sise/dividend_list.nhn"
    res = []
    for page in range(1, 28):  # 테스트용 1~4페이지. 전체는 28p
        pg_url = f"{url}?&page={page}"
        source = urllib.request.urlopen(pg_url).read()
        soup = BeautifulSoup(source, "lxml")

        table = soup.find("table", attrs={"class": "type_1 tb_ty"})
        if not table:
            continue
        table_rows = table.find_all("tr")

        for tr in table_rows:
            td = tr.find_all("td")
            row = [t.text.strip() for t in td if t.text.strip()]
            if row:
                res.append(row)

    # 열 개수 변동에 대비해 자르기/채우기 로직을 넣어도 됨
    cols = ["종목명", "현재가", "기준월", "배당금", "수익률", "배당성향",
            "배당_ROE", "배당_PER", "배당_PBR", "1년전", "2년전", "3년전"]
    # row 길이 불일치 방지
    cleaned = []
    for r in res:
        if len(r) >= len(cols):
            cleaned.append(r[:len(cols)])

    df = pd.DataFrame(cleaned, columns=cols)
    if "현재가" in df.columns:
        del df["현재가"]
    return df


# -------------------------------
# 메인
# -------------------------------
if __name__ == "__main__":
    driver = init_driver()

    kospi = pd.DataFrame()
    kosdaq = pd.DataFrame()
    all_stocks = pd.DataFrame()

    try:
        for sosok in range(0, 2):  # 0: KOSPI, 1: KOSDAQ
            total = pd.DataFrame()
            for page in range(1, 33):  # 테스트용 1~2페이지. 실제는 1~30 (KOSDAQ은 1~29)
                if sosok == 1 and page > 32:
                    continue
                df = gathering_naver_stocks(driver, sosok, page)
                if df is not None and not df.empty:
                    total = pd.concat([total, df], ignore_index=True)

            if sosok == 0:
                kospi = total
            elif sosok == 1:
                kosdaq = total

        all_stocks = pd.concat([kospi, kosdaq], ignore_index=True)

    finally:
        # 크롬 닫기
        driver.quit()

    # Debug 출력
    if all_stocks is not None:
        print(all_stocks.head(5))
    else:
        print("No data collected for total DataFrame.")
    if kospi is not None:
        print(kospi.head(5))
    else:
        print("No data collected for kospi DataFrame.")
    if kosdaq is not None:
        print(kosdaq.head(5))
    else:
        print("No data collected for kosdaq DataFrame.")

    # 배당 데이터
    df_div = get_dividend_data()
    print(df_div.head(5))

    # 병합
    if all_stocks is None or all_stocks.empty:
        all_stocks = pd.DataFrame(columns=df_div.columns)
    try:
        merged_df = pd.merge(all_stocks, df_div, on="종목명", how="outer")
        merged_df = merged_df.fillna(0)
        merged_df = merged_df.sort_values(by="종목명").reset_index(drop=True)
        print(merged_df.head(5))
    except Exception as e:
        print(f"An error occurred during the merge: {e}")
        merged_df = pd.DataFrame()

    # 저장
    d = datetime.datetime.today()
    date = d.strftime("%y%m%d")

    os.makedirs("scraping", exist_ok=True)

    if kospi is not None and not kospi.empty:
        save_csv(kospi, f"scraping/{date}_naver_stocks_kospi.csv")
    if kosdaq is not None and not kosdaq.empty:
        save_csv(kosdaq, f"scraping/{date}_naver_stocks_kosdaq.csv")
    if all_stocks is not None and not all_stocks.empty:
        save_csv(all_stocks, f"scraping/{date}_naver_stocks_total.csv")

    save_csv(df_div, f"scraping/{date}_naver_stocks_dividend.csv")
    save_csv(merged_df, f"scraping/{date}_naver_stocks_all.csv")

    print(merged_df.head(5))
    print("Naver stock data saved successfully.")
