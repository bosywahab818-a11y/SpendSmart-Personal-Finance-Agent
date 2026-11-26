import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import spendsmart_agent as spend


class FinanceToolTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / "transactions.csv"
        self.csv_path.write_text(
            "transaction_id,date,merchant,amount,description,transaction_type,currency\n"
            "1,2026-11-01,Employer,6000,Monthly salary,income,EGP\n"
            "2,2026-11-02,Supermarket,500,Groceries,expense,EGP\n"
            "3,2026-11-03,Metro,100,Transport,expense,EGP\n"
            "4,2026-11-03 23:45:00,Taxi,50,Late transport,expense,EGP\n",
            encoding="utf-8",
        )

    def test_metrics_use_selected_period_and_currency(self):
        with patch.object(spend, "TRANSACTIONS_PATH", self.csv_path):
            result = json.loads(
                spend.calculate_financial_metrics("2026-11-01", "2026-11-30")
            )
        self.assertEqual(result["transaction_income_total"], 6000.0)
        self.assertEqual(result["total_expenses"], 650.0)
        self.assertEqual(result["remaining_balance"], 5400.0)
        self.assertEqual(result["currency"], ["EGP"])

    def test_metrics_exclude_records_outside_period(self):
        with patch.object(spend, "TRANSACTIONS_PATH", self.csv_path):
            result = json.loads(
                spend.calculate_financial_metrics("2026-11-02", "2026-11-03")
            )
        self.assertEqual(result["transaction_income_total"], 0.0)
        self.assertEqual(result["total_expenses"], 650.0)

    def test_reverse_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            spend._period("2026-11-30", "2026-11-01")

    def test_invalid_transaction_type_returns_error(self):
        with patch.object(spend, "TRANSACTIONS_PATH", self.csv_path):
            result = json.loads(
                spend.retrieve_transactions(
                    "2026-11-01", "2026-11-30", "refund"
                )
            )
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
