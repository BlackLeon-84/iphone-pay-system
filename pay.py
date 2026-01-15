import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.0", layout="centered")

# --- 데이터베이스 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 실적 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    # [v1.0 추가] 단가 및 항목 설정 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (item_name TEXT PRIMARY KEY, price INTEGER)''')
    
    # 초기값 설정 (데이터가 없을 때만)
    c.execute("SELECT count(*) FROM settings")
    if c.fetchone()[0] == 0:
        default_settings = [
            ('일반필름', 9000), ('풀필름', 18000), 
            ('젤리', 9000), ('케이블', 15000), ('어댑터', 23000)
        ]
        c.executemany("INSERT INTO settings VALUES (?, ?)", default_settings)
    
    conn.commit()
    conn.close()

init_db()

# --- 설정 데이터 불러오기 ---
def load_settings():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings", conn)
    conn.close()
    # 딕셔너리 형태로 변환 {항목명: 단가}
    return dict(zip(df['item_name'], df['price']))

# --- 로그인 세션 ---
STAFF_LIST = ["성훈", "남근"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        if st.form_submit_button("입장하기", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.user_name = user_id
            st.rerun()
    st.stop()

user_name = st.session_state.user_name

# --- 사이드바: 항목 및 단가 관리 (설정 페이지) ---
with st.sidebar:
    st.header("⚙️ 시스템 설정 (v1.0)")
    st.write("항목명과 단가를 수정하세요.")
    current_settings = load_settings()
    new_settings = {}
    
    with st.form("settings_form"):
        for item, price in current_settings.items():
            new_price = st.number_input(f"{item} 단가", value=int(price), step=1000)
            new_settings[item] = new_price
        
        if st.form_submit_button("설정 저장"):
            conn = get_connection()
            c = conn.cursor()
            for item, price in new_settings.items():
                c.execute("UPDATE settings SET price = ? WHERE item_name = ?", (price, item))
            conn.commit()
            conn.close()
            st.success("단가가 수정되었습니다!")
            st.rerun()

# 변수 할당 (계산 및 표기용)
price_dict = load_settings()
items = list(price_dict.keys()) # ['일반필름', '풀필름', '젤리', '케이블', '어댑터']

# --- CSS 및 메인 화면 ---
st.markdown("""<style>
    div[data-testid="stHorizontalBlock"] { display: flex !important; gap: 5px !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 1 0% !important; min-width: 0 !important; }
</style>""", unsafe_allow_html=True)

st.write(f"### 💼 {user_name}님 실적 (v1.0)")
top_c1, top_c2 = st.columns([2, 1])
selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = selected_date.strftime("%Y-%m-%d")

df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty

# ... [입력 로직 및 최근 기입 현황은 이전과 동일 (생략 방지를 위해 핵심만 유지)] ...
# (중략: 최근 기입 현황 테이블 코드)
st.write("**🗓️ 최근 기입 현황**")
table_html = """<table style="width:100%; border-collapse: collapse; table-layout: fixed;"><tr style="background-color: #f8f9fa;">"""
for i in range(7):
    d = date.today() - timedelta(days=6-i)
    table_html += f"<th style='border:1px solid #ddd; padding:5px; font-size:10px; text-align:center;'>{d.day}일</th>"
table_html += "</tr><tr>"
for i in range(7):
    d = date.today() - timedelta(days=6-i)
    str_check = d.strftime("%Y-%m-%d")
    target_row = df_all[df_all["날짜"] == str_check]
    icon, bg = "⚪", "#ffffff"
    if not target_row.empty:
        if target_row.iloc[0]["비고"] == "휴무": icon, bg = "💤", "#e1f5fe"
        else: icon, bg = "✅", "#e8f5e9"
    table_html += f"<td style='border:1px solid #ddd; padding:8px; text-align:center; background-color:{bg}; font-size:16px;'>{icon}</td>"
table_html += "</tr></table>"
st.markdown(table_html, unsafe_allow_html=True)

st.divider()

# 3. 인센티브 입력
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=1000, label_visibility="collapsed")

btn_c1, btn_c2, btn_c3 = st.columns(3)
if btn_c1.button("➕ 추가"):
    st.session_state.current_incen_sum += add_amount
    st.session_state.incen_history.append(add_amount)
    st.rerun()
if btn_c2.button("↩️ 취소") and st.session_state.incen_history:
    st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
    st.rerun()
if btn_c3.button("🧹 리셋"):
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.rerun()

# 4. 수량 입력 (설정된 항목명 사용)
f_c1, f_c2 = st.columns(2)
v_nf = f_c1.number_input(items[0], 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
v_ff = f_c2.number_input(items[1], 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
v_j = f_c1.number_input(items[2], 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
v_c = f_c2.number_input(items[3], 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
v_a = st.number_input(items[4], 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)

if st.button("✅ 최종 실적 저장", use_container_width=True, type="primary"):
    # 가변 단가 적용 계산
    daily_sum = st.session_state.current_incen_sum + \
                (v_nf * price_dict[items[0]]) + (v_ff * price_dict[items[1]]) + \
                (v_j * price_dict[items[2]]) + (v_c * price_dict[items[3]]) + (v_a * price_dict[items[4]])
    
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
    conn.commit()
    conn.close()
    st.success("저장 성공!")
    st.rerun()

# 5. 정산 현황 및 제출 리포트 (v1.0)
st.divider()
st.subheader("📊 정산 및 제출 리포트")
BASE_SALARY, INSURANCE = 3500000, 104760

if selected_date.day >= 13:
    start_dt, end_dt = date(selected_date.year, selected_date.month, 13), (selected_date.replace(day=28) + timedelta(days=20)).replace(day=12)
else:
    end_dt, start_dt = selected_date.replace(day=12), (selected_date.replace(day=1) - timedelta(days=10)).replace(day=13)

period_df = df_all[(pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜", ascending=True)

if not period_df.empty:
    total_extra = period_df["합계"].sum()
    final_pay = int(BASE_SALARY + total_extra - INSURANCE)
    
    st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left:5px solid #ff4b4b; margin-bottom:15px;">
            <p style="margin:0; font-size:12px; color:#666;">정산 기간: {start_dt} ~ {end_dt}</p>
            <p style="margin:5px 0; font-size:18px; font-weight:bold;">💰 총 수당(인센+판매): {total_extra:,}원</p>
            <p style="margin:0; font-size:22px; font-weight:bold; color:#ff4b4b;">🏦 최종 실수령액: {final_pay:,}원</p>
        </div>
    """, unsafe_allow_html=True)
    
    # [제출용 표] 설정된 항목명으로 헤더 구성
    html_code = f"""<table style="width:100%; border-collapse:collapse; table-layout:fixed; font-size:10px; text-align:center;">
        <tr style="background-color:#f8f9fa; border-bottom:2px solid #ddd;">
            <th style="padding:4px; border:1px solid #eee; width:14%;">날짜</th>
            <th style="padding:4px; border:1px solid #eee;">인센티브</th>
            <th style="padding:4px; border:1px solid #eee;">{items[0][:2]}</th>
            <th style="padding:4px; border:1px solid #eee;">{items[1][:2]}</th>
            <th style="padding:4px; border:1px solid #eee;">{items[2][:2]}</th>
            <th style="padding:4px; border:1px solid #eee;">{items[3][:2]}</th>
            <th style="padding:4px; border:1px solid #eee;">{items[4][:2]}</th>
            <th style="padding:4px; border:1px solid #eee;">합계</th>
        </tr>"""
    
    for _, r in period_df.iterrows():
        html_code += f"""<tr style="border-bottom:1px solid #eee;">
            <td style="padding:4px; border:1px solid #eee;">{r['날짜'][5:]}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['인센티브']:,}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['일반필름']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['풀필름']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['젤리']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['케이블']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['어댑터']}</td>
            <td style="padding:4px; border:1px solid #eee; font-weight:bold;">{r['합계']:,}</td>
        </tr>"""
    
    # 합계 행
    html_code += f"""<tr style="background-color:#fff3f3; font-weight:bold; border-top:2px solid #ff4b4b;">
            <td style="padding:4px; border:1px solid #eee;">합계</td>
            <td style="padding:4px; border:1px solid #eee;">{period_df['인센티브'].sum():,}</td>
            <td style="padding:4px; border:1px solid #eee;">{period_df['일반필름'].sum()}</td>
            <td style="padding:4px; border:1px solid #eee;">{period_df['풀필름'].sum()}</td>
            <td style="padding:4px; border:1px solid #eee;">{period_df['젤리'].sum()}</td>
            <td style="padding:4px; border:1px solid #eee;">{period_df['케이블'].sum()}</td>
            <td style="padding:4px; border:1px solid #eee;">{period_df['어댑터'].sum()}</td>
            <td style="padding:4px; border:1px solid #eee; color:#ff4b4b;">{total_extra:,}</td>
        </tr></table>"""
    st.markdown(html_code, unsafe_allow_html=True)

    # 개별 상세 (생략)
