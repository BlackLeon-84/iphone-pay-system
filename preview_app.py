import calendar
from copy import deepcopy
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

from payroll_core import daily_total, overtime_pay, payroll_summary, safe_date, safe_int, settlement_period


st.set_page_config(page_title="정산 테스트", layout="wide", initial_sidebar_state="collapsed")

STAFF = ["태완", "남근", "성훈", "대원", "성욱", "테스트"]
OVERTIME_STAFF = {"태완", "남근"}
CONFIGS = {
    "태완": [3_000_000, 13, 110_410, ["필름", "풀필름", "젤리", "케이블", "어댑터", "뒷1", "뒷2"], [9_000, 19_000, 9_000, 13_000, 21_000, 10_000, 20_000], 4_000, True],
    "남근": [3_000_000, 21, 104_300, ["일반필름", "풀필름", "젤리", "케이블", "어댑터", "뒷유리", "후카필름"], [9_000, 19_000, 9_000, 13_000, 21_000, 10_000, 9_000], 3_000, True],
    "성훈": [3_500_000, 15, 104_760, ["일반필름", "풀필름", "젤리", "케이블", "어댑터", "후카필름", ""], [9_000, 18_000, 9_000, 13_000, 21_000, 9_000, 0], 0, True],
    "대원": [2_500_000, 8, 104_760, ["일반필름", "풀필름", "젤리", "케이블", "어댑터", "후카필름", ""], [9_000, 18_000, 9_000, 13_000, 21_000, 9_000, 0], 0, True],
    "성욱": [2_500_000, 1, 209_530, ["필름", "풀필름", "젤리", "케이블", "어댑터", "뒷유리", "뒷추가"], [9_000, 18_000, 8_000, 13_000, 21_000, 10_000, 10_000], 0, True],
    "테스트": [2_500_000, 1, 104_760, ["일반필름", "풀필름", "젤리", "케이블", "어댑터", "후카필름", ""], [9_000, 18_000, 9_000, 13_000, 21_000, 9_000, 0], 0, False],
}


def config_dict(values):
    return {
        "base_salary": values[0], "start_day": values[1], "insurance": values[2],
        "item_names": values[3], "item_prices": values[4], "overtime_rate": values[5], "apply_global": values[6],
    }


def seed_state():
    if "preview_configs" in st.session_state:
        return
    st.session_state.preview_configs = {name: config_dict(deepcopy(values)) for name, values in CONFIGS.items()}
    st.session_state.preview_passwords = {name: "0000" for name in STAFF}
    st.session_state.preview_records = {name: {} for name in STAFF}
    st.session_state.preview_deductions = {name: {} for name in STAFF}
    for name in STAFF:
        cfg = st.session_state.preview_configs[name]
        counts = [1, 0, 2, 0, 1, 0, 0]
        incentive = 35_000
        overtime = overtime_pay("21:00", cfg["overtime_rate"], name in OVERTIME_STAFF)
        day = date.today() - timedelta(days=1)
        st.session_state.preview_records[name][day.isoformat()] = {
            "직원명": name, "날짜": day.isoformat(), "인센티브": incentive, "시간수당": overtime,
            "퇴근시간": "21:00" if name in OVERTIME_STAFF else "20:00", "합계": daily_total(incentive, counts, cfg["item_prices"], overtime),
            "비고": "정상 | 15000+20000", **{f"item{i + 1}": count for i, count in enumerate(counts)},
        }
        off = date.today() - timedelta(days=3)
        st.session_state.preview_records[name][off.isoformat()] = {
            "직원명": name, "날짜": off.isoformat(), "인센티브": 0, "시간수당": 0, "퇴근시간": "휴무",
            "합계": 0, "비고": "휴무", **{f"item{i}": 0 for i in range(1, 8)},
        }


def money(value):
    return f"{safe_int(value):,}원"


def parse_parts(row):
    remark = str(row.get("비고", ""))
    if "|" in remark:
        return [safe_int(value) for value in remark.rsplit("|", 1)[1].split("+") if safe_int(value)]
    value = safe_int(row.get("인센티브"))
    return [value] if value else []


def period_options(start_day):
    periods = []
    start, end = settlement_period(date.today(), start_day)
    for _ in range(12):
        periods.append((start, end))
        start, end = settlement_period(start - timedelta(days=1), start_day)
    return periods


def rows_for_period(user, start, end):
    return [row for key, row in st.session_state.preview_records[user].items() if start <= date.fromisoformat(key) <= end]


def excel_bytes(rows, cfg):
    output = []
    for row in sorted(rows, key=lambda value: value["날짜"]):
        item = {"날짜": row["날짜"], "인센티브": safe_int(row["인센티브"])}
        if row["직원명"] in OVERTIME_STAFF:
            item["시간수당"] = safe_int(row["시간수당"])
        for i, name in enumerate(cfg["item_names"]):
            item[name or f"품목{i + 1}"] = safe_int(row[f"item{i + 1}"])
        item["합계"] = safe_int(row["합계"])
        item["비고"] = row["비고"]
        output.append(item)
    buffer = BytesIO()
    pd.DataFrame(output).to_excel(buffer, index=False)
    return buffer.getvalue()


def set_selected_day(day):
    st.session_state.selected_day = day


def calendar_view(user):
    records = st.session_state.preview_records[user]
    shown = st.session_state.get("calendar_month", date.today().replace(day=1))
    with st.container(key="calendar_head"):
        head = st.columns([1, 4, 1, 1])
    if head[0].button("이전", key="month_prev", width="stretch"):
        st.session_state.calendar_month = (shown - timedelta(days=1)).replace(day=1)
        st.rerun()
    head[1].markdown(f"<div class='calendar-title'>{shown.year}년 {shown.month}월</div>", unsafe_allow_html=True)
    if head[2].button("오늘", key="month_today", width="stretch"):
        st.session_state.calendar_month = date.today().replace(day=1)
        set_selected_day(date.today())
        st.rerun()
    if head[3].button("다음", key="month_next", width="stretch"):
        year, month = (shown.year + 1, 1) if shown.month == 12 else (shown.year, shown.month + 1)
        st.session_state.calendar_month = date(year, month, 1)
        st.rerun()
    weekday_cols = st.columns(7)
    for col, label in zip(weekday_cols, ["월", "화", "수", "목", "금", "토", "일"]):
        col.markdown(f"<div class='weekday'>{label}</div>", unsafe_allow_html=True)
    for week_index, week in enumerate(calendar.Calendar(firstweekday=0).monthdatescalendar(shown.year, shown.month)):
        cols = st.columns(7)
        for index, day in enumerate(week):
            if day.month != shown.month:
                cols[index].markdown("<div class='cal-empty'></div>", unsafe_allow_html=True)
                continue
            row = records.get(day.isoformat())
            marker = "-" if row and row.get("비고") == "휴무" else "●" if row else "○" if day < date.today() else ""
            disabled = day > date.today()
            selected = day == st.session_state.selected_day
            label = f"{day.day}\n{marker}"
            with cols[index].container(key=f"cal_{week_index}_{index}_{'selected' if selected else 'normal'}"):
                if st.button(label, key=f"day_{day.isoformat()}", disabled=disabled, width="stretch"):
                    set_selected_day(day)
                    st.rerun()


def save_daily(user, cfg, selected):
    context = f"{user}_{selected.isoformat()}"
    parts = st.session_state.get(f"parts_{context}", []).copy()
    pending = safe_int(st.session_state.get(f"pending_{context}"))
    if pending:
        parts.append(pending)
    incentive = sum(parts)
    counts = [safe_int(st.session_state.get(f"qty_{context}_{i}")) for i in range(7)]
    end_time = st.session_state.get(f"end_{context}", "20:00")
    overtime = overtime_pay(end_time, cfg["overtime_rate"], user in OVERTIME_STAFF)
    st.session_state.preview_records[user][selected.isoformat()] = {
        "직원명": user, "날짜": selected.isoformat(), "인센티브": incentive, "시간수당": overtime,
        "퇴근시간": end_time, "합계": daily_total(incentive, counts, cfg["item_prices"], overtime),
        "비고": "정상" + (" | " + "+".join(map(str, parts)) if parts else ""),
        **{f"item{i + 1}": count for i, count in enumerate(counts)},
    }
    st.session_state[f"parts_{context}"] = parts
    st.session_state[f"pending_{context}"] = 0
    st.session_state.save_notice = f"{selected:%m월 %d일} 기록을 테스트 저장소에 저장했습니다."


def add_incentive(context):
    value = safe_int(st.session_state.get(f"pending_{context}"))
    if value:
        st.session_state[f"parts_{context}"].append(value)
        st.session_state[f"pending_{context}"] = 0


def save_zero_daily(user, cfg, selected):
    context = f"{user}_{selected.isoformat()}"
    st.session_state[f"parts_{context}"] = []
    st.session_state[f"pending_{context}"] = 0
    save_daily(user, cfg, selected)


def daily_view(user, cfg):
    st.markdown("<div class='eyebrow'>DAILY WORKSPACE</div><h1>오늘의 기록</h1>", unsafe_allow_html=True)
    st.caption("달력에서 빠진 날짜를 확인하고, 선택한 날의 실적을 입력합니다.")
    with st.container(key="calendar_grid"):
        calendar_view(user)
    selected = st.session_state.selected_day
    row = st.session_state.preview_records[user].get(selected.isoformat(), {})
    context = f"{user}_{selected.isoformat()}"
    if st.session_state.get("loaded_context") != context:
        st.session_state.loaded_context = context
        st.session_state[f"parts_{context}"] = parse_parts(row)
    parts = st.session_state.get(f"parts_{context}", [])

    st.markdown(f"<div class='date-line'><b>{selected:%Y년 %m월 %d일}</b><span>{'저장됨' if row else '미입력'}</span></div>", unsafe_allow_html=True)
    if st.session_state.pop("save_notice", None):
        st.success("저장되었습니다. 운영 데이터에는 반영되지 않았습니다.")

    with st.container(key="work_area"):
        work, live = st.columns([1.7, 1], gap="large")
    with work:
        st.subheader("인센티브")
        amount_col, add_col = st.columns([3, 1])
        amount_col.number_input("추가 금액", min_value=0, step=1_000, key=f"pending_{context}")
        add_col.button("추가", type="primary", width="stretch", key=f"add_{context}", on_click=add_incentive, args=(context,))
        undo, clear = st.columns(2)
        if undo.button("직전 취소", disabled=not parts, width="stretch", key=f"undo_{context}"):
            st.session_state[f"parts_{context}"].pop()
            st.rerun()
        if clear.button("입력 초기화", disabled=not parts, width="stretch", key=f"clear_{context}"):
            st.session_state[f"parts_{context}"] = []
            st.rerun()

        if user in OVERTIME_STAFF:
            times = [f"{hour}:{minute:02d}" for hour in range(20, 24) for minute in range(0, 60, 10)] + ["24:00"]
            saved_time = row.get("퇴근시간", "20:00") if row.get("퇴근시간") != "휴무" else "20:00"
            st.selectbox("퇴근 시간", times, index=times.index(saved_time) if saved_time in times else 0, key=f"end_{context}")

        st.subheader("품목 수량")
        for i, (name, price) in enumerate(zip(cfg["item_names"], cfg["item_prices"])):
            label = name or f"품목 {i + 1}"
            left, right = st.columns([3, 1])
            left.markdown(f"<div class='item-name'><b>{label}</b><small>{money(price)}</small></div>", unsafe_allow_html=True)
            right.number_input(label, min_value=0, value=safe_int(row.get(f"item{i + 1}")), label_visibility="collapsed", key=f"qty_{context}_{i}")

    with live:
        counts = [safe_int(st.session_state.get(f"qty_{context}_{i}", row.get(f"item{i + 1}", 0))) for i in range(7)]
        end_time = st.session_state.get(f"end_{context}", row.get("퇴근시간", "20:00"))
        overtime = overtime_pay(end_time, cfg["overtime_rate"], user in OVERTIME_STAFF)
        total = daily_total(sum(parts) + safe_int(st.session_state.get(f"pending_{context}")), counts, cfg["item_prices"], overtime)
        st.markdown(f"<div class='total-panel'><small>입력 중 합계</small><strong>{money(total)}</strong><p>인센티브 {money(sum(parts))}</p><p>시간수당 {money(overtime)}</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='ledger-title'>추가 내역</div>", unsafe_allow_html=True)
        if parts:
            for index, value in enumerate(parts, 1):
                st.markdown(f"<div class='ledger-row'><span>{index:02d}</span><b>{money(value)}</b></div>", unsafe_allow_html=True)
        else:
            st.caption("추가한 금액이 없습니다.")
        st.button("최종 저장", type="primary", width="stretch", key=f"save_{context}", on_click=save_daily, args=(user, cfg, selected))
        with st.container(key="quick_actions"):
            action_cols = st.columns(3)
        if action_cols[0].button("휴무", width="stretch", key=f"off_{context}"):
            st.session_state.preview_records[user][selected.isoformat()] = {
                "직원명": user, "날짜": selected.isoformat(), "인센티브": 0, "시간수당": 0, "퇴근시간": "휴무", "합계": 0,
                "비고": "휴무", **{f"item{i}": 0 for i in range(1, 8)},
            }
            st.session_state.loaded_context = ""
            st.rerun()
        action_cols[1].button("인센없음", width="stretch", key=f"zero_{context}", on_click=save_zero_daily, args=(user, cfg, selected))
        if action_cols[2].button("삭제", width="stretch", key=f"delete_{context}"):
            st.session_state.preview_records[user].pop(selected.isoformat(), None)
            st.session_state.loaded_context = ""
            st.rerun()


def report_rows(rows, cfg):
    output = []
    for row in sorted(rows, key=lambda item: item["날짜"]):
        output.append({
            "날짜": row["날짜"][5:], "상태": row["비고"].split("|")[0].strip(), "인센티브": safe_int(row["인센티브"]),
            "시간수당": safe_int(row["시간수당"]), "품목": sum(safe_int(row[f"item{i}"]) for i in range(1, 8)), "합계": safe_int(row["합계"]),
        })
    return pd.DataFrame(output)


def monthly_view(user, cfg):
    st.markdown("<div class='eyebrow'>PAYROLL REPORT</div><h1>월간 정산</h1>", unsafe_allow_html=True)
    periods = period_options(cfg["start_day"])
    labels = [f"{end:%Y년 %m월}" for _, end in periods]
    selected_index = st.selectbox("정산 월", range(len(periods)), format_func=lambda i: labels[i], key=f"period_{user}")
    start, end = periods[selected_index]
    key = end.strftime("%Y-%m")
    deductions = st.session_state.preview_deductions[user].setdefault(key, {"Cash": 0, "Card": 0, "CardDeduct": 0, "Etc": 0, "EtcAdd": 0, "EtcAddDesc": "", "CardDetail": []})
    rows = rows_for_period(user, start, end)
    result = payroll_summary(rows, cfg, deductions)

    st.markdown(f"<div class='period-line'>{start:%Y.%m.%d} - {end:%Y.%m.%d}</div>", unsafe_allow_html=True)
    report_mode = st.toggle("보고용 보기", key=f"report_mode_{user}")
    if report_mode:
        st.markdown("<style>.st-key-desktop_identity,.st-key-navigation{display:none!important}.block-container{max-width:520px!important}</style>", unsafe_allow_html=True)
        summary, editor = st.container(), None
    else:
        with st.container(key="monthly_area"):
            summary, editor = st.columns([1.4, 1], gap="large")
    with summary:
        st.markdown(f"<div class='pay-hero'><small>{user} 예상 수령액</small><strong>{money(result['final_pay'])}</strong><span>테스트 데이터 기준</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='breakdown-title'>지급 내역</div>", unsafe_allow_html=True)
        for label, value in [("기본급", cfg["base_salary"]), ("인센티브", result["incentive"]), ("품목", result["items"]), ("시간수당", result["overtime"]), (deductions.get("EtcAddDesc") or "기타 지급", result["extra"])]:
            st.markdown(f"<div class='breakdown-row'><span>{label}</span><b>+ {money(value)}</b></div>", unsafe_allow_html=True)
        st.markdown("<div class='breakdown-title'>공제 내역</div>", unsafe_allow_html=True)
        for label, value in [("보험료", cfg["insurance"]), ("매장 현금", result["cash"]), ("카드 실공제", result["card_real"]), ("기타 공제", result["etc"])]:
            st.markdown(f"<div class='breakdown-row deduction'><span>{label}</span><b>- {money(value)}</b></div>", unsafe_allow_html=True)
    if editor is not None:
        with editor:
            st.subheader("공제 및 지급 편집")
            cash = st.number_input("매장 현금", min_value=0, value=safe_int(deductions["Cash"]), step=10_000, key=f"cash_{user}_{key}")
            card = st.number_input("카드 총 사용액", min_value=0, value=safe_int(deductions["Card"]), step=10_000, key=f"card_{user}_{key}")
            etc = st.number_input("기타 공제", min_value=0, value=safe_int(deductions["Etc"]), step=10_000, key=f"etc_{user}_{key}")
            extra = st.number_input("기타 지급", min_value=0, value=safe_int(deductions["EtcAdd"]), step=10_000, key=f"extra_{user}_{key}")
            extra_desc = st.text_input("기타 지급 내역", value=deductions.get("EtcAddDesc", ""), key=f"extra_desc_{user}_{key}")
            st.markdown("<div class='ledger-title'>카드 공제 제외</div>", unsafe_allow_html=True)
            details = deductions["CardDetail"]
            for index, item in enumerate(details.copy()):
                cols = st.columns([3, 2, 1])
                cols[0].write(item["desc"])
                cols[1].write(money(item["amt"]))
                if cols[2].button("삭제", key=f"remove_card_{user}_{key}_{index}"):
                    details.pop(index)
                    deductions["CardDeduct"] = sum(value["amt"] for value in details)
                    st.rerun()
            add_desc = st.text_input("제외 내역", key=f"card_desc_{user}_{key}")
            add_amount = st.number_input("제외 금액", min_value=0, step=1_000, key=f"card_amount_{user}_{key}")
            if st.button("제외 항목 추가", width="stretch", key=f"add_card_{user}_{key}") and add_desc and add_amount:
                details.append({"desc": add_desc, "amt": int(add_amount)})
                deductions["CardDeduct"] = sum(value["amt"] for value in details)
                st.rerun()
            st.caption(f"카드 실공제 {money(card - sum(value['amt'] for value in details))}")
            if st.button("공제 내역 저장", type="primary", width="stretch", key=f"save_deduct_{user}_{key}"):
                deductions.update({"Cash": cash, "Card": card, "CardDeduct": sum(value["amt"] for value in details), "Etc": etc, "EtcAdd": extra, "EtcAddDesc": extra_desc})
                st.success("테스트 저장소에 저장했습니다.")

    if report_mode:
        return

    st.subheader("일별 명세")
    table = report_rows(rows, cfg)
    if table.empty:
        st.info("이 기간에는 입력된 기록이 없습니다.")
    else:
        st.dataframe(table, hide_index=True, width="stretch")
    st.download_button("정산 리포트 다운로드", excel_bytes(rows, cfg), f"{user}_정산_{start:%m%d}-{end:%m%d}.xlsx", width="stretch")


def profile_view(user, cfg):
    st.markdown("<div class='eyebrow'>PROFILE & SETTINGS</div><h1>내 정보</h1>", unsafe_allow_html=True)
    metrics = st.columns(3)
    metrics[0].metric("기본급", money(cfg["base_salary"]))
    metrics[1].metric("보험료", money(cfg["insurance"]))
    metrics[2].metric("정산 시작일", f"매월 {cfg['start_day']}일")
    st.subheader("적용 품목")
    for name, price in zip(cfg["item_names"], cfg["item_prices"]):
        st.markdown(f"<div class='breakdown-row'><span>{name or '미사용 품목'}</span><b>{money(price)}</b></div>", unsafe_allow_html=True)
    with st.expander("비밀번호 변경"):
        current = st.text_input("현재 비밀번호", type="password", key="current_pw")
        new = st.text_input("새 비밀번호", type="password", key="new_pw")
        confirm = st.text_input("새 비밀번호 확인", type="password", key="confirm_pw")
        if st.button("비밀번호 변경", width="stretch"):
            if current != st.session_state.preview_passwords[user]:
                st.error("현재 비밀번호가 다릅니다.")
            elif len(new) < 4 or new != confirm:
                st.error("4자리 이상 같은 비밀번호를 입력하세요.")
            else:
                st.session_state.preview_passwords[user] = new
                st.success("테스트 비밀번호를 변경했습니다.")
    if user == "태완":
        with st.expander("관리자 설정", expanded=True):
            target = st.selectbox("직원", STAFF, key="admin_target")
            target_cfg = st.session_state.preview_configs[target]
            base = st.number_input("기본급", min_value=0, value=target_cfg["base_salary"], step=10_000, key=f"admin_base_{target}")
            insurance = st.number_input("보험료", min_value=0, value=target_cfg["insurance"], step=1_000, key=f"admin_ins_{target}")
            start_day = st.slider("정산 시작일", 1, 31, value=target_cfg["start_day"], key=f"admin_day_{target}")
            rate = st.number_input("10분당 시간수당", min_value=0, value=target_cfg["overtime_rate"], step=100, disabled=target not in OVERTIME_STAFF, key=f"admin_rate_{target}")
            apply_global = st.checkbox("현재 단가를 과거 기록에도 적용", value=target_cfg["apply_global"], key=f"admin_global_{target}")
            names, prices = [], []
            for i in range(7):
                cols = st.columns([3, 2])
                names.append(cols[0].text_input(f"품목 {i + 1}", value=target_cfg["item_names"][i], key=f"admin_name_{target}_{i}"))
                prices.append(cols[1].number_input(f"단가 {i + 1}", min_value=0, value=target_cfg["item_prices"][i], step=1_000, key=f"admin_price_{target}_{i}"))
            if st.button("설정 저장", type="primary", width="stretch", key=f"admin_save_{target}"):
                target_cfg.update({"base_salary": base, "insurance": insurance, "start_day": start_day, "overtime_rate": rate, "apply_global": apply_global, "item_names": names, "item_prices": prices})
                st.success("테스트 설정만 변경했습니다.")
            if st.button("비밀번호 0000으로 초기화", width="stretch", key=f"admin_pw_{target}"):
                st.session_state.preview_passwords[target] = "0000"
                st.success("테스트 비밀번호를 초기화했습니다.")


def login_view():
    st.markdown("<div class='login-wrap'><div class='eyebrow'>PAYROLL WORKSPACE</div><h1>정산을 더 선명하게.</h1><p>운영과 분리된 디자인 검증 사이트입니다.</p></div>", unsafe_allow_html=True)
    with st.form("login", border=False):
        user = st.selectbox("직원", STAFF, index=5, key="login_user")
        password = st.text_input("테스트 비밀번호", type="password", key="login_password")
        if st.form_submit_button("입장", type="primary", width="stretch", key="login_submit"):
            if password == st.session_state.preview_passwords[user]:
                st.session_state.user = user
                st.session_state.selected_day = date.today()
                st.session_state.calendar_month = date.today().replace(day=1)
                st.rerun()
            else:
                st.error("비밀번호가 다릅니다. 최초 테스트 비밀번호는 0000입니다.")


st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
:root { --ink:#191b1f; --muted:#747982; --line:#e5e7eb; --soft:#f6f7f8; --blue:#2457d6; --green:#23734b; }
html, body, [class*="css"] { font-family:Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); letter-spacing:0; }
.stApp { background:#fff; }
[data-testid="stHeader"], [data-testid="stSidebar"], footer { display:none; }
.block-container { max-width:1320px; padding:28px 28px 110px; }
h1 { font-size:34px!important; line-height:1.1!important; margin:4px 0 6px!important; font-weight:720!important; }
h2, h3 { letter-spacing:0!important; }
.eyebrow { color:var(--blue); font-size:11px; font-weight:750; letter-spacing:.12em; }
.login-wrap { max-width:430px; margin:14vh auto 26px; text-align:center; }
.login-wrap h1 { font-size:46px!important; }
.login-wrap p, .period-line { color:var(--muted); }
[data-testid="stForm"] { border:0; padding:0; }
button { min-height:42px!important; border-radius:6px!important; box-shadow:none!important; }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background:var(--ink)!important; border-color:var(--ink)!important; color:#fff!important; }
input[type="radio"], input[role="switch"] { accent-color:var(--blue)!important; }
label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child { background:var(--blue)!important; border-color:var(--blue)!important; }
label:has(input[role="switch"]:checked) > div:first-of-type { background-color:var(--blue)!important; border-color:var(--blue)!important; }
input, [data-baseweb="select"] > div { border-radius:6px!important; }
.calendar-title { text-align:center; font-size:18px; font-weight:700; padding:9px 0; }
.weekday { color:var(--muted); font-size:12px; text-align:center; padding:8px 0 3px; }
.cal-empty { min-height:42px; }
[class*="st-key-cal_"] button { border:0!important; background:#fff!important; font-size:13px!important; line-height:1.05!important; padding:3px!important; color:var(--ink)!important; }
[class*="st-key-cal_"][class*="selected"] button { background:var(--ink)!important; color:#fff!important; }
.date-line { display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--line); border-bottom:1px solid var(--line); margin:18px 0 24px; padding:14px 2px; }
.date-line span { color:var(--green); font-size:13px; }
.item-name { min-height:48px; display:flex; flex-direction:column; justify-content:center; border-bottom:1px solid var(--line); }
.item-name small { color:var(--muted); margin-top:2px; }
.total-panel { background:var(--ink); color:#fff; padding:24px; border-radius:7px; margin-bottom:18px; position:sticky; top:20px; }
.total-panel small, .pay-hero small { display:block; color:#aeb3bc; }
.total-panel strong { display:block; font-size:34px; margin:8px 0 18px; font-variant-numeric:tabular-nums; white-space:nowrap; }
.total-panel p { display:flex; justify-content:space-between; color:#d5d7dc; font-size:13px; margin:6px 0; }
.ledger-title, .breakdown-title { font-size:12px; color:var(--muted); font-weight:700; text-transform:uppercase; margin:20px 0 8px; }
.ledger-row, .breakdown-row { display:flex; justify-content:space-between; gap:12px; padding:12px 2px; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }
.ledger-row span { color:var(--muted); }
.deduction b { color:#a63b36; }
.pay-hero { padding:30px 0; border-top:1px solid var(--ink); border-bottom:1px solid var(--ink); }
.pay-hero strong { display:block; font-size:44px; margin:8px 0; white-space:nowrap; font-variant-numeric:tabular-nums; }
.pay-hero span { color:var(--muted); font-size:12px; }
.period-line { margin:9px 0 24px; }
.st-key-navigation [role="radiogroup"] { gap:4px; }
.st-key-navigation label { padding:9px 10px!important; border-radius:6px; }
@media (max-width: 700px) {
  .block-container { padding:20px 18px 104px; }
  h1 { font-size:29px!important; }
  .login-wrap h1 { font-size:36px!important; }
  .pay-hero strong, .total-panel strong { font-size:34px; }
  .st-key-desktop_shell [data-testid="stHorizontalBlock"] { display:flex!important; flex-wrap:nowrap!important; }
  .st-key-desktop_shell [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { width:0!important; flex:1 1 0!important; min-width:0!important; }
  .st-key-calendar_head [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) { flex-grow:1.8!important; }
  .st-key-calendar_head .calendar-title { white-space:nowrap; }
  .st-key-desktop_shell > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"],
  .st-key-work_area > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"],
  .st-key-monthly_area > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] { display:block!important; }
  .st-key-desktop_shell > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > div,
  .st-key-work_area > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > div,
  .st-key-monthly_area > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > div { width:100%!important; }
  .st-key-desktop_identity { display:none!important; }
  .st-key-navigation { position:fixed; left:0; right:0; bottom:0; z-index:999; padding:8px 14px calc(8px + env(safe-area-inset-bottom)); background:rgba(255,255,255,.96); border-top:1px solid var(--line); backdrop-filter:blur(16px); }
  .st-key-navigation [role="radiogroup"] { display:grid!important; grid-template-columns:repeat(3,1fr); }
  .st-key-navigation label { justify-content:center; min-height:44px; }
  .st-key-navigation label > div:first-child { display:none; }
  [class*="st-key-cal_"] button { min-height:38px!important; font-size:12px!important; }
  .calendar-title { font-size:16px; }
}
</style>
""", unsafe_allow_html=True)

seed_state()
if "user" not in st.session_state:
    login_view()
    st.stop()

user = st.session_state.user
cfg = st.session_state.preview_configs[user]
with st.container(key="desktop_shell"):
    nav, body = st.columns([0.18, 0.82], gap="large")
    with nav:
        with st.container(key="desktop_identity"):
            st.markdown("<div class='eyebrow'>PAYROLL</div>", unsafe_allow_html=True)
            st.markdown(f"### {user}")
            st.caption("운영과 분리된 테스트 모드")
            if st.button("로그아웃", width="stretch"):
                del st.session_state.user
                st.rerun()
        with st.container(key="navigation"):
            view = st.radio("메뉴", ["기록", "정산", "내 정보"], label_visibility="collapsed", key="main_view")
    with body:
        if view == "기록":
            daily_view(user, cfg)
        elif view == "정산":
            monthly_view(user, cfg)
        else:
            profile_view(user, cfg)
