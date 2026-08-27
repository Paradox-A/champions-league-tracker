# UEFA Champions League 2026-27 Tracker

A static tracker for the Champions League, mirroring the domestic-league trackers but adapted for the competition's single league-phase format (adopted 2024-25), with three tabs:
- **League Table**: full 36-team league-phase standings, color-coded by qualification zone (Round of 16, direct — positions 1-8), knockout play-off zone (9-24), and eliminated (25-36), plus a "Round of 16 Race" view of the top of the table and a "Play-off Battle" view of the bubble around the 24th-place cutoff.
- **Club Stats**: clean sheets, home/away form splits, biggest wins & heaviest losses — all derived from match results.
- **Player Stats**: top scorer race, plus expandable lists for Most Goals, Most Assists, and Most Goals & Assists.

## Data source
[football-data.org](https://www.football-data.org/) free API (Champions League competition code `CL`) — standings, matches, goals/penalties.

No known free source for Champions League cards or individual goalkeeper clean sheets has been found (unlike the Premier League tracker's pulselive source or the LaLiga tracker's site-scrape), and assists aren't reliably populated by football-data.org for this competition either — the "Most Assists" list falls back to goal-sorted order when that's the case, flagged in the page itself.

**Format note:** this only covers the league phase (August-January), where every team's record is a normal table row. Once the competition moves into the knockout rounds (play-offs, Round of 16, quarter-finals, etc. from February on), results become two-legged head-to-head ties rather than table positions, which this tracker doesn't attempt to visualize — the league-phase table simply freezes at its final standings.

## Regenerating

```bash
export FOOTBALL_DATA_API_TOKEN=your_token_here
./fetch_data.sh
git add index.html
git commit -m "Refresh standings"
git push
```

Not live-updating — rebuild after each matchday (or whenever) to refresh the table.
