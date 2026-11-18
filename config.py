from datetime import date
from decimal import Decimal

AUTHOR_NAME = "Algirdas_Neironis"

SHIPMENTS_FILE = "shipments.json"
PAYMENTS_FILE = "payments.json"
OUTPUT_DIR = "output"

CLIENTS = ("PRIVATE", "EXEMPT")
EXCISE_PER_LITRE = {
    "GASOLINE": Decimal("0.47"),
    "DIESEL": Decimal("0.33"),
    "LPG": Decimal("0.18"),
}

VOLUME_DISCOUNTS = [
    (Decimal("20000"), Decimal("0.10")),
    (Decimal("5000"), Decimal("0.05")),
]
DELIVERY_PRICE_PER_KM = Decimal("1.80")
SMALL_LOAD_LIMIT = Decimal("1000")
SMALL_LOAD_FEE = Decimal("150.00")

VAT_EXEMPT = Decimal("0")
VAT_BEFORE_CHANGE = Decimal("0.21")
VAT_FROM_CHANGE = Decimal("0.23")
VAT_CHANGE_DATE = date(2024, 1, 1)

PAYMENT_DAYS = 30
REPORT_DATE = date(2024, 7, 20)
INTEREST_BEFORE_CHANGE = Decimal("0.12")
INTEREST_FROM_CHANGE = Decimal("0.09")
INTEREST_CHANGE_DATE = date(2024, 7, 1)
DAYS_IN_YEAR = 365
