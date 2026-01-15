import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.2", layout="centered")

# --- 데이터베이스 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 실적 테이블: 유연한 구조를 위해 데이터를 JSON이나 다른 방식으로 저장할 수도 있으나, 
    # 기존 설계 유지 및 호환성을 위해 최대 10개 항목까지 대응 가능한 구조로 유지하거나 
    # 확장형 테이블 설계를 권장하지만, 일단 현재 구조에서 항목명 매핑 방식으로 진행합니다.
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 
                  v1 INTEGER, v2 INTEGER, v3 INTEGER, v4 INTEGER, v5 INTEGER,
                  v6 INTEGER, v7 INTEGER, v8 INTEGER, v9 INTEGER, v10 INTEGER,
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    
    # 설정 테이블: 항목 무제한 추가 가능
    c.execute('''CREATE TABLE IF NOT EXISTS settings_v3
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT, price INTEGER)''')
    
    c.execute("SELECT count(*) FROM settings_v3")
    if c.fetchone()[0] == 0:
        default_settings = [
            ('일반필름', 9000), ('풀필름', 18000), ('젤리', 9000), ('케이블', 15000), ('어댑터', 23000)
        ]
        c.executemany("INSERT INTO settings_v3 (display_name, price) VALUES (?, ?)", default_settings)
    
    conn.commit()
    conn.close()

init_db()

def load_settings():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings_v3", conn)
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

# --- 사이드바: 항목 관리 (항목 추가/삭제 기능 포함) ---
with st.sidebar:
    st.header("⚙️ 항목 및 단가 관리 >> setting")
    df_settings = load_settings()
    
    # 1. 항목 추가 기능
    with st.expander("➕ 새 항목 추가"):
        with st.form("add_item_form"):
            add_name = st.text_input("항목명 (예: 케이스)")
            add_price = st.number_input("단가", min_value=0, step=1000)
            if st.form_submit_button("항목 리스트에 추가"):
                if add_name:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO settings_v3 (display_name, price) VALUES (?, ?)", (add_name, add_price))
                    conn.commit()
                    conn.close()
                    st.rerun()

    # 2. 기존 항목 수정 및 삭제
    st.write("---")
    new_data = []
    items_to_delete = []
    
    with st.form("edit_settings_form"):
        for i, row in df_settings.iterrows():
            c1, c2 = st.columns([3, 1])
            n_name = c1.text_input(f"품목 {i+1} 이름", value=row['display_name'], key=f"nm_{row['id']}")
            n_price = c1.number_input(f"품목 {i+1} 단가", value=int(row['price']), step=1000, key=f"pr_{row['id']}")
            if c2.checkbox("삭제", key=f"del_{row['id']}"):
                items_to_delete.append(row['id'])
            new_data.append((n_name, n_price, row['id']))
        
        if st.form_submit_button("변경사항 저장"):
            conn = get_connection()
            c = conn.cursor()
            # 삭제 처리
            for del_id in items_to_delete:
                c.execute("DELETE FROM settings_v3 WHERE id = ?", (del_id,))
            # 업데이트 처리
            for name, price, idx in new_data:
                if idx not in items_to_delete:
                    c.execute("UPDATE settings_v3 SET display_name=?, price=? WHERE id=?", (name, price, idx))
            conn.commit()
            conn.close()
            st.rerun()

# 설정 데이터 로드
settings = load_settings()
item_list = settings.to_dict('records') # [{'id':1, 'display_name':'...', 'price':...}, ...]

# --- CSS 설정 (v1.0 디자인 복구 유지) ---
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { display: flex !important; gap: 5px !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 1 0% !important; min-width: 0 !important; }
    .stButton>button { width: 100% !important; height: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

# 1. 상단 날짜 및 휴무
st.write(f"### 💼 {user_name}님 실적 (v1.2)")
top_c1, top_c2 = st.columns([2, 1])
selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = selected_date.strftime("%Y-%m-%d")

# 데이터 불러오기 (v1~v10까지 대응)
df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty

if top_c2.button("🌴 휴무", use_container_width=True):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary (직원명, 날짜, 인센티브, 합계, 비고) 
                 VALUES (?, ?, 0, 0, ?)''', (user_name, str_date, "휴무"))
    conn.commit()
    conn.close()
    st.rerun()

# 2. 최근 기입 현황 (동략)
st.write("**🗓️ 최근 기입 현황**")
# ... (기존 현황 테이블 코드 생략) ...
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

# 4. 동적 수량 입력창 (설정된 항목 수만큼 생성)
st.write("**📦 품목 수량 입력**")
input_values = []
cols = st.columns(2)
for i, item in enumerate(item_list):
    col_idx = i % 2
    default_val = int(existing_row.iloc[0][f"v{i+1}"]) if is_edit and f"v{i+1}" in existing_row.columns and not pd.isna(existing_row.iloc[0][f"v{i+1}"]) else 0
    val = cols[col_idx].number_input(item['display_name'], min_value=0, value=default_val, key=f"input_{item['id']}")
    input_values.append(val)

if st.button("✅ 최종 실적 저장", use_container_width=True, type="primary"):
    # 합계 계산
    items_total = sum(v * p['price'] for v, p in zip(input_values, item_list))
    daily_sum = st.session_state.current_incen_sum + items_total
    
    # DB 저장 준비 (v1~v10)
    save_values = [user_name, str_date, st.session_state.current_incen_sum]
    for i in range(10): # 최대 10개 항목까지 대응
        save_values.append(input_values[i] if i < len(input_values) else 0)
    save_values.extend([daily_sum, "정상"])
    
    conn = get_connection()
    c = conn.cursor()
    placeholders = ",".join(["?"] * len(save_values))
    c.execute(f"INSERT OR REPLACE INTO salary VALUES ({placeholders})", save_values)
    conn.commit()
    conn.close()
    st.success("저장 성공!")
    st.rerun()

# 5. 리포트 (동적 항목 대응)
st.divider()
st.subheader("📊 정산 및 제출 리포트")
# (기간 계산 로직 동일)
if selected_date.day >= 13:
    start_dt, end_dt = date(selected_date.year, selected_date.month, 13), (selected_date.replace(day=28) + timedelta(days=20)).replace(day=12)
else:
    end_dt, start_dt = selected_date.replace(day=12), (selected_date.replace(day=1) - timedelta(days=10)).replace(day=13)

period_df = df_all[(pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜", ascending=True)

if not period_df.empty:
    # 정산 기간 및 실수령액 표기 생략...
    total_extra = period_df["합계"].sum()
    st.info(f"정산 기간 내 총 합계: {total_extra:,}원")

    # 동적 헤더 표 생성
    html_code = f"""<table style="width:100%; border-collapse:collapse; text-align:center; font-size:10px;">
        <tr style="background-color:#f8f9fa;">
            <th style="padding:4px; border:1px solid #eee;">날짜</th>
            <th style="padding:4px; border:1px solid #eee;">인센</th>"""
    for item in item_list:
        html_code += f'<th style="padding:4px; border:1px solid #eee;">{item["display_name"][:2]}</th>'
    html_code += '<th style="padding:4px; border:1px solid #eee;">합계</th></tr>'

    for _, r in period_df.iterrows():
        html_code += f"<tr><td style='padding:4px; border:1px solid #eee;'>{r['날짜'][5:]}</td>"
        html_code += f"<td style='padding:4px; border:1px solid #eee;'>{r['인센티브']:,}</td>"
        for i in range(len(item_list)):
            html_code += f"<td style='padding:4px; border:1px solid #eee;'>{r[f'v{i+1}']}</td>"
        html_code += f"<td style='padding:4px; border:1px solid #eee; font-weight:bold;'>{r['합계']:,}</td></tr>"
    
    # 합계 행 생략...
    html_code += "</table>"
    st.markdown(html_code, unsafe_allow_html=True)
