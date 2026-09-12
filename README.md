# ABE 205 Course Challenge Leaderboard

An interactive, gamified leaderboard for **Purdue ABE 205: Computations for Engineering Systems**.

The site visualizes participant progress, completed challenges, rankings, and scores in a simple game-inspired interface.

## Features

* Ranked participant leaderboard
* Score and overall progress tracking
* Completed challenge indicators
* Participant search and focus view
* Responsive desktop and mobile design
* Automatic selection of the newest participant CSV
* Static GitHub Pages deployment
* No backend, database, or API keys required

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

Challenge columns beginning with `C#` are detected automatically. The application derives completed-task counts and available points from the CSV rather than requiring them to be hard-coded.

## Run Locally

Requires Python 3. No additional Python packages are required.

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

## Updating the Leaderboard

1. Export or create the latest participant CSV.
2. Name it using the `Participants_YYYYMMDD.csv` convention.
3. Place it in the repository.
4. Commit and push the new file.

There is no need to modify the frontend when a newer CSV is added.

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

## License

Source code is available under the [MIT License](LICENSE).

Participant/course data contained in CSV files is not granted for reuse under the software license.
