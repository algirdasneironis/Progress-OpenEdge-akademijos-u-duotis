import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import config
from pricing import calculate, late_interest, paid_dates, parse_date, validate

PRICE_HEADER = ["ShipmentID", "NetFuelPrice", "LogisticsCost", "TotalTax", "GrandTotal"]


def read_json(name):
    data = Path(name).read_bytes()
    return json.loads(data, parse_float=Decimal, parse_int=Decimal, parse_constant=Decimal)


def read_payments():
    try:
        payments = read_json(config.PAYMENTS_FILE)
    except (OSError, ValueError):
        return []
    return payments if isinstance(payments, list) else []


def write_csv(name, header, rows):
    output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / name, "w", encoding="utf-8", newline="") as file:
        file.write(config.AUTHOR_NAME + "\n")
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def money(value):
    return format(value, "f")


def price_rows(shipments, prices):
    return [
        (s["id"], money(p["net"]), money(p["logistics"]), money(p["total_tax"]), money(p["grand_total"]))
        for s, p in zip(shipments, prices)
    ]


def ask(prompt, parse):
    while True:
        print(prompt, end="", flush=True)
        line = sys.stdin.readline()
        if not line:
            sys.exit("\nError: input ended before all questions were answered.")
        value = parse(line.replace("\ufeff", "").strip())
        if value is not None:
            return value
        print("Error: invalid value, please try again.")


def parse_number(text):
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if value.is_finite() and value >= 0:
        return value
    return None


def main():
    shipments, errors = validate(read_json(config.SHIPMENTS_FILE))
    write_csv("errors.csv", ["ShipmentID", "ErrorCode"], errors)

    prices = [calculate(s) for s in shipments]
    write_csv("task1.csv", PRICE_HEADER, price_rows(shipments, prices))

    paid = paid_dates(read_payments(), {s["id"] for s in shipments})
    bonus2 = []
    for s, p in zip(shipments, prices):
        due_date, days_late, interest = late_interest(p["grand_total"], s["date"], paid.get(s["id"]))
        bonus2.append((s["id"], due_date.isoformat(), days_late, money(interest)))
    write_csv("bonus2.csv", ["ShipmentID", "DueDate", "DaysLate", "LateInterest"], bonus2)

    vat = ask("Enter custom VAT rate for Private clients (%): ", parse_number) / 100
    excise = ask("Enter custom Excise rate for Gasoline: ", parse_number)
    prices = [calculate(s, vat, excise) for s in shipments]
    write_csv("task2.csv", PRICE_HEADER, price_rows(shipments, prices))

    start = ask("Enter Start Date (YYYY-MM-DD or DD/MM/YYYY): ", parse_date)

    def parse_end_date(text):
        end = parse_date(text)
        return end if end and end >= start else None

    end = ask("Enter End Date (YYYY-MM-DD or DD/MM/YYYY): ", parse_end_date)
    in_range = [(s, p) for s, p in zip(shipments, prices) if start <= s["date"] <= end]
    if in_range:
        most_expensive = max(in_range, key=lambda item: item[1]["grand_total"])[0]["id"]
        row = (len(in_range), most_expensive, money(sum(p["vat"] for s, p in in_range)))
    else:
        row = (0, "N/A", "0.00")
    write_csv("bonus1.csv", ["ShipmentCount", "MostExpensiveID", "TotalVAT"], [row])


if __name__ == "__main__":
    main()
