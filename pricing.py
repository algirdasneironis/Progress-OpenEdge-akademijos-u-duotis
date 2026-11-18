import re
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, getcontext

import config

getcontext().prec = 1000

REQUIRED_FIELDS = ["id", "type", "client", "date", "volume", "distance", "basePrice"]
DATE_FORMATS = [
    (re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}"), "%Y-%m-%d"),
    (re.compile(r"[0-9]{2}/[0-9]{2}/[0-9]{4}"), "%d/%m/%Y"),
]


def round_money(value):
    return abs(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(text):
    for pattern, date_format in DATE_FORMATS:
        if isinstance(text, str) and pattern.fullmatch(text):
            try:
                return datetime.strptime(text, date_format).date()
            except ValueError:
                return None
    return None


def normalise(value):
    if isinstance(value, str) and value.strip().isascii():
        return value.strip().upper()
    return None


def is_number(value):
    return isinstance(value, Decimal) and value.is_finite()


def error_code(record, seen_ids):
    shipment_id = record.get("id") if isinstance(record, dict) else None
    if shipment_id is None:
        return "MISSING_FIELD"
    if not isinstance(shipment_id, str):
        return "INVALID_VALUE"
    if shipment_id in seen_ids:
        return "DUPLICATE_ID"
    seen_ids.add(shipment_id)

    if any(record.get(field) is None for field in REQUIRED_FIELDS):
        return "MISSING_FIELD"
    if normalise(record["type"]) not in config.EXCISE_PER_LITRE:
        return "UNKNOWN_TYPE"
    if normalise(record["client"]) not in config.CLIENTS:
        return "UNKNOWN_CLIENT"
    if parse_date(record["date"]) is None:
        return "INVALID_DATE"

    volume, distance, price = record["volume"], record["distance"], record["basePrice"]
    if not (is_number(volume) and volume > 0):
        return "INVALID_VALUE"
    if not (is_number(distance) and distance >= 0 and is_number(price) and price >= 0):
        return "INVALID_VALUE"
    return None


def validate(records):
    seen_ids, shipments, errors = set(), [], []
    for record in records:
        code = error_code(record, seen_ids)
        if code:
            shipment_id = record.get("id") if isinstance(record, dict) else None
            errors.append(("" if shipment_id is None else str(shipment_id), code))
        else:
            shipments.append({
                "id": record["id"],
                "type": normalise(record["type"]),
                "client": normalise(record["client"]),
                "date": parse_date(record["date"]),
                "volume": record["volume"],
                "distance": record["distance"],
                "price": record["basePrice"],
            })
    return shipments, errors


def calculate(shipment, private_vat=None, gasoline_excise=None):
    volume = shipment["volume"]

    discount = Decimal("0")
    for over_litres, rate in config.VOLUME_DISCOUNTS:
        if volume > over_litres:
            discount = rate
            break
    net = round_money(volume * shipment["price"] * (1 - discount))

    logistics = round_money(shipment["distance"] * config.DELIVERY_PRICE_PER_KM)
    if volume < config.SMALL_LOAD_LIMIT:
        logistics += config.SMALL_LOAD_FEE

    excise_rate = config.EXCISE_PER_LITRE[shipment["type"]]
    if gasoline_excise is not None and shipment["type"] == "GASOLINE":
        excise_rate = gasoline_excise
    excise = round_money(volume * excise_rate)

    if shipment["client"] == "EXEMPT":
        vat_rate = config.VAT_EXEMPT
    elif private_vat is not None:
        vat_rate = private_vat
    elif shipment["date"] < config.VAT_CHANGE_DATE:
        vat_rate = config.VAT_BEFORE_CHANGE
    else:
        vat_rate = config.VAT_FROM_CHANGE
    vat = round_money((net + logistics + excise) * vat_rate)

    total_tax = excise + vat
    return {
        "net": net,
        "logistics": logistics,
        "vat": vat,
        "total_tax": total_tax,
        "grand_total": net + logistics + total_tax,
    }


def paid_dates(payments, shipment_ids):
    result = {}
    for payment in payments:
        if not isinstance(payment, dict):
            continue
        shipment_id = payment.get("id")
        if isinstance(shipment_id, str) and shipment_id in shipment_ids and shipment_id not in result:
            paid = parse_date(payment.get("paidDate"))
            if paid:
                result[shipment_id] = paid
    return result


def late_interest(grand_total, delivery_date, paid_date):
    due_date = delivery_date + timedelta(days=config.PAYMENT_DAYS)
    last_day = paid_date or config.REPORT_DATE
    days_late = max(0, (last_day - due_date).days)

    days_before_change = (config.INTEREST_CHANGE_DATE - due_date).days - 1
    days_before_change = min(days_late, max(0, days_before_change))
    days_from_change = days_late - days_before_change

    interest = (
        round_money(grand_total * config.INTEREST_BEFORE_CHANGE * days_before_change / config.DAYS_IN_YEAR)
        + round_money(grand_total * config.INTEREST_FROM_CHANGE * days_from_change / config.DAYS_IN_YEAR)
    )
    return due_date, days_late, interest
