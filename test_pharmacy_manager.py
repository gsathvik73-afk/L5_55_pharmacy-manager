"""Behavior and security regression checks for the Lab 5 fixes."""

import contextlib
import copy
import io
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pharmacy_manager as pharmacy


class PharmacyTests(unittest.TestCase):
    """Verify successful operations and preservation of state on failure."""

    def setUp(self):
        pharmacy.medicines.clear()
        self.future = (date.today() + timedelta(days=90)).isoformat()
        self.past = (date.today() - timedelta(days=1)).isoformat()

    def stock(self, name="Medicine", qty=10, expiry=None):
        """Create a valid stock fixture."""
        return pharmacy.add_medicine(name, qty, 1.5, expiry or self.future)

    def test_add_and_restock(self):
        self.stock()
        self.stock(qty=5)
        self.assertEqual(pharmacy.get_quantity("Medicine"), 15)

    def test_audit_defaults_are_independent(self):
        first = self.stock("First")
        second = self.stock("Second")
        self.assertIsNot(first, second)
        self.assertEqual((len(first), len(second)), (1, 1))

    def test_explicit_audit_is_extended(self):
        audit = []
        returned = pharmacy.add_medicine(
            "Medicine", 2, 1.5, self.future, audit
        )
        self.assertIs(returned, audit)
        self.assertEqual(len(audit), 1)

    def test_bad_audit_does_not_change_stock(self):
        with self.assertRaises(ValueError):
            pharmacy.add_medicine("Medicine", 2, audit="invalid")
        self.assertEqual(pharmacy.medicines, {})

    def test_invalid_stock_inputs_are_rejected(self):
        for name, qty, price, expiry in [
            (404, 2, 1.5, self.future),
            (" ", 2, 1.5, self.future),
            ("Medicine", -2, 1.5, self.future),
            ("Medicine", 0, 1.5, self.future),
            ("Medicine", True, 1.5, self.future),
            ("Medicine", 1.5, 1.5, self.future),
            ("Medicine", 2, -1, self.future),
            ("Medicine", 2, float("nan"), self.future),
            ("Medicine", 2, float("inf"), self.future),
            ("Medicine", 2, 10 ** 400, self.future),
            ("Medicine", 2, True, self.future),
            ("Medicine", 2, "1.5", self.future),
            ("Medicine", 2, 1.5, "2026-02-30"),
            ("Medicine", 2, 1.5, "20261021"),
        ]:
            with self.subTest(name=name, qty=qty, expiry=expiry):
                with self.assertRaises(ValueError):
                    pharmacy.add_medicine(name, qty, price, expiry)
                self.assertEqual(pharmacy.medicines, {})

    def test_different_batch_is_not_merged(self):
        self.stock()
        before = copy.deepcopy(pharmacy.medicines)
        with self.assertRaises(ValueError):
            pharmacy.add_medicine("Medicine", 2, 3.0, self.future)
        self.assertEqual(pharmacy.medicines, before)

    def test_dispense_reduces_stock(self):
        self.stock()
        pharmacy.dispense_medicine("Medicine", 3)
        self.assertEqual(pharmacy.get_quantity("Medicine"), 7)

    def test_dispensing_all_removes_empty_stock(self):
        self.stock()
        pharmacy.dispense_medicine("Medicine", 10)
        self.assertNotIn("Medicine", pharmacy.medicines)

    def test_failed_dispense_preserves_stock(self):
        self.stock()
        for qty in [-2, 0, 11, True, 0.5]:
            with self.subTest(qty=qty):
                with self.assertRaises(ValueError):
                    pharmacy.dispense_medicine("Medicine", qty)
                self.assertEqual(pharmacy.get_quantity("Medicine"), 10)

    def test_unknown_medicine_is_reported(self):
        with self.assertRaises(KeyError):
            pharmacy.dispense_medicine("Unknown", 1)

    def test_expired_stock_is_blocked(self):
        self.stock(expiry=self.past)
        self.assertTrue(pharmacy.is_expired("Medicine"))
        with self.assertRaises(ValueError):
            pharmacy.dispense_medicine("Medicine", 1)
        with self.assertRaises(ValueError):
            pharmacy.bill_amount([("Medicine", 1)])
        self.assertEqual(pharmacy.get_quantity("Medicine"), 10)

    def test_expiry_boundary_is_inclusive(self):
        for name, offset in [("Past", -1), ("Today", 0), ("Last", 30),
                             ("Later", 31)]:
            expiry = (date.today() + timedelta(days=offset)).isoformat()
            self.stock(name, expiry=expiry)
        self.assertFalse(pharmacy.is_expired("Today"))
        self.assertEqual(pharmacy.expiring_soon(), ["Today", "Last"])
        self.assertEqual(pharmacy.expiring_soon(0), ["Today"])

    def test_invalid_expiry_window_is_rejected(self):
        for days in [-1, 1.5, True]:
            with self.assertRaises(ValueError):
                pharmacy.expiring_soon(days)

    def test_bill_is_correct_and_does_not_dispense(self):
        self.stock()
        self.assertEqual(pharmacy.bill_amount([("Medicine", 3)]), 4.5)
        self.assertEqual(pharmacy.get_quantity("Medicine"), 10)

    def test_duplicate_bill_lines_cannot_exceed_stock(self):
        self.stock()
        self.assertEqual(
            pharmacy.bill_amount([("Medicine", 4), ("Medicine", 6)]), 15
        )
        with self.assertRaises(ValueError):
            pharmacy.bill_amount([("Medicine", 6), ("Medicine", 6)])
        self.assertEqual(pharmacy.get_quantity("Medicine"), 10)

    def test_arithmetic_supports_original_demo_and_parentheses(self):
        self.assertEqual(pharmacy.calculate_dosage("250 * 2"), 500)
        self.assertEqual(pharmacy.calculate_dosage("(100 + 50) / 2"), 75)
        self.assertEqual(pharmacy.calculate_dosage("+100 - -25"), 125)

    def test_arithmetic_rejects_code_and_invalid_results(self):
        for formula in [
            "__import__('os').getcwd()", "(1).__class__", "name",
            "2 ** 1000000", "[1]", "True", "'250'", "1 / 0",
            "-1", "0", "1e999", "1000000000 * 2", "", " ",
            "1 +", "1" * 201, "+" * 70 + "1", None,
        ]:
            with self.subTest(formula=formula):
                with self.assertRaises(ValueError):
                    pharmacy.calculate_dosage(formula)

    def test_label_treats_shell_syntax_as_literal_text(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "should_not_exist"
            label = f"Medicine; touch {marker}"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                pharmacy.print_label(label)
            self.assertIn(label, output.getvalue())
            self.assertFalse(marker.exists())

    def test_json_round_trip(self):
        self.stock()
        expected = copy.deepcopy(pharmacy.medicines)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stock.json"
            pharmacy.save_stock(path)
            self.assertEqual(json.loads(path.read_text()), expected)
            pharmacy.medicines.clear()
            pharmacy.load_stock(path)
        self.assertEqual(pharmacy.medicines, expected)

    def test_invalid_stock_file_is_atomic(self):
        self.stock()
        before = copy.deepcopy(pharmacy.medicines)
        cases = [
            [], {"Bad": []}, {"Bad": {"qty": 1}},
            {"Bad": {"qty": -1, "price": 1, "expiry": self.future}},
            {"Bad": {"qty": 1, "price": float("nan"),
                     "expiry": self.future}},
            {"Bad": {"qty": 1, "price": 1, "expiry": "bad-date"}},
            {"Valid": {"qty": 1, "price": 1, "expiry": self.future},
             "Invalid": {"qty": -1, "price": 1, "expiry": self.future}},
            {"Same": {"qty": 1, "price": 1, "expiry": self.future},
             " Same ": {"qty": 1, "price": 1, "expiry": self.future}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stock.json"
            for data in cases:
                with self.subTest(data=data):
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        pharmacy.load_stock(path)
                    self.assertEqual(pharmacy.medicines, before)
            path.write_text("not JSON", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                pharmacy.load_stock(path)
            self.assertEqual(pharmacy.medicines, before)

    def test_missing_stock_file_does_not_clear_stock(self):
        self.stock()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                pharmacy.load_stock(Path(folder) / "missing.json")
        self.assertEqual(pharmacy.get_quantity("Medicine"), 10)

    def test_patient_ids_are_unambiguous(self):
        first = pharmacy.patient_id("ab", "c")
        self.assertEqual(len(first), 64)
        self.assertEqual(first, pharmacy.patient_id("ab", "c"))
        self.assertNotEqual(first, pharmacy.patient_id("a", "bc"))

    def test_invalid_patient_fields_are_rejected(self):
        for name, phone in [("", "1"), (1, "2"), ("Name", None)]:
            with self.assertRaises(ValueError):
                pharmacy.patient_id(name, phone)

    def test_prescription_reference_format(self):
        reference = pharmacy.generate_rx_number()
        self.assertIsNotNone(re.fullmatch(r"RX-[0-9A-F]{32}", reference))

    def test_login_denies_missing_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(pharmacy.pharmacist_login("anything"))
            self.assertFalse(pharmacy.pharmacist_login(""))

    def test_login_checks_configured_credential(self):
        credential = secrets.token_urlsafe(24)
        with patch.dict(os.environ, {"PHARMACY_PASSWORD": credential}):
            self.assertTrue(pharmacy.pharmacist_login(credential))
            self.assertFalse(pharmacy.pharmacist_login(credential + "x"))
            self.assertFalse(pharmacy.pharmacist_login(None))

    def test_import_has_no_demo_side_effects(self):
        source = str(Path(pharmacy.__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-c", "import pharmacy_manager"],
                cwd=folder, env={**os.environ, "PYTHONPATH": source},
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(result.stdout + result.stderr, "")
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
