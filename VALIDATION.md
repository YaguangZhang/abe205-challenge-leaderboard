# Theme selector, bonus activity, and score ties · validation

Prepared from the GitHub repository's `main` branch at commit `7e2a980fe8dff1119cded8d655bd9c48a29ed1ec`, checked on September 19, 2026. The source CSV, LICENSE, and Pages workflow are preserved. This archive contains the updated project contents without Git history or generated JSON.

## Verified

- **41 Python standard-library tests pass.** Coverage includes filename selection, Unicode/quoted names, dynamic required and bonus columns, unchanged supplied scores and percentages, score-cap validation, malformed/missing values, old CSVs without bonus, multiple bonus activities, ranking, public-data minimization, and stale-output removal. New cases cover competition-style numbering (1, 2, 3, 4, 5, 5, 7), all-zero ties, unique scores, and equal numeric scores with different CSV formatting.
- **9 Node standard-library theme-controller tests pass.** They execute the actual theme controller using a strict browser fixture. Coverage includes all eight random-selection intervals, early application before the body is ready, every manual choice, unchanged themes on tab switches, independent reloads, restored form values, and back/forward cache returns. The fixture rejects storage access, timers, participant data requests, and access to leaderboard elements. These are controller tests, not browser rendering tests.
- **Leaderboard behavior is unchanged by themes.** The source CSV, score configuration, `prepare_data.py`, and `app.js` were compared byte-for-byte with the preceding ZIP and are identical. Theme switching only updates the document theme, dropdown, browser theme color, and accessible status text.
- **The current CSV builds with no warnings:** 26 participants, five required tasks, one optional bonus, and a 200-point cap. All published scores and display percentages agree with the CSV. Paisley has 20 points, 10% score progress, no required tasks completed, and one completed bonus. John Holland has 30 points, 15%, one required task completed, and one completed bonus.
- **Ranking remains based on required completion.** Bonus does not create a sixth required task or provide an extra tie-breaker. Finishers without a completed bonus still qualify for completion-time ordering. A 200-point score alone does not make an unfinished participant a finisher.
- **Shared numbers preserve ordering.** Equal scores share their first list position, including when completion-time ordering separates equal scores. Existing tests also check that different required-task counts and finish times still determine row order. Separate list positions remain available for next/previous navigation; search retains full-roster tie information.
- **Static site validation passes:** generated JSON schema version 3, shared ranks and tie counts, required/bonus counts, project-relative assets, and the public artifact allowlist including `themes.js` and `themes.css`.
- **JavaScript syntax and CSS source checks pass.** CSS blocks and custom-property references are consistent. The base text/accent colors meet a 4.5:1 contrast threshold against their configured background/surface colors in all eight palettes. Glass alpha colors were composited over the base background for this calculation; this is not a full rendered accessibility audit. Theme-specific toolbar and bonus text colors were also checked.
- **Local HTTP smoke checks pass:** `dev.py` prepares the data and serves HTML, both CSS files, both JavaScript files, SVG, and JSON with HTTP 200. Source CSVs, Python files, and tests are not served. Node is used only for optional contributor tests and delivery checks; Python 3.10+ remains the only build/serve prerequisite.

## Browser and deployment limits

The summary alignment has also been corrected: the three values and labels use the same vertical order at every breakpoint, with the optional bonus note below the required-task label. The required-task count uses ordinary number formatting (5 rather than 05).

The heading and browser title now read “Course Challenge Leaderboard.” Equal scores use shared numbers with a small “tie” label beneath the rank, matching text in participant focus, and an accessible explanation on each row. Mobile title sizing accommodates the longer heading.

The “Professor Yaguang Zhang” credit links to `http://yaguangzhang.github.io/`. It uses each theme's text and accent colors, with an underline and the existing keyboard-focus outline.

The inactive ABE 205 badge has been replaced with a labeled native theme dropdown. The course subtitle includes “ABE 205:”. All eight themes share the same DOM and responsive layout. Theme differences include typography, backgrounds, borders, card shapes, meters, shadows, and decorative brand-mark styling. Purdue retains the original design. Each page load gets an independent random selection, including cached-page returns; tab switches and manual selections do not reroll during a visit. Independent random choices can repeat.

The updated interface was reviewed in source but has not been visually or interactively verified in a browser. No browser executable is available in this environment. The earlier remote-browser and local-download attempts were unsuccessful. Existing responsive, keyboard-focus, dialog, and reduced-motion behavior is retained. Theme selection uses a native dropdown, and Glass includes an opaque fallback when background blur is unsupported or reduced transparency is requested.

No remote commits or deployments were made as part of this ZIP delivery. The existing GitHub Pages workflow is unchanged.

Before publishing, run `python scripts/dev.py` and check Paisley and John Holland in the search results and focus panel. Confirm their supplied scores, the bonus badge, five required milestones, and the separate completed bonus star. Check a participant without bonus completion for the outlined star and “Not completed” text. Verify search reset, Escape to close the dialog, and the narrow-screen card layout.

Also check the new title and shared score ranks. Harold and sparklygiraffe should both display 05 with a “tie” label, while retaining their relative order. Searching for either name should keep the shared number and tie label. The participant panel should show that shared rank, while its navigation counter continues to advance once per participant.

Check all eight themes on desktop and phone widths. Confirm the dropdown changes the appearance immediately, search remains active, ties and bonus indicators remain readable, and participant navigation works in each style. Reload, navigate away and back, and switch tabs to check visit behavior. The dropdown moves below the brand at narrow widths. Keyboard Tab/arrow keys should operate the selector, and manual choices should be announced by a screen reader.
