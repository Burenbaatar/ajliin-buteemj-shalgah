import unittest

from productivity import build_report, calculate_completion, report_text


class CalculateCompletionTests(unittest.TestCase):
    def test_common_values(self):
        self.assertEqual(calculate_completion(10, 8), 80.0)
        self.assertEqual(calculate_completion(10, 0), 0.0)
        self.assertEqual(calculate_completion(10, 10), 100.0)

    def test_invalid_values_raise_value_error(self):
        invalid_pairs = [
            (0, 0),
            (10, 11),
            (10, -1),
            (10.0, 8),
            (10, True),
            ("10", 8),
        ]
        for target, completed in invalid_pairs:
            with self.subTest(target=target, completed=completed):
                with self.assertRaises(ValueError):
                    calculate_completion(target, completed)


class ReportTests(unittest.TestCase):
    def test_build_report_has_expected_fields(self):
        report = build_report(
            {"id": "emp-demo", "name": "Хүслэн", "target": 10, "completed": 8},
            {"total_seconds": 3600, "apps": ["Editor"]},
        )
        self.assertEqual(report["employee_id"], "emp-demo")
        self.assertEqual(report["completion_rate"], 80.0)
        self.assertEqual(report["activity_seconds"], 3600.0)
        self.assertEqual(report["apps"], ["Editor"])
        self.assertIn("date", report)

    def test_report_text_handles_missing_and_negative_duration(self):
        text = report_text({"name": "А" * 500, "activity_seconds": -60})
        self.assertIn("Тооцоолоогүй", text)
        self.assertIn("0.0 секунд", text)
        self.assertIn("0.0 минут", text)


if __name__ == "__main__":
    unittest.main()
