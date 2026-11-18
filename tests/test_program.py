import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


class ProgramTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        shutil.copy(PROJECT / "shipments.json", self.folder)
        shutil.copy(PROJECT / "payments.json", self.folder)

    def run_program(self, answers):
        result = subprocess.run([sys.executable, str(PROJECT / "main.py")], cwd=self.folder,
                                input=answers, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def lines(self, name):
        return (self.folder / "output" / name).read_text(encoding="utf-8").splitlines()

    def test_sample_data(self):
        self.run_program("25\n0.52\n2024-01-01\n2024-01-31\n")
        self.assertEqual(self.lines("task1.csv")[:2],
                         ["Algirdas_Neironis", "ShipmentID,NetFuelPrice,LogisticsCost,TotalTax,GrandTotal"])
        self.assertIn("4fc31099-170f-45f8-80b4-45b3367ea45d,5814.00,162.00,4031.28,10007.28", self.lines("task1.csv"))
        self.assertIn("4fc31099-170f-45f8-80b4-45b3367ea45d,5814.00,162.00,4194.00,10170.00", self.lines("task2.csv"))
        self.assertIn("480100d2-4d5d-460e-ab5a-cb3e54bb484a,2024-01-30,15,37.96", self.lines("bonus2.csv"))
        self.assertEqual(self.lines("bonus1.csv")[2], "4,c47c3701-232f-410f-a281-5e5798c5c979,2934.93")
        self.assertEqual(self.lines("errors.csv")[2:], [
            "3e8b6f52-1c47-4a9d-8e25-7b0d4c9a1f63,UNKNOWN_TYPE",
            "b612de70-6792-418b-85e3-07da86c8a233,INVALID_VALUE",
            "a41d9c07-5e82-4b36-9f1a-2d8c6e0b7f45,INVALID_DATE",
            "6f2a8d13-9b50-4c74-a3e8-1c5d7b9e0a24,MISSING_FIELD",
            "d09e3b78-4a16-4f52-b8c7-0e1a5d3f9c86,UNKNOWN_CLIENT",
            "35d5cf85-fcec-4658-87e8-53f26826359e,DUPLICATE_ID",
        ])

    def test_bad_answers_are_asked_again(self):
        output = self.run_program("abc\n-5\n25\n\n0,52\n0.52\n2024-02-30\n31/01/2024\n2024-01-01\n2024-01-31\n")
        self.assertEqual(output.count("Error:"), 6)
        self.assertEqual(self.lines("bonus1.csv")[2], "2,08541693-d9ce-444a-a4c2-269afded9f2a,1115.95")

    def test_utf16_and_bom_files(self):
        text = (PROJECT / "shipments.json").read_text(encoding="utf-8")
        (self.folder / "shipments.json").write_text(text, encoding="utf-16")
        (self.folder / "payments.json").write_text((PROJECT / "payments.json").read_text(encoding="utf-8"), encoding="utf-8-sig")
        self.run_program("25\n0.52\n2024-01-01\n2024-01-31\n")
        self.assertIn("480100d2-4d5d-460e-ab5a-cb3e54bb484a,2024-01-30,15,37.96", self.lines("bonus2.csv"))

    def test_equal_grand_total_first_in_file_wins(self):
        record = '{"id": "%s", "type": "LPG", "client": "PRIVATE", "date": "%s", "volume": 100, "distance": 1, "basePrice": 1}'
        records = [record % ("cheap", "2024-01-01"), record % ("first", "2024-01-31"), record % ("second", "2024-01-02")]
        records[0] = records[0].replace('"volume": 100', '"volume": 50')
        (self.folder / "shipments.json").write_text("[" + ",".join(records) + "]", encoding="utf-8")
        self.run_program("25\n0.52\n2024-01-01\n2024-01-31\n")
        self.assertEqual(self.lines("bonus1.csv")[2].split(",")[:2], ["3", "first"])

    def test_empty_file(self):
        (self.folder / "shipments.json").write_text("[]", encoding="utf-8")
        self.run_program("25\n0.52\n2024-01-01\n2024-01-31\n")
        self.assertEqual(self.lines("errors.csv"), ["Algirdas_Neironis", "ShipmentID,ErrorCode"])
        self.assertEqual(self.lines("bonus1.csv")[2], "0,N/A,0.00")


if __name__ == "__main__":
    unittest.main()
