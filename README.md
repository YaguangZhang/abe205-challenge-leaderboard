# ABE 205 Course Challenge Leaderboard

An interactive, gamified leaderboard for **Purdue ABE 205: Computations for Engineering Systems**.

The site visualizes participant progress, completed challenges, rankings, and scores in a simple game-inspired interface.

## Features

* Ranked participant leaderboard
* Shared rank numbers and a small “tie” label for equal scores
* Score and overall progress tracking
* Completed challenge indicators
* Optional bonus milestones and a star badge for completed bonus activity
* Participant search and focus view
* Responsive desktop and mobile design
* Eight distinctive themes with a dropdown and a fresh random choice each visit
* Automatic selection of the newest participant CSV
* Static GitHub Pages deployment
* No backend, database, or API keys required

## Default Ranking

1. Participants who have completed all **required** challenges are ranked ahead of participants who have not. Bonus activity is optional.
2. Among participants who have completed all required challenges, rank by **Completion Time ascending** — the person who completed all required challenges first ranks highest.
3. Among participants who have not completed all challenges, rank by **Total Score descending**.
4. Then by **number of completed required tasks descending**.
5. Finally by **participant name alphabetically** for deterministic tie-breaking.

Completion time should only affect ranking after a participant has completed all required challenges. Empty or malformed completion times must not cause errors.

Finishers with unknown times follow finishers with valid times and remain ahead of unfinished participants. Bonus completion does not provide an additional ranking tie-breaker. A 200-point score or 100% score progress does not by itself mean all required tasks are complete.

**Displayed ties:** equal CSV scores share the position of their first appearance in the ordered list, with a small **tie** label. Numbering skips occupied positions, for example **04, 05 · tie, 05 · tie, 07**. These labels do not change any ordering rule above: completion times, required-task counts, and names still decide row order. Ties remain visible in search results and the participant focus panel. The panel's next/previous counter tracks each participant's individual position.

## Themes

Use the **Theme** dropdown at the top right of the header (below the brand on small screens). The course label now reads **ABE 205: Computations for Engineering Systems**.

| Theme | Visual treatment |
| --- | --- |
| Arcade | Dark purple cabinet, candy colors, chunky borders, segmented progress bars |
| Festival | Warm paper, colorful confetti patterns, rounded cards, playful serif headings |
| Glass / Futuristic | Translucent panels, blue/violet gradients, frosted glass and soft shadows |
| Minimal | White surfaces, quiet typography, fine rules and more breathing room |
| Neon | Dark technical grid, cyan/magenta accents and luminous edges |
| Purdue | Original Purdue-inspired gold-and-black design |
| Retro | Typewriter typography, vintage paper, square edges and striped meters |
| Sports Broadcast | Navy studio header, bold scoreboard typography and red/blue graphics |

Each new page load chooses uniformly at random from all eight themes before the page is painted. Manual selection changes the styling immediately and stays active during that visit. Reloading or returning through browser back/forward navigation makes a fresh random choice. Switching tabs, searching, opening a participant, or navigating between participants does not change the theme. An independent random draw can occasionally repeat the previous theme.

Theme state exists only in the current document. The site uses no localStorage, sessionStorage, cookies, URL parameters, or other browser storage for themes. All styles share the same content, data, rankings, layout structure, and controls. The dropdown is keyboard accessible, themes also style the participant panel and error states, and system fonts keep the site self-contained.

## Data

Leaderboard data is read from CSV files stored in the repository using the naming convention:

```text
Participants_YYYYMMDD.csv
```

For example:

```text
Participants_20260912.csv
```

More precise timestamps are also supported:

```text
Participants_YYYYMMDD-HHMMSS.csv
```

When multiple files are present, the build script automatically selects the newest file based on the timestamp in the filename.

Required challenge columns beginning with `C#` are detected automatically. Optional bonus columns use the prefix `Bonus -`, for example `Bonus - Lab Presentation - 20 pts`; matching the bonus prefix ignores case. In both groups, numeric `1` means completed. Missing or malformed activity values mean incomplete. Counts and milestone indicators adapt to the number of columns, and older CSVs without bonus columns still work.

**Scores come directly from the CSV.** The application does not calculate participant scores, add bonus points, or rebuild percentages from completion flags. `Total Score` is displayed as supplied, and `Percentage` is converted from a fraction to a display percentage (`0.1` → 10%). `leaderboard.config.json` explicitly sets the score cap to **200**, including bonus activity.

The website shows required-task counts separately from score progress. Completed bonus work earns a small **★ Bonus completed** badge; the focus panel shows a separate **Bonus · Optional** section with completed/pending stars. Bonus activity names and point weights are not published in the JSON or shown in the interface. The latest included roster, `Participants_20260917.csv`, has 26 participants, five required tasks, and one bonus activity.

Rows with a missing, malformed, or out-of-range `Total Score` or `Percentage` are skipped with a build warning, so scores are never invented. Correct those fields in the CSV. If no valid participants remain, the build fails with an actionable error. See [INSTRUCTIONS.md](INSTRUCTIONS.md) for complete input and recovery rules.

## Run Locally

Requires Python 3.10+. No additional Python packages are required.

Clone the repository and run:

```bash
python scripts/dev.py
```

The script prepares the latest leaderboard data and starts a local web server.

Open the local URL printed in the terminal.

### Build Data Only

```bash
python scripts/prepare_data.py
```

This finds the newest participant CSV and generates the JSON used by the web application.

## Tests

Run the test suite with:

```bash
python -m unittest discover -s tests
```

Optional theme-controller regression tests use Node 18+ with no packages:

```bash
node --test tests/test_themes.cjs
```

Node is not required to build or serve the leaderboard.

## Updating the Leaderboard

1. Export or create the latest participant CSV.
2. Name it using the `Participants_YYYYMMDD.csv` convention.
3. Place it in the repository.
4. Commit and push the new file.

There is no need to modify the frontend when a newer CSV is added.

### Applying this update

Copy the extracted project contents into your existing repository, including `.github` and the updated `leaderboard.config.json`. This version includes **Course Challenge Leaderboard**, shared score ranks, the theme dropdown, and the new `site/themes.js` and `site/themes.css` files. Update the Python scripts and frontend together so the generated data includes the display-rank fields and the static validator includes the theme assets. Keep your newer CSVs if you have added any since this archive was prepared. Then run:

```bash
python -m unittest discover -s tests
python scripts/prepare_data.py
python scripts/validate_site.py
python scripts/dev.py
```

After checking the local page, commit and push the changed files to your default branch. The existing Pages workflow needs no changes. Generated `site/data/leaderboard.json` remains ignored by Git and is rebuilt automatically. The archive does not contain Git history.

## GitHub Pages

The repository includes a GitHub Actions workflow for GitHub Pages deployment.

For initial setup:

1. Open the repository on GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, select **GitHub Actions** as the source.
4. Push to the configured deployment branch.

The workflow prepares the latest leaderboard data, validates the project, and deploys the static site automatically.

## Project Structure

```text
.
├── Participants_YYYYMMDD.csv
├── README.md
├── LICENSE
├── scripts/
│   ├── prepare_data.py
│   └── dev.py
├── site/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   ├── themes.js
│   ├── themes.css
│   └── data/
│       └── leaderboard.json
├── tests/
└── .github/
    └── workflows/
        └── deploy-pages.yml
```

## Course

**ABE 205 — Computations for Engineering Systems**
Purdue University
Instructor: [Dr. Yaguang Zhang](https://yaguangzhang.github.io/)

## Development Note

This leaderboard application was developed with assistance from ChatGPT by OpenAI.

## License

Source code is available under the [MIT License](LICENSE).

Participant/course data contained in CSV files is not granted for reuse under the software license.
