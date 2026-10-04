"""Header, malformed-record, and typo handling for the hardened script."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_mars as shared
from test_mars import HARDENED, HEADER, LOG, row


@unittest.skipUnless(HARDENED, "hardened behavior only")
class HardenedTests(unittest.TestCase):
    # Share the execution/assertion helpers without inheriting the core tests twice.
    run_script = shared.MissionTests.run_script
    fixture_result = shared.MissionTests.fixture_result
    check_output = shared.MissionTests.check_output
    check_error = shared.MissionTests.check_error

    def check_case(self, content, expected="XRT-421-ZQP", status=0, warning=None):
        result = self.fixture_result(content, header=False)
        if status:
            self.check_error(result, status, warning)
        elif warning:
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stdout, (expected + "\n").encode())
            self.assertIn(warning, result.stderr.decode())
        else:
            self.check_output(result, expected)

    def test_attached_22_cases(self):
        original = LOG.read_text()

        def reordered(order):
            for line in original.splitlines(keepends=True):
                is_header = line.startswith("# Format:")
                fields = (line.split(":", 1)[1] if is_header else line).strip().split("|")
                if len(fields) == 8 and (is_header or not line.lstrip().startswith("#")):
                    prefix = "# Format: " if is_header else ""
                    yield prefix + "|".join(fields[i] for i in order) + "\n"
                else:
                    yield line

        additions = [
            ("CMT", "# " + row(9999)),
            ("ICMT", "  \t# " + row(9999)),
            ("MRX", row(9999, destination="Marsville")),
            ("NCP", row(9999, status="Not Completed")),
            ("MID", row(9999, destination="Moon").replace("ID-1234", "Mars-ID")),
            ("DUR", row("9994d")),
            ("NF9", row(9999).rstrip() + " | extra\n"),
        ]
        for name, addition in additions:
            with self.subTest(case=name):
                self.check_case(original + "\n" + addition)
        with self.subTest(case="TAB"):
            self.check_case(original + row(2000, "TAB-200-OKK").replace(" | ", "\t|\t"), "TAB-200-OKK")
        with self.subTest(case="CRLF"):
            self.check_case(original.replace("\n", "\r\n"))
        with self.subTest(case="TIE"):
            self.check_case(original + row(1629), status=2, warning="2 missions tie")
        with self.subTest(case="NONE"):
            self.check_case("".join(line for line in original.splitlines(True) if "Mars" not in line), status=1, warning="no qualifying")
        with self.subTest(case="REORDER"):
            self.check_case("".join(reordered([7, 3, 0, 2, 1, 5, 4, 6])))
        with self.subTest(case="SWAP67"):
            self.check_case("".join(reordered([0, 1, 2, 3, 4, 6, 5, 7])))
        with self.subTest(case="NOHEADER"):
            self.check_case("".join(line for line in original.splitlines(True) if "# Format:" not in line), status=3, warning="header")
        replacements = [
            ("H_CASE", "# Format: DATE | mission id | DESTINATION | status | Crew Size | duration(DAYS) | Success Rate | security_code\n", 0, None),
            ("H_DUP", HEADER.replace("Mission ID", "DESTINATION"), 3, "duplicate destination"),
            ("H_TYPO", HEADER.replace("Destination", "Destinaton"), 0, "warning: treating header"),
            ("H_TYPO_DUP", HEADER.replace("Mission ID", "Destinaton"), 0, "misspelled duplicate"),
        ]
        for name, replacement, status, warning in replacements:
            with self.subTest(case=name):
                content = "".join(replacement if line.startswith("# Format:") else line for line in original.splitlines(True))
                self.check_case(content, status=status, warning=warning)
        for name, addition, expected, status, warning in [
            ("E_CASE", row(2100, "CAS-210-UPP", "MARS", "COMPLETED"), "CAS-210-UPP", 0, None),
            ("E_TYPO_WIN", row(2200, destination="Mras"), None, 4, "refusing to answer"),
            ("E_TYPO_LOSE", row(500, status="Completd"), "XRT-421-ZQP", 0, "warning:"),
            ("E_UNCOMP", row(2300, status="Uncompleted"), "XRT-421-ZQP", 0, None),
        ]:
            with self.subTest(case=name):
                self.check_case(original + addition, expected, status, warning)

    def test_invalid_durations_are_skipped(self):
        for value in ("", "garbage", "9994d", "-10", "+20", "1e9", "NaN", "Inf", "1,000", ".5", "5.", "9" * 400):
            with self.subTest(duration=value):
                self.check_case(HEADER + row(value) + row(0, "ZER-000-DAY"), "ZER-000-DAY")

    def test_decimal_durations_and_numeric_ties(self):
        self.check_case(HEADER + row("001.25") + row("1.5", "DEC-150-MAX"), "DEC-150-MAX")
        self.check_case(HEADER + row("1.50") + row("01.5"), status=2, warning="2 missions tie")

    def test_tie_can_be_superseded_by_a_unique_maximum(self):
        self.check_case(HEADER + row(5) + row(5) + row(6, "NEW-006-MAX"), "NEW-006-MAX")

    def test_three_way_tie(self):
        self.check_case(HEADER + row(5) * 3, status=2, warning="3 missions tie")

    def test_suspect_equal_to_maximum_or_without_exact_matches(self):
        for content in (row(100) + row(100, destination="Marz"), row(100, status="Completd")):
            with self.subTest(content=content):
                self.check_case(HEADER + content, status=4, warning="refusing to answer")

    def test_explicit_aliases_and_empty_alias_entries(self):
        with patch.dict(os.environ, {"DEST_ALIASES": " , MRAS,marz, ", "STATUS_ALIASES": " Completd, "}):
            self.check_case(HEADER + row(100, "ALS-100-YES", "Mras", "Completd"), "ALS-100-YES")
            self.check_case(HEADER + row(100, destination="") + row(0, "ZER-000-DAY"), "ZER-000-DAY")
        with patch.dict(os.environ, {"DEST_ALIASES": "moon", "STATUS_ALIASES": "approved"}):
            self.check_case(HEADER + row(100, "ALS-100-YES", "Moon", "Approved"), "ALS-100-YES")

    def test_missing_ambiguous_and_duplicate_headers(self):
        for header in (
            HEADER.replace("Destination", "Planet"),
            HEADER.replace("Destination", "Destinaton").replace("Mission ID", "Destinatiom"),
            HEADER.replace("Mission ID", "duration"),
            HEADER.replace("Security Code", ""),
        ):
            with self.subTest(header=header):
                self.check_case(header + row(1), status=3, warning="invalid header")

    def test_empty_headerless_and_data_before_header(self):
        for content in ("", "# Only comments\n", row(9999), row(9999) + HEADER + row(1), row(9999, destination="Venus", status="Failed") + HEADER + row(1)):
            with self.subTest(content=content):
                self.check_case(content, status=3, warning="header")

    def test_repeated_header_and_mid_file_column_change(self):
        reversed_header = "# fOrMaT: " + "|".join(HEADER.split(":", 1)[1].strip().split("|")[::-1]) + "\n"
        reversed_row = "|".join(row(20, "REV-020-MAX").strip().split("|")[::-1]) + "\n"
        self.check_case(HEADER + row(5) + HEADER + row(10) + reversed_header + reversed_row, "REV-020-MAX")
        self.check_case(HEADER + row(5) + HEADER.replace("Destination", "Planet"), status=3, warning="invalid header")

    def test_missing_fields_and_absent_final_newline(self):
        truncated = "|".join(row(9999).split("|")[:-1]) + "\n"
        self.check_case(HEADER + truncated + row(10).rstrip("\n"), "TST-123-ROW")

    def test_bounded_cache_does_not_change_classification(self):
        unique_values = "".join(row(9999, destination=f"Other-{i}") for i in range(300))
        unique_values += "".join(row(9999, status=f"Other-{i}") for i in range(300))
        # Disable both prefilters so every distinct value reaches classification.
        with patch.dict(os.environ, {"DEST_ALIASES": "unused-destination", "STATUS_ALIASES": "unused-status"}):
            self.check_case(HEADER + unique_values + row(10), "TST-123-ROW")
            self.check_case(HEADER + unique_values + row(10) + row(20, destination="Mras"), status=4, warning="refusing to answer")

    def test_one_edit_candidates_survive_filtering(self):
        for target, field in (("mars", "destination"), ("completed", "status")):
            variants = {target[:i] + target[i + 1:] for i in range(len(target))}
            variants.update(target[:i] + target[i + 1] + target[i] + target[i + 2:] for i in range(len(target) - 1))
            for char in ("x", " ", "\t"):
                variants.update(target[:i] + char + target[i + 1:] for i in range(len(target)))
                variants.update(target[:i] + char + target[i:] for i in range(len(target) + 1))
            for value in sorted(variants):
                # Trimming may turn an edge-space insertion into an exact match.
                normalized = " ".join(value.lower().split())
                variants_to_check = (value, value.upper(), value.replace(" ", " \t "))
                for variant in variants_to_check:
                    with self.subTest(field=field, value=variant):
                        content = HEADER + row(10, "NEW-010-MAX", **{field: variant})
                        if normalized == target:
                            self.check_case(content, "NEW-010-MAX")
                        else:
                            self.check_case(content, status=4, warning="refusing to answer")

    def test_original_line_numbers_survive_filtering(self):
        content = HEADER + row(9999, destination="Venus", status="Failed") * 30
        content += row(1) + row(10, destination="Mras")
        self.check_case(content, status=4, warning="longest at line 33")

    def test_filter_errors_do_not_print_a_partial_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            grep = Path(directory) / "grep"
            grep.write_text("#!/bin/sh\nprintf '%s\\n' '1:" + HEADER.rstrip() + "' '2:" + row(100).rstrip() + "'\nexit 2\n")
            grep.chmod(0o755)
            with patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
                self.check_case(HEADER + row(100), status=5, warning="input filter failed")


if __name__ == "__main__":
    unittest.main()
