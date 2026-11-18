import unittest
from datetime import date
from decimal import Decimal as D

from pricing import calculate, late_interest, paid_dates, parse_date, round_money, validate


def shipment(type="LPG", client="PRIVATE", day=date(2024, 7, 4), volume="12000", distance="90", price="0.51"):
    return {"id": "a", "type": type, "client": client, "date": day,
            "volume": D(volume), "distance": D(distance), "price": D(price)}


def record(**changes):
    r = {"id": "a", "type": "DIESEL", "client": "PRIVATE", "date": "2024-01-01",
         "volume": D("100"), "distance": D("10"), "basePrice": D("1")}
    r.update(changes)
    return r


def codes(records):
    return validate(records)[1]


class CalculateTest(unittest.TestCase):
    def test_rounding_half_up(self):
        self.assertEqual(round_money(D("0.125")), D("0.13"))
        self.assertEqual(round_money(D("2.675")), D("2.68"))

    def test_pdf_example_task1(self):
        p = calculate(shipment())
        self.assertEqual((p["net"], p["logistics"], p["vat"], p["total_tax"], p["grand_total"]),
                         (D("5814.00"), D("162.00"), D("1871.28"), D("4031.28"), D("10007.28")))

    def test_pdf_example_task2(self):
        p = calculate(shipment(), D("0.25"), D("0.52"))
        self.assertEqual((p["total_tax"], p["grand_total"]), (D("4194.00"), D("10170.00")))

    def test_discount_rounded_only_at_the_end(self):
        self.assertEqual(calculate(shipment("GASOLINE", volume="6200", price="0.8775"))["net"], D("5168.48"))

    def test_discount_limits(self):
        nets = [calculate(shipment(volume=v, price="1"))["net"] for v in ["5000", "5001", "20000", "20001"]]
        self.assertEqual(nets, [D("5000.00"), D("4750.95"), D("19000.00"), D("18000.90")])

    def test_small_load_fee(self):
        self.assertEqual(calculate(shipment(volume="999", distance="10"))["logistics"], D("168.00"))
        self.assertEqual(calculate(shipment(volume="1000", distance="10"))["logistics"], D("18.00"))

    def test_vat_rates(self):
        old = shipment("DIESEL", day=date(2023, 12, 31), volume="5000", price="0.91")
        new = shipment("DIESEL", day=date(2024, 1, 1), volume="5000", price="0.91")
        self.assertEqual(calculate(old)["grand_total"], D("7698.02"))
        self.assertEqual(calculate(new)["vat"], D("1463.26"))
        self.assertEqual(calculate(shipment(client="EXEMPT"), D("0.25"))["vat"], D("0.00"))

    def test_custom_excise_only_for_gasoline(self):
        diesel = shipment("DIESEL", volume="1000", distance="0", price="0")
        gasoline = shipment("GASOLINE", volume="1000", distance="0", price="0")
        self.assertEqual(calculate(diesel, None, D("1"))["total_tax"], D("405.90"))
        self.assertEqual(calculate(gasoline, None, D("1"))["total_tax"], D("1230.00"))

    def test_huge_numbers(self):
        self.assertEqual(calculate(shipment(volume="1e120", price="1"))["net"], D("9E+119"))


class ValidateTest(unittest.TestCase):
    def test_valid_record_is_normalised(self):
        shipments, errors = validate([record(type="  diesel ", client=" Exempt")])
        self.assertEqual(errors, [])
        self.assertEqual((shipments[0]["type"], shipments[0]["client"]), ("DIESEL", "EXEMPT"))

    def test_error_codes(self):
        records = [
            record(id="1", basePrice=None),
            record(id="2", type="KEROSENE"),
            record(id="3", client="GOVERNMENT"),
            record(id="4", date="2023-02-30"),
            record(id="5", volume=D("0")),
            record(id="6", volume="1500"),
            record(id="7", distance=D("-1")),
            record(id="8", basePrice=True),
            record(id="9", volume=D("NaN")),
            record(id="10", type="d\u0131esel"),
        ]
        del records[0]["basePrice"]
        self.assertEqual(codes(records), [
            ("1", "MISSING_FIELD"), ("2", "UNKNOWN_TYPE"), ("3", "UNKNOWN_CLIENT"), ("4", "INVALID_DATE"),
            ("5", "INVALID_VALUE"), ("6", "INVALID_VALUE"), ("7", "INVALID_VALUE"), ("8", "INVALID_VALUE"),
            ("9", "INVALID_VALUE"), ("10", "UNKNOWN_TYPE"),
        ])

    def test_missing_id_and_not_an_object(self):
        self.assertEqual(codes([record(id=None), None]), [("", "MISSING_FIELD"), ("", "MISSING_FIELD")])

    def test_duplicates(self):
        records = [record(type="X"), record(), record(id="A")]
        self.assertEqual(codes(records), [("a", "UNKNOWN_TYPE"), ("a", "DUPLICATE_ID")])

    def test_zero_distance_and_price_are_valid(self):
        self.assertEqual(codes([record(distance=D("0"), basePrice=D("0"))]), [])


class DateTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_date("2024-02-29"), date(2024, 2, 29))
        self.assertEqual(parse_date("29/02/2024"), date(2024, 2, 29))

    def test_invalid(self):
        for text in ["2023-02-30", "29/02/2023", "2024-1-5", "1/1/2024", "2024/01/01", " 2024-01-01",
                     "", "0000-01-01", "\u0661\u0662\u0663\u0664-01-01", None, 20240101]:
            self.assertIsNone(parse_date(text), text)


class LateInterestTest(unittest.TestCase):
    def test_pdf_example(self):
        self.assertEqual(late_interest(D("7698.02"), date(2023, 12, 31), date(2024, 2, 14)),
                         (date(2024, 1, 30), 15, D("37.96")))

    def test_on_time(self):
        self.assertEqual(late_interest(D("100"), date(2024, 1, 1), date(2024, 1, 31))[1:], (0, D("0.00")))

    def test_unpaid_and_rate_split(self):
        self.assertEqual(late_interest(D("10000"), date(2024, 6, 1), None)[1:], (19, D("46.85")))
        self.assertEqual(late_interest(D("36500"), date(2024, 5, 29), date(2024, 7, 5))[1:], (7, D("69.00")))

    def test_first_usable_payment(self):
        payments = [{"id": "x", "paidDate": "2024-01-01"}, {"id": "a", "paidDate": "2024-02-30"},
                    {"id": "a", "paidDate": "05/03/2024"}, {"id": "a", "paidDate": "2024-01-01"}, None]
        self.assertEqual(paid_dates(payments, {"a"}), {"a": date(2024, 3, 5)})


if __name__ == "__main__":
    unittest.main()
