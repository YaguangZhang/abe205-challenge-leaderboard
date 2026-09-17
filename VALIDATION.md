# Delivery validation

## Checks completed

- **25 standard-library unit tests passed.** Fixtures are isolated from the live roster and cover timestamp selection, Unicode/CSV quoting, dynamic task schemas, weighted totals, percentages, ranking, bad inputs, fallback weights, and public-data minimization.
- **Updated ranking verified:** all-task finishers precede unfinished participants; valid completion times sort earliest first; missing or malformed finish times follow known times within the finisher group. Unfinished participants ignore completion times and use score, task count, and name. Tied finish times use names, not scores. Completion status comes from task flags, and completion timestamps remain absent from public JSON.
- **Supplied input verified:** 25 participants, five tasks, 200 available points. Quinn Phelan ranks first with 20 points, two completed tasks, and 10% progress; Harold ranks second. Aarón's Unicode name is preserved.
- **Static build passed:** `prepare_data.py` and `validate_site.py` generated and checked the current snapshot and its assets.
- **JavaScript syntax passed:** `node --check site/app.js`. Node is a delivery check only, not a project dependency.
- **Local server smoke check passed:** `dev.py --port 0` generated the roster, printed its URL, and served HTML, CSS, JavaScript, SVG, and JSON with HTTP 200 and appropriate content types. The source CSV, scripts, and README returned 404 from the public site server.
- **Source reviewed against the brief:** relative asset/data paths; default-branch Pages deployment; no browser directory discovery; safe text rendering; search/reset; native keyboard-accessible dialog; persistent selection highlight; dynamic milestones; responsive card rules; reduced-motion styles; loading, empty-search, and error states.

## Verification still required

Browser interaction and visual QA could not run in the delivery environment. The remote browser could not reach the local server, and no local browser executable was installed. Desktop/mobile rendering, screen-reader behavior, reduced motion, and touch interactions are implemented but **not browser-verified**.

No GitHub repository was connected or published during delivery. The Actions workflow is included and uses official Pages actions, but a live GitHub deployment has **not been executed**. Follow the one-time setup in README.md and inspect the first successful workflow.

Before publishing, run the README's manual UI check on desktop and mobile. In particular, verify search and reset, opening/closing the focus panel with a keyboard, changing participants, correct milestone states, and no horizontal scrolling at narrow widths.
