import unittest
from datetime import date

from payroll_core import (
    daily_total,
    overtime_pay,
    payroll_summary,
    settlement_period,
)


class PayrollCoreTest(unittest.TestCase):
    def test_daily_total_uses_all_seven_employee_prices(self):
        self.assertEqual(
            daily_total(25_000, [1, 2, 0, 1, 0, 3, 1], [9_000, 19_000, 9_000, 13_000, 21_000, 10_000, 20_000], 8_000),
            143_000,
        )

    def test_overtime_is_counted_in_ten_minute_units(self):
        self.assertEqual(overtime_pay("21:35", 4_000, True), 36_000)
        self.assertEqual(overtime_pay("24:00", 3_000, True), 72_000)
        self.assertEqual(overtime_pay("22:00", 4_000, False), 0)

    def test_settlement_period_handles_short_month_and_year_boundary(self):
        self.assertEqual(settlement_period(date(2026, 3, 15), 31), (date(2026, 2, 28), date(2026, 3, 30)))
        self.assertEqual(settlement_period(date(2027, 1, 5), 13), (date(2026, 12, 13), date(2027, 1, 12)))
        self.assertEqual(settlement_period(date(2024, 3, 1), 29), (date(2024, 2, 29), date(2024, 3, 28)))

    def test_payroll_keeps_historical_totals_when_global_prices_are_off(self):
        rows = [
            {"인센티브": 10_000, "시간수당": 4_000, "합계": 100_000, **{f"item{i}": 1 for i in range(1, 8)}},
            {"인센티브": 20_000, "시간수당": 8_000, "합계": 150_000, **{f"item{i}": 2 for i in range(1, 8)}},
        ]
        result = payroll_summary(
            rows,
            {"base_salary": 3_000_000, "insurance": 110_000, "item_prices": [99_000] * 7, "apply_global": False},
            {"Cash": 30_000, "Card": 100_000, "CardDeduct": 25_000, "Etc": 5_000, "EtcAdd": 10_000},
        )
        self.assertEqual(result["performance"], 250_000)
        self.assertEqual(result["card_real"], 75_000)
        self.assertEqual(result["final_pay"], 3_040_000)

    def test_payroll_reprices_every_item_when_global_prices_are_on(self):
        rows = [
            {"인센티브": 10_000, "시간수당": 4_000, "합계": 999_999, **{f"item{i}": i for i in range(1, 8)}},
        ]
        result = payroll_summary(
            rows,
            {"base_salary": 2_500_000, "insurance": 100_000, "item_prices": [1_000, 2_000, 3_000, 4_000, 5_000, 6_000, 7_000], "apply_global": True},
            {"Cash": 0, "Card": 40_000, "CardDeduct": 10_000, "Etc": 5_000, "EtcAdd": 15_000},
        )
        self.assertEqual(result["items"], 140_000)
        self.assertEqual(result["performance"], 154_000)
        self.assertEqual(result["final_pay"], 2_534_000)


if __name__ == "__main__":
    unittest.main()
