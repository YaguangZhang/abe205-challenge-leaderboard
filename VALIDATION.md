# Course challenge, bonus activity, and score ties · validation

Prepared from the GitHub repository's `main` branch at commit `7e2a980fe8dff1119cded8d655bd9c48a29ed1ec`, checked on September 19, 2026. The source CSV, LICENSE, and Pages workflow are preserved. This archive contains the updated project contents without Git history or generated JSON.

## Verified

- **41 Python standard-library tests pass.** Coverage includes filename selection, Unicode/quoted names, dynamic required and bonus columns, unchanged supplied scores and percentages, score-cap validation, malformed/missing values, old CSVs without bonus, multiple bonus activities, ranking, public-data minimization, and stale-output removal. New cases cover competition-style numbering (1, 2, 3, 4, 5, 5, 7), all-zero ties, unique scores, and equal numeric scores with different CSV formatting.
- **The current CSV builds with no warnings:** 26 participants, five required tasks, one optional bonus, and a 200-point cap. All published scores and display percentages agree with the CSV. Paisley has 20 points, 10% score progress, no required tasks completed, and one completed bonus. John Holland has 30 points, 15%, one required task completed, and one completed bonus.
- **Ranking remains based on required completion.** Bonus does not create a sixth required task or provide an extra tie-breaker. Finishers without a completed bonus still qualify for completion-time ordering. A 200-point score alone does not make an unfinished participant a finisher.
- **Shared numbers preserve ordering.** Equal scores share their first list position, including when completion-time ordering separates equal scores. Existing tests also check that different required-task counts and finish times still determine row order. Separate list positions remain available for next/previous navigation; search retains full-roster tie information.
- **Static site validation passes:** generated JSON schema version 3, shared ranks and tie counts, required/bonus counts, project-relative assets, and the public artifact allowlist.
- **JavaScript syntax passes** with `node --check site/app.js`. Node is only a delivery check; the project still requires only Python 3.10+ for development and deployment.
- **Local HTTP smoke checks pass:** `dev.py` prepares the data and serves the site's HTML, CSS, JavaScript, SVG, and JSON with HTTP 200. Source CSVs and Python files are not served.

## Browser and deployment limits

The summary alignment has also been corrected: the three values and labels use the same vertical order at every breakpoint, with the optional bonus note below the required-task label. The required-task count uses ordinary number formatting (5 rather than 05).

The heading and browser title now read “Course Challenge Leaderboard.” Equal scores use shared numbers with a small “tie” label beneath the rank, matching text in participant focus, and an accessible explanation on each row. Mobile title sizing accommodates the longer heading.

The updated interface was reviewed in source but has not been visually or interactively verified in a browser. The remote browser cannot reach the local development server; a local browser download also failed in this environment. Existing responsive, keyboard-focus, dialog, and reduced-motion behavior is retained, with the bonus UI added to the same layouts.

No remote commits or deployments were made as part of this ZIP delivery. The existing GitHub Pages workflow is unchanged.

Before publishing, run `python scripts/dev.py` and check Paisley and John Holland in the search results and focus panel. Confirm their supplied scores, the bonus badge, five required milestones, and the separate completed bonus star. Check a participant without bonus completion for the outlined star and “Not completed” text. Verify search reset, Escape to close the dialog, and the narrow-screen card layout.

Also check the new title and shared score ranks. Harold and sparklygiraffe should both display 05 with a “tie” label, while retaining their relative order. Searching for either name should keep the shared number and tie label. The participant panel should show that shared rank, while its navigation counter continues to advance once per participant.
