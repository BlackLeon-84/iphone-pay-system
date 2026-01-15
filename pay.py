import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템", layout="centered")

# --- 데이터베이스 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # [에러 해결 핵심] '비고' 컬럼이 있는지 확인하고 없으면 테이블을 새로 만듭니다.
    try:
        c.execute("SELECT 비고 FROM salary LIMIT 1")
    except sqlite3.OperationalError:
        # '비고' 컬럼이 없는 구형 테이블이라면 삭제
        c.execute("DROP TABLE IF EXISTS salary")
    
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    conn.commit()
    conn.close()

init_db()

# --- 이하 코드는 이전과 동일합니다 ---
# (중략 - 태완님이 가지고 계신 최신 코드를 그대로 유지하되, 위 init_db 부분만 교체하시면 됩니다)
