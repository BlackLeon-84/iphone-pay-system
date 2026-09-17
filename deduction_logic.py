def safe_int(value, default=0):
    try:
        text = str(value or "").replace(",", "").replace("원", "").strip()
        return int(text.split(".")[0]) if text else default
    except (TypeError, ValueError):
        return default


def card_detail_total(detail):
    total = 0
    for item in str(detail or "").split("||"):
        parts = item.split("__")
        if len(parts) >= 3 and parts[2] == "O":
            total += safe_int(parts[1])
    return total


def merge_carried_card_detail(target_row, previous_detail):
    result = dict(target_row)
    saved_detail = result.get("CardDetail")
    if saved_detail and not str(result.get("CardDeduct", "")).strip():
        result["CardDeduct"] = card_detail_total(saved_detail)
    if not saved_detail and previous_detail:
        result["CardDetail"] = previous_detail
    return result


def card_list_only_update(current_data, items):
    return {
        "Cash": safe_int(current_data.get("Cash")),
        "Card": safe_int(current_data.get("Card")),
        "CardDeduct": safe_int(current_data.get("CardDeduct")),
        "Etc": safe_int(current_data.get("Etc")),
        "EtcAdd": safe_int(current_data.get("EtcAdd")),
        "EtcAddDesc": current_data.get("EtcAddDesc", ""),
        "CardDetail": "||".join(f"{item['desc']}__{safe_int(item['amt'])}__O" for item in items),
    }


def real_card_deduction(card_total, excluded_total):
    return max(0, safe_int(card_total) - safe_int(excluded_total))
