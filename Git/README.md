# Odibets Odileague Scraper

Automated scraper for Odibets Odileague that extracts goal markets, tracks live matches, and collects results/standings.

## Features

- **Goal Markets Extraction**: Scrapes all goal-related markets (OV/UN, GG/NG, Total Goals, etc.)
- **Timer Monitoring**: Tracks pre-match countdown for selected timestamp
- **Live Match Tracking**: Detects goals and score changes in real-time
- **Results & Standings**: Collects match results and league standings

## GitHub Actions Automation

This scraper runs automatically on GitHub Actions at scheduled times:

- Daily at 10:00, 14:00, and 18:00 UTC
- Can also be triggered manually from the Actions tab

## Output Data

All scraped data is saved in the `odibets_scraped_data` directory:

- `goal_markets_*.json` - Goal market odds
- `live_tracking_*.json` - Live match events and goals
- `results_*.json` - Match results by week
- `standings_*.json` - League standings with team form
- `execution_summary_*.json` - Summary of each run

## Manual Trigger

1. Go to the Actions tab in your GitHub repository
2. Select "Odibets Integrated Scraper"
3. Click "Run workflow"
4. Choose scraping mode:
   - `full` - Complete workflow (goals → timer → live → results)
   - `goals_only` - Only scrape goal markets
   - `live_only` - Only monitor timer and track live matches
   - `results_only` - Only scrape results and standings

## Data Retention

Scraped data artifacts are retained for 30 days on GitHub Actions.