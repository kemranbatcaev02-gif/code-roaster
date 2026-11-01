import unittest
from pathlib import Path
import sys

# Добавляем родительскую папку в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roaster import (
    PERSONALITIES,
    scan_file,
    calculate_flame_score,
    get_verdict,
    RoastIssue,
)


class TestCodeRoaster(unittest.TestCase):
    def setUp(self):
        self.sample_file = Path(__file__).resolve().parent / "sample_bad_code.py"
        self.senior = PERSONALITIES["senior"]

    def test_personalities_structure(self):
        for key in ["senior", "ramsay", "cyber", "teamlead", "junior"]:
            self.assertIn(key, PERSONALITIES)
            p = PERSONALITIES[key]
            self.assertIn("name", p)
            self.assertIn("avatar", p)
            self.assertIn("flame_comments", p)

    def test_to_dict(self):
        issue = RoastIssue("f.py", 10, "x = 1", "Нейминг", 3, "Плохо")
        d = issue.to_dict()
        self.assertEqual(d["file_path"], "f.py")
        self.assertEqual(d["line_number"], 10)
        self.assertEqual(d["severity"], 3)

    def test_scan_bad_code(self):
        issues = scan_file(self.sample_file, self.senior)
        self.assertTrue(len(issues) >= 4)
        rule_names = {i.rule_name for i in issues}
        self.assertTrue(any("Нейминг" in r for r in rule_names))
        self.assertTrue(any("Отладочный" in r for r in rule_names))
        self.assertTrue(any("TODO" in r for r in rule_names))

    def test_flame_score_calculation(self):
        dummy_issues = [
            RoastIssue("f.py", 1, "temp = 1", "Нейминг", 3, "bad"),
            RoastIssue("f.py", 2, "print(1)", "Дебаг", 3, "bad"),
        ]
        score = calculate_flame_score(dummy_issues, total_files=1)
        self.assertTrue(0 <= score <= 100)

        score_empty = calculate_flame_score([], total_files=1)
        self.assertEqual(score_empty, 0)

    def test_verdict(self):
        v_title, _ = get_verdict(0)
        self.assertIn("СВЯТОЙ", v_title)

        v_chernobyl, _ = get_verdict(90)
        self.assertIn("ЧЕРНОБЫЛЬ", v_chernobyl)


if __name__ == "__main__":
    unittest.main()
