import unittest

from deduction_logic import card_list_only_update, merge_carried_card_detail, real_card_deduction


class DeductionLogicTest(unittest.TestCase):
    def test_carried_list_does_not_become_this_month_deduction(self):
        result = merge_carried_card_detail({}, "카톡__2500__O||바디프렌드__37500__O||전부가세__75000__O||네이버플러스__4900__O||캡컷__10000__O")

        self.assertEqual(0, result.get("CardDeduct", 0))
        self.assertIn("카톡__2500__O", result["CardDetail"])

    def test_editing_list_preserves_committed_deduction_until_full_save(self):
        current = {"Cash": "10,000", "Card": "200,000", "CardDeduct": "25,000", "Etc": "3,000", "EtcAdd": "5,000", "EtcAddDesc": "교통비"}
        result = card_list_only_update(current, [{"desc": "업무용", "amt": 70_000}])

        self.assertEqual(25_000, result["CardDeduct"])
        self.assertEqual("업무용__70000__O", result["CardDetail"])

    def test_legacy_saved_detail_backfills_missing_deduction(self):
        result = merge_carried_card_detail({"CardDetail": "업무용__12000__O", "CardDeduct": ""}, "이월__99000__O")

        self.assertEqual(12_000, result["CardDeduct"])

    def test_exclusion_cannot_turn_into_extra_pay(self):
        self.assertEqual(0, real_card_deduction(0, 129_900))
        self.assertEqual(70_000, real_card_deduction(100_000, 30_000))


if __name__ == "__main__":
    unittest.main()
