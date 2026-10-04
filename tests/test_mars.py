"""Check the challenge requirements and the script's documented behavior."""

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "lcm_mars.sh"
LOG = ROOT / "space_missions.log"


def row(days, code="TST-123-ROW", destination="Mars", status="Completed"):
    return f"2045-07-12 | ID-1234 | {destination} | {status} | 5 | {days} | 98.7 | {code}\n"


class MissionTests(unittest.TestCase):
    def run_script(self, path=None, cwd=None):
        command = ["sh", str(SCRIPT)]
        if path is not None:
            command.append(str(path))
        return subprocess.run(command, cwd=cwd, capture_output=True, timeout=10, check=False)

    def check_output(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout, (expected + "\n").encode())
        self.assertEqual(result.stderr, b"")

    def check_fixture(self, content, expected, filename="input.log", default=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / filename
            path.write_bytes(content.encode())
            result = self.run_script(None if default else filename, cwd=directory)
        self.check_output(result, expected)

    def test_supplied_log(self):
        self.check_output(self.run_script(LOG), "XRT-421-ZQP")

    def test_new_winner_at_end_of_supplied_log(self):
        content = LOG.read_text() + "\n" + row(10000, "NEW-123-MAX")
        self.check_fixture(content, "NEW-123-MAX")

    def test_numeric_maximum_is_independent_of_order(self):
        records = [row(9), row(100, "MAX-123-ROW"), row(80)]
        for order in (records, records[::-1]):
            with self.subTest(order=order):
                self.check_fixture("".join(order), "MAX-123-ROW")

    def test_exact_destination_and_status(self):
        content = (
            row(9999, destination="Marsville")
            + row(9999, status="Not Completed")
            + row(9999, destination="Venus").replace("ID-1234", "Mars-ID")
            + row(9999, status="Failed").replace("ID-1234", "Completed-ID")
            + row(10, "YES-123-MAR")
        )
        self.check_fixture(content, "YES-123-MAR")

    def test_comments_blank_lines_and_noise(self):
        content = "\nSYSTEM: Mars Completed\n# " + row(9999)
        content += "  \t# " + row(9999) + row(10, "YES-123-MAR")
        self.check_fixture(content, "YES-123-MAR")

    def test_spacing_tabs_and_crlf(self):
        for separator in ("|", "  | ", "\t|\t"):
            with self.subTest(separator=separator):
                content = row(15).replace(" | ", separator).replace("\n", "\r\n")
                self.check_fixture(content, "TST-123-ROW")

    def test_zero_day_mission(self):
        self.check_fixture(row(0, "ZER-000-DAY"), "ZER-000-DAY")

    def test_first_maximum_wins_a_tie(self):
        self.check_fixture(row(100, "ONE-123-MAX") + row(100, "TWO-123-MAX"), "ONE-123-MAX")

    def test_no_match_prints_blank_line(self):
        for content in ("", "# Mars Completed\n", row(100, destination="Venus")):
            with self.subTest(content=content):
                self.check_fixture(content, "")

    def test_default_and_unusual_filenames(self):
        self.check_fixture(row(10), "TST-123-ROW", "space_missions.log", default=True)
        for filename in ("file with spaces.log", "-input.log", "name=value.log"):
            with self.subTest(filename=filename):
                self.check_fixture(row(10), "TST-123-ROW", filename)

    def test_missing_input_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_script("missing.log", cwd=directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main()
