# Fuel Delivery Pricing

A Python program that validates fuel delivery records, calculates prices, and writes CSV reports.

## Requirements

- Python 3.8 or later (https://www.python.org/downloads/)
- No third-party packages

## Run

Start in the project folder with `shipments.json` and `payments.json` in the current working directory:

```text
python main.py
```

The program asks for four values, one per line, in this order:

1. Custom VAT rate for private clients, entered as a percentage (for example, `25` for 25%).
2. Custom gasoline excise rate per litre (for example, `0.52`).
3. Bonus 1 start date.
4. Bonus 1 end date.

Rates must be numbers greater than or equal to zero. Dates must use `YYYY-MM-DD` or `DD/MM/YYYY`; the end date cannot be before the start date. Invalid answers are requested again. Reports are written to `output/` in the current working directory.

## Implemented parts

- **Task 1:** Standard prices.
- **Task 2:** What-if prices using the entered private-client VAT rate and gasoline excise rate. Exempt clients remain VAT-exempt; the custom excise applies only to gasoline.
- **Bonus 1:** For the inclusive date range, reports the number of valid deliveries, the ID with the highest Task 2 grand total, and the sum of Task 2 VAT. If the range has no deliveries, the row is `0,N/A,0.00`.
- **Bonus 2:** Calculates late-payment interest using Task 1 totals. It uses the first payment with a known delivery ID and valid date. Unpaid deliveries are treated as unpaid on 2024-07-20.
- **Validation report:** Writes rejected records and their error codes to `output/errors.csv`, including when there are no rejected records.

## Input and output details

Each shipment needs an ID, fuel type (`GASOLINE`, `DIESEL`, or `LPG`), client (`PRIVATE` or `EXEMPT`), date, volume, distance, and base price. Fuel type and client values are trimmed and compared without regard to case. Dates are accepted only in the two formats above and must be real calendar dates: `parse_date()` first checks the exact format with a regular expression, then `datetime.strptime()` rejects dates that do not exist (for example `2023-02-30`). The same function is used for shipment dates, payment dates and the Bonus 1 answers.

JSON numeric values are parsed as `Decimal`. Volume must be positive; distance and base price must be non-negative. Duplicate IDs are compared exactly, and only the first occurrence is considered. Each rejected record receives one error code, checked in this order: missing ID, non-text ID, duplicate ID, other missing field, fuel type, client, date, then numeric values.

Every CSV report starts with `Algirdas_Neironis`, followed by its column header and then rows in input order. Rejected deliveries are excluded from price and bonus reports. Money is written with a dot decimal separator and exactly two decimal places.

## Calculation notes

Rates, thresholds, and rate-change dates are defined in `config.py`. The `calculate()` function in `pricing.py` prices a single delivery without reading files or prompting for input. Monetary calculations use `Decimal` and half-up rounding. The discounted net fuel price is rounded only after applying the discount; logistics, excise, and VAT are rounded at their calculation steps before later amounts use them.

For Bonus 2, the 30-day payment term and 2024-07-20 report date are defined in `config.py`. Late days before 2024-07-01 use 12%; days from 2024-07-01 use 9%. When a late period crosses that date, the interest for each rate period is multiplied by the number of days in that period, rounded to two decimals, and then added. Interest for a single day is not rounded before multiplying by the number of days.

## Tests

Run the test suite from the project folder:

```text
python -m unittest
```

## AI usage

Claude Code (Anthropic) was used to write the tests, help test for bugs, and draft this README.
