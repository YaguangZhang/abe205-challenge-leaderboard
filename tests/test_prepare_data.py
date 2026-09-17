import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_data import DataError, filename_timestamp, parse_completion_time, prepare, select_latest, write_data


class DataPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.headers = ["Name", "C#1 - First - 10 pts", "C#2 - Second - 30 pts", "Total Score", "Percentage", "Completion Time (YYYYMMDD-HHMMSS)"]

    def roster(self, rows, filename="Participants_20260912.csv", headers=None):
        path = self.root / filename
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers or self.headers)
            writer.writerows(rows)
        return path

    def test_latest_uses_encoded_date_not_mtime(self):
        old = self.roster([["Old", 0, 0, 0, 0]], "Participants_20260101.csv")
        newest = self.roster([["New", 0, 0, 0, 0]], "Participants_20260912-183001.csv")
        self.roster([["Midday", 0, 0, 0, 0]], "Participants_20260912-120001.csv")
        os.utime(old, (2000000000, 2000000000))
        os.utime(newest, (1, 1))
        self.assertEqual(select_latest(self.root), newest)

    def test_invalid_dates_times_and_attachment_suffix_are_ignored(self):
        for filename in ["Participants_20260230.csv", "Participants_20260912-246000.csv", "Participants_20260912(1).csv", "Participants_99999999.csv"]:
            self.roster([], filename)
            self.assertIsNone(filename_timestamp(filename))
        with self.assertRaisesRegex(DataError, "No valid"):
            select_latest(self.root)

    def test_calendar_leap_days_and_midnight_tie_are_deterministic(self):
        self.assertIsNotNone(filename_timestamp("Participants_20240229.csv"))
        self.assertIsNone(filename_timestamp("Participants_20230229.csv"))
        self.roster([], "Participants_20260912.csv")
        self.roster([], "Participants_20260912-000000.csv")
        self.assertEqual(select_latest(self.root).name, "Participants_20260912.csv")

    def test_unicode_quotes_capitalization_and_spaces_are_preserved(self):
        names = ["Aarón", 'Quinn "Q", Phelan', "  lilly  w  ", "李 明", "<img src=x onerror=alert(1)>"]
        self.roster([[name, 0, 0, 0, 0, ""] for name in names])
        data, warnings = prepare(self.root)
        self.assertCountEqual([p["name"] for p in data["participants"]], names)
        self.assertFalse(warnings)
        write_data(self.root)
        self.assertIn("Aarón", (self.root / "site/data/leaderboard.json").read_text(encoding="utf-8"))

    def test_dynamic_tasks_and_weighted_progress(self):
        headers = ["Name", "C#1 - X - 5 pts", "C#2 - Y - 20 pts", "C#3 - Z - 25 pts", "Total Score", "Percentage"]
        self.roster([["Aarón", 1, 1, 0, 25, ".5"]], headers=headers)
        data, _ = prepare(self.root)
        self.assertEqual(data["metadata"]["taskCount"], 3)
        self.assertEqual(data["metadata"]["maxScore"], 50)
        p = data["participants"][0]
        self.assertEqual(p["completedTasks"], 2)
        self.assertEqual(p["tasks"], [True, True, False])
        self.assertEqual(p["score"], 25)
        self.assertEqual(p["progress"], 50)

    def test_decimal_percentage_examples(self):
        self.roster([["Five", 0, 0, 0, ".05"], ["Ten", 0, 0, 0, ".1"], ["Full", 1, 1, 40, "1"]])
        data, _ = prepare(self.root)
        self.assertEqual({p["name"]: p["progress"] for p in data["participants"]}, {"Five": 5, "Ten": 10, "Full": 100})

    def test_missing_malformed_and_nonfinite_values_are_recovered(self):
        self.roster([["Missing", "", 1, "", ""], ["Broken", "wat", "", "NaN", "Infinity"], ["Out of range", 1, 0, -2, 5], ["Truncated", 1]])
        data, warnings = prepare(self.root)
        people = {p["name"]: p for p in data["participants"]}
        self.assertEqual(people["Missing"]["score"], 30)
        self.assertEqual(people["Missing"]["progress"], 75)
        self.assertEqual(people["Broken"]["completedTasks"], 0)
        self.assertEqual(people["Broken"]["score"], 0)
        self.assertEqual(people["Out of range"]["progress"], 25)
        self.assertEqual(people["Truncated"]["tasks"], [True, False])
        self.assertTrue(warnings)
        json.dumps(data, allow_nan=False)

    def test_task_completion_requires_one(self):
        self.roster([["A", 2, "yes", 0, 0], ["B", "1.0", "1", 40, 1]])
        data, _ = prepare(self.root)
        self.assertEqual(data["participants"][0]["tasks"], [True, True])
        self.assertEqual(data["participants"][1]["tasks"], [False, False])

    def test_unfinished_ranking_uses_score_tasks_then_alphabetical_name(self):
        headers = ["Name", "C#1 - X - 10 pts", "C#2 - Y - 30 pts", "C#3 - Z - 10 pts", "Total Score", "Percentage"]
        self.roster([["Zoey", 1, 0, 0, 10, .2], ["Aarón", 1, 0, 0, 10, .2], ["More tasks", 1, 1, 0, 10, .2], ["Winner", 0, 1, 0, 30, .6]], headers=headers)
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Winner", "More tasks", "Aarón", "Zoey"])
        self.assertEqual([p["rank"] for p in data["participants"]], [1, 2, 3, 4])

    def test_finishers_rank_first_by_time_even_with_lower_source_scores(self):
        self.roster([
            ["Unfinished", 1, 0, 40, 1, "20260901-000000"],
            ["Later", 1, 1, 40, 1, "20260912-100001"],
            ["First", 1, 1, 10, .25, "20260912-100000"],
            ["Unknown time", 1, 1, 0, 0, ""],
        ])
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["First", "Later", "Unknown time", "Unfinished"])
        self.assertEqual([p["rank"] for p in data["participants"]], [1, 2, 3, 4])

    def test_unfinished_completion_times_are_ignored(self):
        self.roster([
            ["Higher score", 0, 1, 30, .75, "malformed"],
            ["Zoey", 1, 0, 10, .25, "20200101-000000"],
            ["Aarón", 1, 0, 10, .25, "20300101-000000"],
        ])
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Higher score", "Aarón", "Zoey"])

    def test_tied_finish_times_use_name_not_score(self):
        self.roster([
            ["Zoey", 1, 1, 40, 1, "20260912-100000"],
            ["Aarón", 1, 1, 10, .25, "20260912-100000"],
        ])
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Aarón", "Zoey"])

    def test_missing_and_malformed_finish_times_sort_after_valid_finish_times(self):
        self.roster([
            ["B invalid", 1, 1, 40, 1, "20260230-120000"],
            ["C truncated", 1, 1, 40, 1],
            ["A empty", 1, 1, 10, .25, ""],
            ["Valid", 1, 1, 40, 1, "99991231-235959"],
            ["Unfinished", 0, 1, 30, .75, "20200101-000000"],
        ])
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Valid", "A empty", "B invalid", "C truncated", "Unfinished"])

    def test_completion_time_parser_checks_format_and_calendar(self):
        for invalid in [None, "", " ", 123, "bad", "20260230-120000", "20260912-240000", "20260912-126000", "20260912-120060", "20260912-10000", "2026912-100000", "20260912", "20260912-120000Z"]:
            with self.subTest(value=invalid):
                self.assertIsNone(parse_completion_time(invalid))
        self.assertEqual(parse_completion_time(" 20240229-120000 ").isoformat(), "2024-02-29T12:00:00")

    def test_finishers_rank_without_completion_time_column(self):
        headers = ["Name", "C#1 - Task - 40 pts", "Total Score", "Percentage"]
        self.roster([["Zoey", 1, 40, 1], ["Aarón", 1, 10, .25], ["Unfinished", 0, 40, 1]], headers=headers)
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Aarón", "Zoey", "Unfinished"])

    def test_valid_source_score_and_fraction_are_authoritative(self):
        self.roster([["A", 1, 0, 20, .7]])
        data, warnings = prepare(self.root)
        self.assertEqual(data["participants"][0]["score"], 20)
        self.assertEqual(data["participants"][0]["progress"], 70)
        self.assertEqual(len(warnings), 2)

    def test_header_weights_take_precedence_over_fallback(self):
        (self.root / "leaderboard.config.json").write_text('{"fallback_task_points":{"1":999,"2":999}}')
        self.roster([["A", 1, 1, 40, 1]])
        data, warnings = prepare(self.root)
        self.assertEqual(data["metadata"]["maxScore"], 40)
        self.assertFalse(warnings)

    def test_configured_fallback_is_validated(self):
        self.roster([["A", 1, 0, 10, .25]], headers=["Name", "C#1 - Missing points", "C#2 - Task - 30 pts", "Total Score", "Percentage"])
        with self.assertRaisesRegex(DataError, "cannot determine points"):
            prepare(self.root)
        config = self.root / "leaderboard.config.json"
        config.write_text('{"fallback_task_points":{"1":10}}')
        data, warnings = prepare(self.root)
        self.assertEqual(data["metadata"]["maxScore"], 40)
        self.assertTrue(warnings)
        config.write_text('{"fallback_task_points":{"1":-10}}')
        with self.assertRaisesRegex(DataError, "Invalid leaderboard.config"):
            prepare(self.root)

    def test_missing_duplicate_and_absent_task_headers_fail(self):
        for headers in [["Name"], ["Name", "Name", "Total Score", "Percentage"], ["Name", "Total Score", "Percentage"]]:
            self.roster([], headers=headers)
            with self.assertRaises(DataError):
                prepare(self.root)

    def test_empty_or_unnamed_roster_fails_and_extra_cells_are_skipped(self):
        self.roster([["", 0, 0, 0, 0], [" ", 0, 0, 0, 0]])
        with self.assertRaisesRegex(DataError, "no valid named participants"):
            prepare(self.root)
        self.roster([["Good", 0, 0, 0, 0, ""], ["Bad", 0, 0, 0, 0, "", "EXTRA"]])
        data, warnings = prepare(self.root)
        self.assertEqual(data["metadata"]["participantCount"], 1)
        self.assertTrue(warnings)

    def test_malformed_csv_reports_error(self):
        path = self.roster([])
        with path.open("a", encoding="utf-8") as handle:
            handle.write('"unclosed name,1,0,10,.25\n')
        with self.assertRaisesRegex(DataError, "Cannot read"):
            prepare(self.root)

    def test_newest_invalid_schema_fails_instead_of_showing_stale_roster(self):
        self.roster([["Good", 0, 0, 0, 0]], "Participants_20260911.csv")
        self.roster([], headers=["Wrong"])
        with self.assertRaisesRegex(DataError, "missing required columns"):
            prepare(self.root)

    def test_failed_build_removes_stale_generated_json(self):
        source = self.roster([["A", 0, 0, 0, 0]])
        write_data(self.root)
        output = self.root / "site/data/leaderboard.json"
        self.assertTrue(output.exists())
        source.unlink()
        with self.assertRaises(DataError):
            write_data(self.root)
        self.assertFalse(output.exists())

    def test_generated_data_omits_challenge_names_and_completion_time(self):
        self.roster([["A", 1, 1, 40, 1, "20260912-140000"]])
        data, _ = write_data(self.root)
        encoded = json.dumps(data)
        for private_text in ["First", "Second", "Completion Time", "_completionTime", "20260912-140000", "C#"]:
            self.assertNotIn(private_text, encoded)

    def test_standard_five_task_schema(self):
        # A self-contained fixture lets instructors replace any real source CSV.
        headers = ["Name"] + [f"C#{i} - Task - {points} pts" for i, points in enumerate([10, 10, 50, 30, 100], 1)] + ["Total Score", "Percentage"]
        self.roster([["Quinn Phelan", 1, 1, 0, 0, 0, 20, .1], ["Aarón", 0, 0, 0, 0, 0, 0, 0]], headers=headers)
        data, warnings = prepare(self.root)
        self.assertEqual(data["metadata"]["participantCount"], 2)
        self.assertEqual(data["metadata"]["taskCount"], 5)
        self.assertEqual(data["metadata"]["maxScore"], 200)
        self.assertEqual(data["participants"][0]["name"], "Quinn Phelan")
        self.assertEqual(data["participants"][0]["progress"], 10)
        self.assertIn("Aarón", [p["name"] for p in data["participants"]])
        self.assertFalse(warnings)


if __name__ == "__main__":
    unittest.main()
