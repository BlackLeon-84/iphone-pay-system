import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.1.3", layout="centered")

# --- 데이터베이스 및 기본 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings_v2
                 (id TEXT PRIMARY KEY, display_name TEXT, price INTEGER)''')
    
    c.execute("SELECT count(*) FROM settings_v2")
    if c.fetchone()[0] == 0:
        default_settings = [
            ('item1', '일반필름', 9000), ('item2', '풀필름', 18000), 
            ('item3', '젤리', 9000), ('item4', '케이블', 15000), ('item5', '어댑터', 23000)
        ]
        c.executemany("INSERT INTO settings_v2 VALUES (?, ?, ?)", default_settings)
    conn.commit()
    conn.close()

init_db()

def load_settings():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings_v2", conn)
    conn.close()
    return df

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

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 항목 및 단가 관리")
    df_settings = load_settings()
    new_data = []
    with st.form("settings_form"):
        for i, row in df_settings.iterrows():
            st.markdown(f"**품목 {i+1}**")
            n_name = st.text_input(f"이름", value=row['display_name'], key=f"nm_{row['id']}")
            n_price = st.number_input(f"단가", value=int(row['price']), step=1000, key=f"pr_{row['id']}")
            new_data.append((n_name, n_price, row['id']))
        if st.form_submit_button("설정 저장"):
            conn = get_connection()
            c = conn.cursor()
            c.executemany("UPDATE settings_v2 SET display_name=?, price=? WHERE id=?", new_data)
            conn.commit()
            conn.close()
            st.rerun()

settings = load_settings()
item_names = settings['display_name'].tolist()
item_prices = settings['price'].tolist()

# --- CSS 설정 (버튼 꽉 차게 고정) ---
st.markdown("""
    <style>
    .version-text { font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }
    
    /* [수정] 버튼 3개를 감싸는 투명 컨테이너 설정 */
    div.stButtonGroup { width: 100% !important; text-align: center; }
    div.stButtonGroup > div { width: 100% !important; display: flex !important; }
    
    /* 버튼 공백 제거 및 풀 사이즈 */
    [data-testid="column"] { min-width: 0px !important; flex: 1 1 0% !important; padding: 0 2px !important; }
    div[data-testid="stHorizontalBlock"] { gap: 0px !important; }

    .stButton>button { 
        width: 100% !important; 
        height: 45px !important; 
        padding: 0px !important; 
        font-weight: bold;
    }
    
    .report-table { width: 100%; border-collapse: collapse; font-size: 10px; text-align: center; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 4px 1px !important; white-space: nowrap; }
    .report-table th { background-color: #f8f9fa; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="version-text">v1.1.3-stable</p>', unsafe_allow_html=True)

# 1. 상단 날짜 및 휴무
st.write(f"### 💼 {user_name}님 실적")
top_c1, top_c2 = st.columns([2, 1])
selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = selected_date.strftime("%Y-%m-%d")

df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty

with top_c2:
    if st.button("🌴 휴무", use_container_width=True):
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?)''', (user_name, str_date, "휴무"))
        conn.commit()
        conn.close()
        st.rerun()

# 2. 최근 기입 현황
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
add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=0, label_visibility="collapsed")

# [수정] 추가/취소/리셋 버튼을 강제로 꽉 차게 배치
btn_c1, btn_c2, btn_c3 = st.columns(3)
with btn_c1:
    if st.button("➕ 추가", key="add_btn"):
        st.session_state.current_incen_sum += add_amount
        st.session_state.incen_history.append(add_amount)
        st.rerun()
with btn_c2:
    if st.button("↩️ 취소", key="undo_btn"):
        if st.session_state.incen_history:
            st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
            st.rerun()
with btn_c3:
    if st.button("🧹 리셋", key="reset_btn"):
        st.session_state.current_incen_sum = 0
        st.session_state.incen_history = []
        st.rerun()

# 4. 수량 입력
f_c1, f_c2 = st.columns(2)
v1 = f_c1.number_input(item_names[0], 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
v2 = f_c2.number_input(item_names[1], 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
v3 = f_c1.number_input(item_names[2], 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
v4 = f_c2.number_input(item_names[3], 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
v5 = st.number_input(item_names[4], 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)

if st.button("✅ 최종 실적 저장", use_container_width=True, type="primary"):
    daily_sum = st.session_state.current_incen_sum + (v1*item_prices[0]) + (v2*item_prices[1]) + (v3*item_prices[2]) + (v4*item_prices[3]) + (v5*item_prices[4])
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (user_name, str_date, st.session_state.current_incen_sum, v1, v2, v3, v4, v5, daily_sum, "정상"))
    conn.commit()
    conn.close()
    st.success("저장 성공!")
    st.rerun()

# 5. 정산 리포트
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
    st.info(f"📅 **{end_dt.month}월 정산 내역**")
    st.markdown(f"**💰 총 수당: {total_extra:,}원 | 🏦 실수령: {final_pay:,}원**")
    
    html_code = f"""<table class="report-table">
        <tr>
            <th style="width:35px;">날짜</th><th>인센</th><th>{item_names[0][:2]}</th><th>{item_names[1][:2]}</th><th>{item_names[2][:2]}</th><th>{item_names[3][:2]}</th><th>{item_names[4][:2]}</th><th>합계</th>
        </tr>"""
    for _, r in period_df.iterrows():
        d_val = datetime.strptime(r['날짜'], "%Y-%m-%d")
        html_code += f"<tr><td>{d_val.day}일</td><td>{r['인센티브']:,}</td><td>{r['일반필름']}</td><td>{r['풀필름']}</td><td>{r['젤리']}</td><td>{r['케이블']}</td><td>{r['어댑터']}</td><td style='font-weight:bold;'>{r['합계']:,}</td></tr>"
    html_code += "</table>"
    st.markdown(html_code, unsafe_allow_html=True)
