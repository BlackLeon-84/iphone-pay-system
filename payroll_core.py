import calendar
from datetime import date, timedelta


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").replace("원", "").strip()
        return int(text.split(".")[0]) if text else default
    except (TypeError, ValueError):
        return default


def safe_date(year, month, day):
    return date(year, month, min(max(safe_int(day, 1), 1), calendar.monthrange(year, month)[1]))


def _shift_month(year, month, offset):
    value = year * 12 + month - 1 + offset
    return value // 12, value % 12 + 1


def settlement_period(target, start_day):
    current_start = safe_date(target.year, target.month, start_day)
    if target >= current_start:
        start = current_start
        next_year, next_month = _shift_month(target.year, target.month, 1)
        end = safe_date(next_year, next_month, start_day) - timedelta(days=1)
    else:
        prev_year, prev_month = _shift_month(target.year, target.month, -1)
        start = safe_date(prev_year, prev_month, start_day)
        end = current_start - timedelta(days=1)
    return start, end


def overtime_pay(end_time, rate, eligible):
    if not eligible:
        return 0
    hours, minutes = (24, 0) if end_time == "24:00" else map(int, end_time.split(":"))
    overtime_minutes = max(0, hours * 60 + minutes - 20 * 60)
    return overtime_minutes // 10 * safe_int(rate)


def daily_total(incentive, counts, prices, overtime=0):
    if len(counts) != 7 or len(prices) != 7:
        raise ValueError("품목 수량과 단가는 각각 7개여야 합니다.")
    return safe_int(incentive) + safe_int(overtime) + sum(safe_int(count) * safe_int(price) for count, price in zip(counts, prices))


def payroll_summary(rows, config, deductions):
    incentive = sum(safe_int(row.get("인센티브")) for row in rows)
    overtime = sum(safe_int(row.get("시간수당")) for row in rows)
    if config.get("apply_global"):
        items = sum(
            safe_int(row.get(f"item{i + 1}")) * safe_int(config["item_prices"][i])
            for row in rows
            for i in range(7)
        )
        performance = incentive + overtime + items
    else:
        performance = sum(safe_int(row.get("합계")) for row in rows)
        items = performance - incentive - overtime

    cash = safe_int(deductions.get("Cash"))
    card = safe_int(deductions.get("Card"))
    card_excluded = safe_int(deductions.get("CardDeduct"))
    etc = safe_int(deductions.get("Etc"))
    extra = safe_int(deductions.get("EtcAdd"))
    card_real = card - card_excluded
    final_pay = safe_int(config.get("base_salary")) + performance - safe_int(config.get("insurance")) - cash - card_real - etc + extra

    return {
        "incentive": incentive,
        "overtime": overtime,
        "items": items,
        "performance": performance,
        "cash": cash,
        "card": card,
        "card_excluded": card_excluded,
        "card_real": card_real,
        "etc": etc,
        "extra": extra,
        "final_pay": final_pay,
    }
