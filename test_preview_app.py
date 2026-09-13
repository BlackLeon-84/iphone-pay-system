import unittest
from datetime import date

import pandas  # Streamlit AppTest imports these safely when preloaded.
import pyarrow
from streamlit.testing.v1 import AppTest


STAFF = ["태완", "남근", "성훈", "대원", "성욱", "테스트"]


def signed_in_app(user):
    app = AppTest.from_file("preview_app.py", default_timeout=20)
    app.session_state["user"] = user
    app.session_state["selected_day"] = date.today()
    app.session_state["calendar_month"] = date.today().replace(day=1)
    return app.run()


class PreviewAppTest(unittest.TestCase):
    def test_every_employee_can_open_every_view_with_their_own_controls(self):
        for user in STAFF:
            with self.subTest(user=user):
                app = signed_in_app(user)
                self.assertEqual([], list(app.exception))
                self.assertEqual(user in {"태완", "남근"}, "퇴근 시간" in [item.label for item in app.selectbox])
                app.radio(key="main_view").set_value("정산").run()
                self.assertEqual([], list(app.exception))
                self.assertIn("정산 월", [item.label for item in app.selectbox])
                app.radio(key="main_view").set_value("내 정보").run()
                self.assertEqual([], list(app.exception))

    def test_off_day_then_normal_save_does_not_leave_the_entry_broken(self):
        user = "테스트"
        day = date.today().isoformat()
        app = signed_in_app(user)
        app.button(key=f"off_{user}_{day}").click().run()
        self.assertEqual("휴무", app.session_state["preview_records"][user][day]["비고"])
        app.number_input(key=f"pending_{user}_{day}").set_value(10_000)
        app.button(key=f"save_{user}_{day}").click().run()
        row = app.session_state["preview_records"][user][day]
        self.assertEqual([], list(app.exception))
        self.assertEqual(10_000, row["인센티브"])
        self.assertEqual(10_000, row["합계"])


if __name__ == "__main__":
    unittest.main()
