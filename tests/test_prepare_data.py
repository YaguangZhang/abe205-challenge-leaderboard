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

    def test_invalid_scores_are_skipped_without_recalculating(self):
        self.roster([["Good", "", 1, 30, .75], ["Missing", 1, 1, "", ""], ["Broken", "wat", "", "NaN", "Infinity"], ["Out of range", 1, 0, -2, 5], ["Truncated", 1]])
        data, warnings = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Good"])
        self.assertEqual(data["participants"][0]["score"], 30)
        self.assertEqual(data["participants"][0]["progress"], 75)
        self.assertEqual(data["participants"][0]["tasks"], [False, True])
        self.assertTrue(warnings)
        json.dumps(data, allow_nan=False)

    def test_invalid_percentages_are_skipped_without_recalculating(self):
        for value in ["", "NaN", "Infinity", "bad", -1, 1.1]:
            with self.subTest(value=value):
                self.roster([["Good", 1, 0, 10, .25], ["Bad", 1, 1, 40, value]])
                data, warnings = prepare(self.root)
                self.assertEqual([p["name"] for p in data["participants"]], ["Good"])
                self.assertTrue(warnings)

    def test_truncated_task_values_are_incomplete_with_valid_source_score(self):
        headers = ["Name", "Total Score", "Percentage", "C#1 - Task - 10 pts", "C#2 - Task - 30 pts"]
        self.roster([["A", 10, .25, 1]], headers=headers)
        data, warnings = prepare(self.root)
        self.assertEqual(data["participants"][0]["tasks"], [True, False])
        self.assertTrue(warnings)

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
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 2, 2, 2])
        self.assertEqual([p["tieCount"] for p in data["participants"]], [1, 3, 3, 3])

    def test_shared_score_ranks_skip_occupied_positions(self):
        self.roster([[name, 0, 0, score, .5] for name, score in
                     [("A", 40), ("B", 35), ("C", 30), ("D", 25), ("E", 20), ("F", 20), ("G", 10)]])
        data, _ = prepare(self.root)
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 2, 3, 4, 5, 5, 7])
        self.assertEqual([p["tieCount"] for p in data["participants"]], [1, 1, 1, 1, 2, 2, 1])
        self.assertEqual([p["rank"] for p in data["participants"]], list(range(1, 8)))

    def test_everyone_with_zero_score_shares_first_rank(self):
        self.roster([[name, 0, 0, 0, 0] for name in ["Zoey", "Aarón", "Bella"]])
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Aarón", "Bella", "Zoey"])
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 1, 1])
        self.assertEqual([p["tieCount"] for p in data["participants"]], [3, 3, 3])

    def test_unique_scores_have_no_tie_indicator(self):
        self.roster([["A", 0, 0, 20, .5], ["B", 0, 0, 10, .25]])
        data, _ = prepare(self.root)
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 2])
        self.assertEqual([p["tieCount"] for p in data["participants"]], [1, 1])

    def test_equal_numeric_scores_share_rank_despite_csv_formatting(self):
        self.roster([["B", 0, 0, "10.0", .25], ["A", 0, 0, "10", .25], ["C", 0, 0, "9.5", .2]])
        data, _ = prepare(self.root)
        self.assertEqual([p["score"] for p in data["participants"]], [10, 10, 9.5])
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 1, 3])

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
        # Score ties affect labels only, even when finish-time ordering separates them.
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 2, 3, 2])
        self.assertEqual([p["tieCount"] for p in data["participants"]], [1, 2, 1, 2])

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
        self.assertFalse(warnings)

    def test_bonus_flags_do_not_change_csv_score_percentage_or_required_count(self):
        headers = ["Name", "C#1 - Task - 10 pts", "C#2 - Task - 30 pts", "Bonus - Activity - 20 pts", "Total Score", "Percentage"]
        self.roster([["Bonus only", 0, 0, 1, 20, .5], ["Required and bonus", 1, 0, 1, 30, .75]], headers=headers)
        data, warnings = prepare(self.root)
        self.assertEqual(data["metadata"]["taskCount"], 2)
        self.assertEqual(data["metadata"]["bonusTaskCount"], 1)
        self.assertEqual(data["metadata"]["maxScore"], 40)
        p = data["participants"][1]
        self.assertEqual((p["name"], p["completedTasks"], p["score"], p["progress"]), ("Bonus only", 0, 20, 50))
        self.assertEqual(p["bonusTasks"], [True])
        self.assertEqual(p["completedBonusTasks"], 1)
        self.assertFalse(warnings)

    def test_capped_scores_stay_at_200_with_completed_bonus(self):
        (self.root / "leaderboard.config.json").write_text('{"max_score":200}')
        headers = ["Name", "C#1 - Task - 200 pts", "Bonus - Activity - 20 pts", "Total Score", "Percentage"]
        self.roster([["Capped", 1, 1, 200, 1]], headers=headers)
        data, warnings = prepare(self.root)
        self.assertEqual(data["participants"][0]["score"], 200)
        self.assertEqual(data["participants"][0]["progress"], 100)
        self.assertEqual(data["metadata"]["maxScore"], 200)
        self.assertFalse(warnings)

    def test_bonus_does_not_change_finisher_detection_or_completion_time_order(self):
        headers = ["Name", "C#1 - Task - 10 pts", "C#2 - Task - 30 pts", "Bonus - Activity - 20 pts", "Total Score", "Percentage", "Completion Time (YYYYMMDD-HHMMSS)"]
        self.roster([
            ["Later with bonus", 1, 1, 1, 40, 1, "20260917-120001"],
            ["Earlier without bonus", 1, 1, 0, 40, 1, "20260917-120000"],
            ["Unfinished at cap", 0, 1, 1, 40, 1, "20260901-000000"],
        ], headers=headers)
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Earlier without bonus", "Later with bonus", "Unfinished at cap"])
        self.assertEqual([p["displayRank"] for p in data["participants"]], [1, 1, 1])

    def test_bonus_count_does_not_break_unfinished_score_and_required_task_ties(self):
        headers = ["Name", "C#1 - Task - 40 pts", "Bonus - Activity - 20 pts", "Total Score", "Percentage"]
        self.roster([["Zoey", 0, 1, 20, .5], ["Aarón", 0, 0, 20, .5]], headers=headers)
        data, _ = prepare(self.root)
        self.assertEqual([p["name"] for p in data["participants"]], ["Aarón", "Zoey"])

    def test_multiple_bonus_columns_and_missing_bonus_values(self):
        headers = ["Name", "C#1 - Task - 40 pts", "Total Score", "Percentage", "Bonus - One", "bonus - Two", "Bonus - Three", "Bonus - Four"]
        self.roster([["A", 0, 20, .5, 1, "bad", ""]], headers=headers)
        data, warnings = prepare(self.root)
        p = data["participants"][0]
        self.assertEqual(p["bonusTasks"], [True, False, False, False])
        self.assertEqual(p["completedBonusTasks"], 1)
        self.assertEqual(data["metadata"]["bonusTaskCount"], 4)
        self.assertEqual(data["metadata"]["maxScore"], 40)
        self.assertTrue(warnings)

    def test_old_csv_without_bonus_columns_still_works(self):
        self.roster([["A", 1, 0, 10, .25]])
        data, _ = prepare(self.root)
        self.assertEqual(data["metadata"]["bonusTaskCount"], 0)
        self.assertEqual(data["participants"][0]["bonusTasks"], [])
        self.assertEqual(data["participants"][0]["completedBonusTasks"], 0)

    def test_max_score_configuration_overrides_required_header_total(self):
        (self.root / "leaderboard.config.json").write_text('{"max_score":200}')
        self.roster([["A", 1, 0, 150, .75]])
        data, _ = prepare(self.root)
        self.assertEqual(data["metadata"]["maxScore"], 200)
        self.assertEqual(data["participants"][0]["score"], 150)

    def test_invalid_score_cap_configuration_fails(self):
        self.roster([["A", 0, 0, 0, 0]])
        for cap in [0, -1, "bad", True, None, 1e100]:
            with self.subTest(cap=cap):
                (self.root / "leaderboard.config.json").write_text(json.dumps({"max_score": cap}))
                with self.assertRaisesRegex(DataError, "max_score"):
                    prepare(self.root)

    def test_bonus_names_and_weights_are_not_published(self):
        headers = ["Name", "C#1 - Secret task - 40 pts", "Bonus - Secret activity - 20 pts", "Total Score", "Percentage"]
        self.roster([["A", 0, 1, 20, .5]], headers=headers)
        data, _ = write_data(self.root)
        encoded = json.dumps(data)
        self.assertNotIn("Secret", encoded)
        self.assertNotIn("20 pts", encoded)

    def test_entirely_invalid_scores_fail_instead_of_inventing_scores(self):
        self.roster([["A", 1, 1, "", ""], ["B", 1, 1, 999, 1]])
        with self.assertRaisesRegex(DataError, "finite Total Score"):
            prepare(self.root)

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
