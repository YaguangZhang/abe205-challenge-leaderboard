# ABE 205 · Computations Leaderboard

A static, gold-and-black course challenge leaderboard for Purdue **ABE 205: Computations for Engineering Systems**, led by Professor Yaguang Zhang. Names and scores take center stage. Search a participant, open their focus panel, and explore their progress through unnamed milestones.

**Python 3.10+ is the only local prerequisite.** There are no packages to install, API keys, logins, external fonts, frontend frameworks, or production servers. The supplied roster is included as `Participants_20260912.csv`; its download suffix `(1)` was removed without changing the CSV contents.

## Run locally

From the repository directory:

```bash
python scripts/dev.py
```

Open **http://127.0.0.1:8000/**. The command prepares the newest roster, then serves only `site/`. Stop with **Ctrl+C**. Use `python3` on systems where Python 3 is named `python3`, or `py -3` on Windows.

Optional port:

```bash
python scripts/dev.py --port 8080
```

Do not open `index.html` with `file://`: the page fetches its JSON over HTTP. The development server binds to loopback by default. To test on a phone on your own network, use `--host 0.0.0.0` and open your computer's LAN address and chosen port.

## Add or update a roster

1. Place the CSV in the **repository root**, beside this README.
2. Name it `Participants_YYYYMMDD.csv`, for example `Participants_20260913.csv`. Optional time precision: `Participants_20260913-143000.csv`.
3. Restart the local command, or run `python scripts/prepare_data.py` and refresh your already-running page.
4. Commit and push the CSV to your repository's default branch to update GitHub Pages.

The script selects the **latest valid date and time encoded in a filename**, never filesystem modification time. Date-only names mean midnight. Invalid calendar dates, invalid times, subdirectory files, and download suffixes such as `(1)` are ignored. In the rare case of identical timestamps, the lexicographically greater filename wins (the date-only name wins a midnight tie). Keep timestamps in one consistent timezone.

Old files may remain in the root. The newest filename is selected first; an invalid schema in that newest file fails the build instead of silently reverting to an older roster. Fix or remove that file to continue.

## CSV schema and scoring

Required headers: `Name`, `Total Score`, `Percentage`, and at least one header beginning with `C#`. Task headers stay in CSV source only. The optional `Completion Time (YYYYMMDD-HHMMSS)` field can be empty or absent and is never published in frontend JSON.

| Input | Interpretation |
| --- | --- |
| `Name` | Preserved display name, including Unicode, spacing, and capitalization |
| Every `C#…` column | Numeric `1` means completed; `0`, empty, or invalid values mean incomplete |
| Header suffix `- 50 pts` | A task worth 50 points; task count and maximum score are derived dynamically |
| `Total Score` | The authoritative score when finite and within `0…maximum` |
| `Percentage` | A fraction: `0.05` → 5%, `0.1` → 10%, `1` → 100% |

**Progress is point-weighted**, not the fraction of tasks completed. In the included roster, Quinn Phelan has 2 / 5 tasks and 20 / 200 points, so progress is 10%. Percentage labels display up to two decimal places.

Default ranking:

1. Participants who have completed every task rank ahead of unfinished participants. Completion is determined from all dynamically discovered task columns, not from score or percentage.
2. Finishers rank by **completion time ascending**: the earliest valid `Completion Time (YYYYMMDD-HHMMSS)` ranks highest.
3. Unfinished participants rank by **total score descending**. Their completion-time values are ignored.
4. Remaining ties use **completed-task count descending**, then **participant name alphabetically**. Scores do not break ties between finishers.

Empty, absent, or malformed completion times are treated as unknown. Finishers with unknown times follow all finishers with valid times, remain ahead of every unfinished participant, and use the same task-count/name tie-breakers. Timestamp parsing requires `YYYYMMDD-HHMMSS` and a valid calendar date and time; surrounding whitespace is ignored. Use one consistent timezone for completion timestamps. Times are used only during preprocessing and are omitted from the generated JSON and interface.

Alphabetical comparison ignores case and accents; exact name spelling resolves any remaining comparison tie. Identical duplicate records retain CSV order. Ranks are sequential, and filtering preserves overall ranks.

### Recovery rules

- Task count is the number of `C#` columns, and task order follows the CSV. The UI creates as many milestone indicators as needed.
- Point suffixes are preferred. If a suffix cannot be parsed, `leaderboard.config.json` supplies **positive point values by numeric task ID**. Its initial fallback is C#1–C#5 → 10, 10, 50, 30, 100. Update this file when changing task weights if you need fallback support. Unknown task IDs without parseable weights fail with an actionable error; the script never guesses a maximum.
- Invalid, empty, non-finite, negative, or excessive scores are recalculated from completed tasks and their point weights.
- Invalid or out-of-range percentages are recalculated from score / maximum. Valid source values are retained; inconsistencies produce build warnings.
- Blank-name rows and rows with extra cells are skipped with warnings. Truncated task cells become incomplete. Broken quoting, invalid UTF-8, duplicate/missing headers, or an entirely unusable roster produce a clear build error.
- A failed preparation removes stale generated JSON locally. A failed GitHub workflow does not deploy; the last successful public deployment remains available.
- Participant text is rendered with `textContent`. Search ignores case and accents, so `aaron` matches `Aarón`. The UI presents a friendly retry state if JSON cannot be loaded or validated.

## Test and build

All data tests use Python's standard library and isolated fixtures, so updating the actual roster does not require changing tests:

```bash
python -m unittest discover -s tests -v
```

Build the current roster and validate the public files:

```bash
python scripts/prepare_data.py
python scripts/validate_site.py
```

The tests cover date selection independent of modification times, invalid filenames, Unicode and quoted names, dynamic tasks, weighted totals, percentage conversion, ranking, malformed values, validated point fallbacks, omitted private fields, and stale-output cleanup. The site validator checks generated data, required files, relative asset paths, and the public artifact allowlist. If adding assets, update that allowlist in `scripts/validate_site.py`.

For a quick manual UI check: search `aaron`, clear the search, select Quinn, confirm 20 / 200 and 10% with two checked milestones, navigate to Harold, and press Escape. Tab and Enter work on rows; native dialog focus stays inside the panel until closed. Check the card layout at a narrow viewport and the browser's reduced-motion setting.

## Deploy to GitHub Pages

Create an empty GitHub repository, then run these commands from this project directory, replacing `YOUR-USER` and `YOUR-REPOSITORY`:

```bash
git init -b main
git add .
git commit -m "Build ABE 205 computations leaderboard"
git remote add origin https://github.com/YOUR-USER/YOUR-REPOSITORY.git
git push -u origin main
```

If working in an existing clone, copy these files into it and commit/push normally instead of running `git init` or adding an existing remote again. Include `.github/workflows/deploy-pages.yml` and the other dotfiles when copying.

**One-time repository setting:** open **Settings → Pages → Build and deployment → Source → GitHub Actions**. This is GitHub's [documented configuration for custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

Then open **Actions → Validate and deploy leaderboard → Run workflow**, choose the default branch, and run it. This also lets you retry an initial push that ran before Pages was enabled. The successful `deploy` job reports your page URL; it is also available under Settings → Pages.

The workflow tests and builds on all branch pushes and pull requests, but **publishes only the repository's current default branch**. No workflow edit is needed if that branch is called `master` or another name. Later pushes to that branch rebuild and deploy automatically. If your repository has environment protection rules, allow that branch in the `github-pages` environment.

The workflow follows GitHub's [official custom Pages build/upload/deploy structure](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages): read-only build permissions, a Pages artifact containing only `site/`, and a separate deploy job with `pages: write` and `id-token: write`. It uses the automatic `GITHUB_TOKEN`; no personal token is needed. All browser asset/data URLs are relative, so project URLs such as `https://YOUR-USER.github.io/YOUR-REPOSITORY/` work without source edits.

The public page exposes participant names, scores, ranks, progress, and task completion states. The deployment artifact excludes the source CSVs, challenge names, scripts, and tests. Files committed to a public source repository remain visible there.

## Files

| Path | Purpose |
| --- | --- |
| `Participants_20260912.csv` | Included source roster; add newer dated CSVs alongside it |
| `leaderboard.config.json` | Validated fallback point weights |
| `scripts/prepare_data.py` | Select, validate, normalize, rank, and generate JSON |
| `scripts/dev.py` | Prepare data and start a local HTTP server |
| `scripts/validate_site.py` | Verify the deployable static artifact |
| `site/index.html` | Semantic interface, row template, and native focus dialog |
| `site/styles.css` | Responsive design, focus states, and reduced-motion support |
| `site/app.js` | JSON validation, safe rendering, search, and participant selection |
| `site/assets/favicon.svg` | Self-contained course leaderboard icon |
| `site/data/leaderboard.json` | Generated output; ignored by Git and rebuilt for development/deployment |
| `site/data/.gitkeep`, `site/.nojekyll` | Keep the output directory and static-site marker |
| `tests/test_prepare_data.py` | Dependency-free regression tests |
| `.github/workflows/deploy-pages.yml` | Validation and official GitHub Pages deployment |

The frontend uses system fonts and a simple computation-inspired icon, without externally loaded imagery or Purdue logo assets.
