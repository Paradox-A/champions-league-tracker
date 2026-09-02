import json
import os
from datetime import datetime, timezone, date
from collections import defaultdict

API_TOKEN = os.environ.get("FOOTBALL_DATA_API_TOKEN")
STANDINGS_PATH = "standings.json"
MATCHES_PATH = "matches.json"
SCORERS_PATH = "scorers.json"
OUT_PATH = "index.html"

TOTAL_GAMES = 8  # each club plays 8 league-phase matches

standings_data = json.load(open(STANDINGS_PATH))
matches_data = json.load(open(MATCHES_PATH))

# football-data.org's /standings endpoint has two failure modes we've seen:
# (1) it silently falls back to the last completed season's final table when
#     the new season's fixtures haven't been loaded yet (detected below via
#     season endDate < today), or (2) once the new season IS loaded but zero
#     matches have been played, it 404s outright since there's no table to
#     compute yet. Handle (2) first: fall back to matches.json's season info
#     and render a minimal "not started" page instead of crashing on a
#     missing "standings" key.
NOT_STARTED = "standings" not in standings_data
if NOT_STARTED:
    m_season = matches_data["filters"]
    m_result = matches_data["resultSet"]
    season_label = f"{m_result['first'][:4]}-{m_result['last'][2:4]}"
    updated = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UEFA Champions League 2026-27 Tracker</title>
<style>
  :root {{ --bg: #f6f1e7; --card: #ffffff; --text: #1a1a1a; --muted: #6b6b6b; --border: #e2ddd0; --accent: #0a1a5c; --tab-bg: #eee6d6; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444; --accent: #8fa3f5; --tab-bg: #2a2534; }}
  }}
  :root[data-theme="dark"] {{ --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444; --accent: #8fa3f5; --tab-bg: #2a2534; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px 16px 60px; }}
  .wrap {{ max-width: 640px; margin: 60px auto; text-align: center; }}
  h1 {{ font-size: 1.6rem; color: var(--accent); }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }}
  .explainer {{ background: var(--tab-bg); border-radius: 8px; padding: 14px; font-size: 0.9rem; line-height: 1.6; }}
  .updated {{ color: var(--muted); font-size: 0.8rem; margin-top: 20px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>UEFA Champions League {season_label} Tracker</h1>
  <div class="card">
    <div class="explainer">
      Real {season_label} fixtures are loaded ({m_result['count']} league-phase matches, {m_result['first']} to {m_result['last']}), but no matches have been played yet, so the data source doesn't have a table to serve. This page will populate automatically with standings, stats, and races once the first matchday ({m_result['first']}) kicks off.
    </div>
  </div>
  <div class="updated">Last checked: {updated}</div>
</div>
</body>
</html>"""
    with open(OUT_PATH, "w") as f:
        f.write(html)
    print(f"Season loaded but not yet started (first match {m_result['first']}) — wrote placeholder page")
    raise SystemExit(0)

table = standings_data["standings"][0]["table"]
season = standings_data["season"]
matchday = season["currentMatchday"]
table = sorted(table, key=lambda t: (t["position"], -t["points"], -t["goalDifference"]))

# football-data.org's /standings endpoint silently falls back to the last
# season it has fixture data for when the current season hasn't been loaded
# yet (e.g. right after a league-phase draw, before the fixture list is
# published). Detect that case rather than presenting a past season as current.
season_end = date.fromisoformat(season["endDate"])
STALE_SEASON = season_end < date.today()
STALE_BANNER = ""
if STALE_SEASON:
    season_label = f"{season['startDate'][:4]}-{season['endDate'][2:4]}"
    STALE_BANNER = f"""
    <div class="explainer" style="background: var(--out); color: var(--out-text); font-weight: 600;">
      ⚠ The 2026-27 Champions League league phase hasn't started yet, and its fixtures aren't loaded into the free data source this tracker uses. Everything below is the final {season_label} table (last completed season), shown for reference only — not current results. This will update automatically once 2026-27 matches are fetched.
    </div>"""

finished = [m for m in matches_data["matches"] if m["status"] == "FINISHED"]

scorers_data = json.load(open(SCORERS_PATH))
scorers = scorers_data["scorers"]

def zone_for(pos):
    if pos <= 8:
        return ("ro16", "Round of 16 (direct)")
    if pos <= 24:
        return ("playoff", "Knockout Play-offs")
    return ("out", "Eliminated")

# ---------- League table rows ----------
rows_html = []
for t in table:
    pos = t["position"]
    zone_class, _ = zone_for(pos)
    played = t["playedGames"]
    pts = t["points"]
    gd = t["goalDifference"]
    gd_str = f"+{gd}" if gd > 0 else str(gd)
    form = t.get("form") or "—"
    rows_html.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{played}</td><td>{t['won']}</td><td>{t['draw']}</td><td>{t['lost']}</td>
      <td>{t['goalsFor']}</td><td>{t['goalsAgainst']}</td><td>{gd_str}</td>
      <td class="pts">{pts}</td><td class="form">{form}</td>
    </tr>""")

# ---------- Round of 16 Race (top of the table) ----------
ro16_zone = table[:12]
ro16_rows = []
eighth = table[7]["points"]
for t in ro16_zone:
    pos = t["position"]
    zone_class, zone_label = zone_for(pos)
    remaining = TOTAL_GAMES - t["playedGames"]
    gap = eighth - t["points"]
    if pos <= 8:
        gap_str = "—"
    else:
        gap_str = f"{gap} pt behind 8th (direct spot)" if gap > 0 else "Level with 8th"
    ro16_rows.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{zone_label}</td><td>{t['points']}</td><td>{remaining}</td>
      <td>{gap_str}</td>
    </tr>""")

# ---------- Play-off Battle (bubble around the 24th-place cutoff) ----------
bubble = [t for t in table if 17 <= t["position"] <= 30]
bubble_rows = []
twentyfourth = table[23]["points"]
for t in bubble:
    pos = t["position"]
    zone_class, zone_label = zone_for(pos)
    remaining = TOTAL_GAMES - t["playedGames"]
    gap = twentyfourth - t["points"]
    if pos <= 24:
        gap_str = f"{gap} pt clear of elimination" if gap > 0 else "On the elimination line"
    else:
        gap_str = f"{abs(gap)} pt behind 24th (play-off spot)" if gap > 0 else "Level with 24th"
    bubble_rows.append(f"""
    <tr class="{zone_class}">
      <td class="pos">{pos}</td>
      <td class="team"><img src="{t['team']['crest']}" alt="" class="crest"> {t['team']['shortName']}</td>
      <td>{zone_label}</td><td>{t['points']}</td><td>{remaining}</td>
      <td>{gap_str}</td>
    </tr>""")

# ---------- Club stats derived from finished matches ----------
club = defaultdict(lambda: {
    "name": None, "crest": None, "gf": 0, "ga": 0, "clean_sheets": 0, "failed_to_score": 0,
    "home_pts": 0, "home_played": 0, "away_pts": 0, "away_played": 0,
    "results": [],  # chronological list of 'W'/'D'/'L'
    "biggest_win": None, "heaviest_loss": None,
})

finished_sorted = sorted(finished, key=lambda m: m["utcDate"])
for m in finished_sorted:
    home = m["homeTeam"]; away = m["awayTeam"]
    hs = m["score"]["fullTime"]["home"]; as_ = m["score"]["fullTime"]["away"]
    for side, opp_side, gf, ga, is_home in [(home, away, hs, as_, True), (away, home, as_, hs, False)]:
        c = club[side["id"]]
        c["name"] = side["shortName"]; c["crest"] = side["crest"]
        c["gf"] += gf; c["ga"] += ga
        if ga == 0:
            c["clean_sheets"] += 1
        if gf == 0:
            c["failed_to_score"] += 1
        margin = gf - ga
        result = "W" if margin > 0 else ("D" if margin == 0 else "L")
        c["results"].append(result)
        pts = 3 if result == "W" else (1 if result == "D" else 0)
        if is_home:
            c["home_pts"] += pts; c["home_played"] += 1
        else:
            c["away_pts"] += pts; c["away_played"] += 1
        if result == "W":
            if c["biggest_win"] is None or margin > c["biggest_win"][0]:
                c["biggest_win"] = (margin, f"{gf}-{ga} vs {opp_side['shortName']}")
        if result == "L":
            deficit = ga - gf
            if c["heaviest_loss"] is None or deficit > c["heaviest_loss"][0]:
                c["heaviest_loss"] = (deficit, f"{gf}-{ga} vs {opp_side['shortName']}")

clean_sheet_rows = []
for cid, c in sorted(club.items(), key=lambda kv: (-kv[1]["clean_sheets"], kv[1]["ga"])):
    played = len(c["results"])
    if played == 0:
        continue
    clean_sheet_rows.append(f"""
    <tr>
      <td class="team"><img src="{c['crest']}" alt="" class="crest"> {c['name']}</td>
      <td>{played}</td><td>{c['clean_sheets']}</td>
      <td>{c['ga']/played:.2f}</td><td>{c['failed_to_score']}</td>
    </tr>""")

form_home_away_rows = []
for cid, c in sorted(club.items(), key=lambda kv: -( (kv[1]["home_pts"]+kv[1]["away_pts"]) )):
    played = len(c["results"])
    if played == 0:
        continue
    last5 = "".join(c["results"][-5:])
    home_ppg = (c["home_pts"]/c["home_played"]) if c["home_played"] else 0
    away_ppg = (c["away_pts"]/c["away_played"]) if c["away_played"] else 0
    form_home_away_rows.append(f"""
    <tr>
      <td class="team"><img src="{c['crest']}" alt="" class="crest"> {c['name']}</td>
      <td>{last5 or '—'}</td>
      <td>{c['home_pts']}pts / {c['home_played']}g ({home_ppg:.2f}/g)</td>
      <td>{c['away_pts']}pts / {c['away_played']}g ({away_ppg:.2f}/g)</td>
    </tr>""")

biggest_wins = sorted([ (c["biggest_win"][0], c["name"], c["biggest_win"][1]) for c in club.values() if c["biggest_win"]], reverse=True)[:5]
heaviest_losses = sorted([ (c["heaviest_loss"][0], c["name"], c["heaviest_loss"][1]) for c in club.values() if c["heaviest_loss"]], reverse=True)[:5]
biggest_win_rows = "".join(f"<tr><td>{name}</td><td>{detail}</td></tr>" for _, name, detail in biggest_wins) or "<tr><td colspan='2'>Not enough results yet</td></tr>"
heaviest_loss_rows = "".join(f"<tr><td>{name}</td><td>{detail}</td></tr>" for _, name, detail in heaviest_losses) or "<tr><td colspan='2'>Not enough results yet</td></tr>"

# ---------- Player stats from scorers ----------
def player_row(s, highlight_field):
    goals = s.get("goals") or 0
    assists_raw = s.get("assists")
    assists = assists_raw or 0
    pens_raw = s.get("penalties")
    pens = pens_raw or 0
    played = s.get("playedMatches") or 0
    involvements = goals + assists
    per_game = (goals/played) if played else 0
    cls = lambda f: "pts" if f == highlight_field else ""
    return f"""
    <tr>
      <td class="team"><img src="{s['team']['crest']}" alt="" class="crest"> {s['player']['name']}</td>
      <td>{s['team']['shortName']}</td>
      <td>{played}</td>
      <td class="{cls('goals')}">{goals}</td>
      <td class="{cls('assists')}">{assists if assists_raw is not None else '—'}</td>
      <td class="{cls('inv')}">{involvements}</td>
      <td>{pens if pens_raw is not None else '—'}</td>
      <td>{per_game:.2f}</td>
    </tr>"""

by_goals = sorted(scorers, key=lambda s: (-(s.get("goals") or 0), -(s.get("assists") or 0)))
by_assists = sorted(scorers, key=lambda s: (-(s.get("assists") or 0), -(s.get("goals") or 0)))
by_involvements = sorted(scorers, key=lambda s: (-((s.get("goals") or 0) + (s.get("assists") or 0))))

any_real_assists = any(s.get("assists") is not None for s in scorers)
assists_data_note = "" if any_real_assists else """<div class="note">⚠ The free data source used here doesn't track assists for the Champions League — every player shows "assists: none," so this list is really just sorted by goals as a fallback (same order as "Most Goals"). No confirmed free alternative source for Champions League assists has been found yet.</div>"""

goals_rows = "".join(player_row(s, "goals") for s in by_goals)
assists_rows = "".join(player_row(s, "assists") for s in by_assists)
involvements_rows = "".join(player_row(s, "inv") for s in by_involvements)

PLAYER_TABLE_HEAD = """<thead><tr><th class="team">Player</th><th>Club</th><th>Games</th><th>Goals</th><th>Assists</th><th>Goal Inv.</th><th>Pens</th><th>Goals/Game</th></tr></thead>"""

updated = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UEFA Champions League 2026-27 Tracker</title>
<style>
  :root {{
    --bg: #f6f1e7; --card: #ffffff; --text: #1a1a1a; --muted: #6b6b6b; --border: #e2ddd0;
    --ro16: #d6f5d6; --ro16-text: #1a6b1a; --playoff: #d6e8ff; --playoff-text: #1a4a8a;
    --out: #ffd6d6; --out-text: #8a1a1a;
    --accent: #0a1a5c; --tab-bg: #eee6d6; --tab-active: #0a1a5c; --tab-active-text: #ffffff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444;
      --ro16: #143d14; --ro16-text: #8fe08f; --playoff: #143355; --playoff-text: #9cc4f5;
      --out: #551a1a; --out-text: #f5a3a3;
      --accent: #8fa3f5; --tab-bg: #2a2534; --tab-active: #8fa3f5; --tab-active-text: #16131a;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #16131a; --card: #211d29; --text: #f0ede4; --muted: #a39d8f; --border: #3a3444;
    --ro16: #143d14; --ro16-text: #8fe08f; --playoff: #143355; --playoff-text: #9cc4f5;
    --out: #551a1a; --out-text: #f5a3a3;
    --accent: #8fa3f5; --tab-bg: #2a2534; --tab-active: #8fa3f5; --tab-active-text: #16131a;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px 16px 60px; }}
  .wrap {{ max-width: 940px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; color: var(--accent); }}
  .updated {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 18px; }}
  .dash-link {{ margin-bottom: 10px; }}
  .dash-link a {{ color: var(--muted); font-size: 0.8rem; text-decoration: none; }}
  .dash-link a:hover {{ text-decoration: underline; color: var(--accent); }}
  .tabs {{ display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }}
  .tab-btn {{
    background: var(--tab-bg); color: var(--text); border: none; border-radius: 8px;
    padding: 10px 16px; font-size: 0.9rem; font-weight: 600; cursor: pointer;
  }}
  .tab-btn.active {{ background: var(--tab-active); color: var(--tab-active-text); }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 20px; overflow-x: auto; }}
  h2 {{ font-size: 1.1rem; margin-top: 0; }}
  .intro {{ font-size: 0.88rem; color: var(--muted); margin-bottom: 16px; line-height: 1.5; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; white-space: nowrap; }}
  th, td {{ padding: 6px 8px; text-align: center; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; }}
  td.team, th.team {{ text-align: left; }}
  .crest {{ width: 16px; height: 16px; vertical-align: middle; margin-right: 6px; }}
  .pos {{ font-weight: 700; }} .pts {{ font-weight: 700; }}
  tr.ro16 {{ background: var(--ro16); color: var(--ro16-text); }}
  tr.playoff {{ background: var(--playoff); color: var(--playoff-text); }}
  tr.out {{ background: var(--out); color: var(--out-text); }}
  .legend {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.78rem; margin-top: 10px; color: var(--muted); }}
  .legend span {{ display: inline-flex; align-items: center; gap: 5px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
  .dot.ro16 {{ background: var(--ro16); }} .dot.playoff {{ background: var(--playoff); }}
  .dot.out {{ background: var(--out); }}
  .note {{ color: var(--muted); font-size: 0.8rem; margin-top: 8px; }}
  .explainer {{ background: var(--tab-bg); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem; color: var(--text); margin-bottom: 12px; line-height: 1.5; }}
  .explainer b {{ color: var(--accent); }}
  footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 30px; }}
  details.stat-accordion {{ border: 1px solid var(--border); border-radius: 10px; margin-bottom: 12px; overflow: hidden; }}
  details.stat-accordion summary {{
    cursor: pointer; padding: 14px 16px; font-weight: 700; font-size: 0.98rem;
    list-style: none; display: flex; justify-content: space-between; align-items: center;
    background: var(--card);
  }}
  details.stat-accordion summary::-webkit-details-marker {{ display: none; }}
  details.stat-accordion summary::after {{ content: "+"; font-size: 1.2rem; color: var(--muted); }}
  details.stat-accordion[open] summary::after {{ content: "−"; }}
  details.stat-accordion summary .sub {{ font-weight: 400; font-size: 0.78rem; color: var(--muted); margin-top: 2px; display: block; }}
  details.stat-accordion .accordion-body {{ padding: 0 16px 16px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="dash-link"><a href="https://paradox-a.github.io/football-dashboard/">&larr; All Trackers (Dashboard)</a></div>
  <h1>UEFA Champions League 2026-27 Tracker</h1>
  <div class="updated">{'Season not yet started' if STALE_SEASON else f'Matchday {matchday}'} · Last updated {updated}</div>
  {STALE_BANNER}

  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('table')">League Table</button>
    <button class="tab-btn" onclick="showTab('club')">Club Stats</button>
    <button class="tab-btn" onclick="showTab('player')">Player Stats</button>
  </div>

  <div id="tab-table" class="tab-panel active">
    <div class="explainer">
      <b>New to the Champions League's format?</b> Since 2024-25, there's no more group stage. All 36 clubs sit in a single <b>league phase</b> table, each playing 8 different opponents (4 home, 4 away). The <b>top 8</b> go straight through to the Round of 16. Clubs finishing <b>9th-24th</b> enter a two-legged knockout <b>play-off round</b> for the remaining 8 Round of 16 spots. Clubs finishing <b>25th-36th</b> are eliminated. This table only covers the league phase (roughly August-January) — once the knockout rounds begin, results become two-legged ties rather than table positions.
    </div>
    <div class="card">
      <h2>League Phase Table</h2>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th><th>Form</th></tr></thead>
        <tbody>{"".join(rows_html)}</tbody>
      </table>
      <div class="note"><b>P</b> Played &nbsp;·&nbsp; <b>W</b> Won &nbsp;·&nbsp; <b>D</b> Drawn &nbsp;·&nbsp; <b>L</b> Lost &nbsp;·&nbsp; <b>GF</b> Goals For &nbsp;·&nbsp; <b>GA</b> Goals Against &nbsp;·&nbsp; <b>GD</b> Goal Difference (GF minus GA — the first tiebreaker when teams are level on points) &nbsp;·&nbsp; <b>Pts</b> Points (3 for a win, 1 for a draw, 0 for a loss) &nbsp;·&nbsp; <b>Form</b> results of the last 5 games, oldest to newest</div>
      <div class="legend">
        <span><span class="dot ro16"></span>Round of 16, direct (1-8)</span>
        <span><span class="dot playoff"></span>Knockout Play-offs (9-24)</span>
        <span><span class="dot out"></span>Eliminated (25-36)</span>
      </div>
    </div>

    <div class="card">
      <h2>Round of 16 Race</h2>
      <div class="explainer">Finishing in the <b>top 8</b> means a bye straight to the Round of 16 — no extra games needed. Everyone else in this list is still chasing that direct spot, shown by how many points behind 8th place they are.</div>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>Zone</th><th>Pts</th><th>Games Left</th><th>Gap</th></tr></thead>
        <tbody>{"".join(ro16_rows)}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Play-off Battle</h2>
      <div class="explainer">The bubble around the <b>24th-place cutoff</b> — the line between qualifying for the knockout play-off round and being eliminated from Europe entirely for the season.</div>
      <table>
        <thead><tr><th>#</th><th class="team">Team</th><th>Zone</th><th>Pts</th><th>Games Left</th><th>Gap</th></tr></thead>
        <tbody>{"".join(bubble_rows)}</tbody>
      </table>
    </div>
  </div>

  <div id="tab-club" class="tab-panel">
    {STALE_BANNER}
    <div class="explainer">
      <b>New to the Champions League?</b> The table tells you <i>where</i> a team stands, but not <i>how</i> they got there. These stats show the underlying strengths and weaknesses — a team can have a good record while quietly being fragile defensively, or vice versa.
    </div>

    <div class="card">
      <h2>Defensive Strength: Clean Sheets</h2>
      <div class="explainer">A <b>clean sheet</b> is a game where a team doesn't concede at all. It's the single clearest sign of defensive solidity, and it matters even more in a knockout competition where a single bad night can end a season.</div>
      <table>
        <thead><tr><th class="team">Team</th><th>Played</th><th>Clean Sheets</th><th>Goals Conceded / Game</th><th>Failed to Score</th></tr></thead>
        <tbody>{"".join(clean_sheet_rows) or "<tr><td colspan=5>No finished matches yet</td></tr>"}</tbody>
      </table>
      <div class="note"><b>Failed to Score</b> counts games where a team didn't score at all — a blunt but telling sign of attacking struggles.</div>
    </div>

    <div class="card">
      <h2>Home Fortress vs. Road Warriors</h2>
      <div class="explainer">Some teams are much stronger at home than away (or the reverse) — this is one of the oldest storylines in football. <b>Points per game (PPG)</b> at home vs. away shows exactly how lopsided that split is. <b>Form</b> is the last 5 results (most recent last) — a better read on momentum than the season-long record.</div>
      <table>
        <thead><tr><th class="team">Team</th><th>Form (last 5)</th><th>Home Record</th><th>Away Record</th></tr></thead>
        <tbody>{"".join(form_home_away_rows) or "<tr><td colspan=4>No finished matches yet</td></tr>"}</tbody>
      </table>
    </div>

    <div class="card">
      <h2>Biggest Wins &amp; Heaviest Losses</h2>
      <div class="explainer">Goal margin matters beyond the 3 points — a big win boosts goal difference (which breaks ties in the table) and can be a statement result against a fellow European heavyweight.</div>
      <div style="display:flex; gap:16px; flex-wrap:wrap;">
        <table style="flex:1; min-width:220px;">
          <thead><tr><th class="team">Team</th><th>Biggest Win</th></tr></thead>
          <tbody>{biggest_win_rows}</tbody>
        </table>
        <table style="flex:1; min-width:220px;">
          <thead><tr><th class="team">Team</th><th>Heaviest Loss</th></tr></thead>
          <tbody>{heaviest_loss_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="note" style="margin-top: -8px;">Not shown: possession, shots, passing accuracy, tackles, or expected goals (xG) — these require a paid data source. Everything above is derived directly from final match scores.</div>
  </div>

  <div id="tab-player" class="tab-panel">
    {STALE_BANNER}
    <div class="explainer">
      <b>New to the Champions League?</b> There's no single official "Golden Boot" title here the way there is domestically, but the top scorer race is still closely watched. Goals alone don't capture everything a player contributes, though — this table adds context.
    </div>
    <div class="card">
      <h2>Top Scorer Race &amp; Goal Involvements</h2>
      <div class="explainer">
        <b>Goals</b>: the headline number.<br>
        <b>Assists</b>: the pass that directly leads to a goal — a measure of creativity, not just finishing.<br>
        <b>Goal Involvements</b> (goals + assists): a fuller picture of a player's attacking output — a player with 8 goals and 10 assists is arguably more valuable than one with 12 goals and 0 assists.<br>
        <b>Goals/Game</b>: raw totals favor players who've played more games — this rate stat levels the comparison.<br>
        <b>Penalties</b>: shown separately since penalty goals are viewed differently from open-play goals (some fans discount them when judging a striker's true quality).
      </div>
      <table>{PLAYER_TABLE_HEAD}<tbody>{goals_rows or "<tr><td colspan=8>No scorer data yet</td></tr>"}</tbody></table>
      <div class="note">Not shown: shots, expected goals (xG), key passes, dribbles, tackles, or cards — the free data source used here only tracks goals, assists, penalties, and appearances. No working free source for Champions League cards or individual clean sheets has been found yet, so those sections aren't included here.</div>
    </div>

    <div class="explainer" style="margin-top: 4px;">
      <b>Want just one ranking at a time?</b> The sections below break the same data out individually, sorted by each specific stat.
    </div>

    <details class="stat-accordion">
      <summary>Most Goals <span class="sub">Decided by goals alone, nothing else</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Goals</b> is the headline number. It rewards finishers over creators — see "Most Goals & Assists" below for the fuller picture.</div>
        <table>{PLAYER_TABLE_HEAD}<tbody>{goals_rows or "<tr><td colspan=8>No scorer data yet</td></tr>"}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Assists <span class="sub">Who's creating goals for others, not just scoring them</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Assists</b> credit the pass (or occasionally the touch) that directly leads to a goal. It's the clearest single measure of creativity — a player can be hugely valuable to a team's attack without scoring much themselves.</div>
        {assists_data_note}
        <table>{PLAYER_TABLE_HEAD}<tbody>{assists_rows or "<tr><td colspan=8>No assist data yet</td></tr>"}</tbody></table>
      </div>
    </details>

    <details class="stat-accordion">
      <summary>Most Goals &amp; Assists <span class="sub">Total attacking output — often a better "who's actually best" ranking than goals alone</span></summary>
      <div class="accordion-body">
        <div class="explainer"><b>Goal Involvements</b> (goals + assists) gives a fuller picture of a player's attacking output than the top-scorer table does on its own. A player with 8 goals and 10 assists has been directly involved in 18 goals — arguably more valuable to their team than someone with 12 goals and 0 assists, even though the latter would top the pure scoring chart.</div>
        <table>{PLAYER_TABLE_HEAD}<tbody>{involvements_rows or "<tr><td colspan=8>No data yet</td></tr>"}</tbody></table>
      </div>
    </details>

    <div class="note">Also shown in each table: <b>Penalties</b> (shown separately since penalty goals are viewed differently from open-play ones), and <b>Goals/Game</b> (a rate stat, since raw totals favor players who've played more games).</div>
  </div>

  <footer>Data: football-data.org · Rebuilt periodically, not live-updating</footer>
</div>
<script>
function showTab(name) {{
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
</script>
</body>
</html>
"""

with open(OUT_PATH, "w") as f:
    f.write(html)
print("wrote", OUT_PATH, len(html), "bytes")
