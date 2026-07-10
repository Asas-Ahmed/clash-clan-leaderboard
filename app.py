from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------
# Configuration
# --------------------------------------------------

SHEET_URL = st.secrets["SHEET_URL"]

RUSH_WEIGHT = 0.30
CWL_WEIGHT = 0.25
WAR_WEIGHT = 0.20
CAPITAL_WEIGHT = 0.15
GAMES_WEIGHT = 0.10

RUSH_EVENT_ENABLED = False

WAR_STARS_PER_PARTICIPATION = 6
CWL_STARS_PER_ATTACK = 3

CAPITAL_GOLD_TARGET = 100_000
CLAN_GAMES_TARGET = 10_000

CWL_EFFICIENCY_WEIGHT = 0.70
CWL_PARTICIPATION_WEIGHT = 0.30

REQUIRED_COLUMNS = [
    "Name",
    "War_Attempts",
    "War_Stars",
    "CWL_Attempts",
    "CWL_Stars",
    "ClanCapital_Gold",
    "ClanGames_Points",
    "RushEvents_Participation_pct",
]
NUMERIC_COLUMNS = REQUIRED_COLUMNS[1:]

st.set_page_config(
    page_title="ClashIntel ⚔️",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------
# Streamlit shell styling
# --------------------------------------------------

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 50% -10%, rgba(41, 121, 255, 0.16), transparent 34rem),
            radial-gradient(circle at 95% 5%, rgba(139, 92, 246, 0.12), transparent 28rem),
            #05070d;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMainBlockContainer"] {
        max-width: 1540px;
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }
    [data-testid="stToolbar"] { right: 1rem; }

    .app-hero {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: .65rem;
    }
    .app-kicker {
        color: #5ee7ff;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: .35rem;
    }
    .app-title {
        color: #f8fafc;
        font-size: clamp(1.85rem, 4vw, 3rem);
        font-weight: 800;
        letter-spacing: -.045em;
        line-height: 1.05;
        margin: 0;
    }
    .app-subtitle {
        color: #94a3b8;
        font-size: .93rem;
        margin: .65rem 0 0;
    }
    .weight-strip {
        display: flex;
        flex-wrap: wrap;
        gap: .5rem;
        margin: .9rem 0 1.15rem;
    }
    .weight-chip {
        border: 1px solid rgba(148,163,184,.15);
        background: rgba(15,23,42,.68);
        color: #cbd5e1;
        border-radius: 999px;
        padding: .42rem .7rem;
        font-size: .72rem;
        font-weight: 700;
        backdrop-filter: blur(12px);
    }
    div[data-testid="stButton"] > button {
        border-radius: 12px;
        border: 1px solid rgba(94,231,255,.24);
        background: rgba(15,23,42,.72);
        color: #e2e8f0;
        font-weight: 700;
        min-height: 2.65rem;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: rgba(94,231,255,.55);
        color: white;
        background: rgba(30,41,59,.9);
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: .75rem;
            padding-right: .75rem;
            padding-top: 1rem;
        }
        .app-subtitle { font-size: .82rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Data loading and validation
# --------------------------------------------------


@st.cache_data(ttl=60, show_spinner="Loading clan performance data…")
def load_player_data() -> pd.DataFrame:
    try:
        df = pd.read_excel(SHEET_URL)
    except Exception as error:
        raise RuntimeError(f"Failed to load the Google Sheet: {error}") from error

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Missing required spreadsheet columns: " + ", ".join(missing_columns)
        )

    df = df[REQUIRED_COLUMNS].copy()
    df["Name"] = df["Name"].fillna("Unknown").astype(str).str.strip()
    df.loc[df["Name"].eq(""), "Name"] = "Unknown"

    for column in NUMERIC_COLUMNS:
        df[column] = (
            pd.to_numeric(df[column], errors="coerce")
            .fillna(0)
            .clip(lower=0)
        )

    df["RushEvents_Participation_pct"] = df[
        "RushEvents_Participation_pct"
    ].clip(0, 100)

    return df


# --------------------------------------------------
# Score calculations — synchronized with RANK(2).py
# --------------------------------------------------


def safe_ratio(
    numerator: pd.Series, denominator: pd.Series | float
) -> pd.Series:
    if isinstance(denominator, pd.Series):
        result = np.divide(
            numerator,
            denominator,
            out=np.zeros(len(numerator), dtype=float),
            where=denominator.to_numpy() > 0,
        )
        return pd.Series(result, index=numerator.index).clip(0, 1)

    if denominator <= 0:
        return pd.Series(0.0, index=numerator.index)

    return (numerator / denominator).clip(0, 1)


def contribution_score(values: pd.Series, target: float) -> pd.Series:
    return np.sqrt(safe_ratio(values, target)).clip(0, 1)


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    max_cwl_attacks = max(float(df["CWL_Attempts"].max()), 1.0)

    war_possible_stars = df["War_Attempts"] * WAR_STARS_PER_PARTICIPATION
    df["War_Efficiency"] = safe_ratio(df["War_Stars"], war_possible_stars)
    df["War_Score"] = np.where(
        df["War_Attempts"] > 0,
        df["War_Efficiency"],
        0,
    )

    cwl_possible_stars = df["CWL_Attempts"] * CWL_STARS_PER_ATTACK
    df["CWL_Efficiency"] = safe_ratio(df["CWL_Stars"], cwl_possible_stars)
    df["CWL_Participation"] = safe_ratio(df["CWL_Attempts"], max_cwl_attacks)
    df["CWL_Score"] = np.where(
        df["CWL_Attempts"] > 0,
        (
            df["CWL_Efficiency"] * CWL_EFFICIENCY_WEIGHT
            + df["CWL_Participation"] * CWL_PARTICIPATION_WEIGHT
        ),
        0,
    )

    df["Capital_Score"] = contribution_score(
        df["ClanCapital_Gold"], CAPITAL_GOLD_TARGET
    )
    df["Games_Score"] = contribution_score(
        df["ClanGames_Points"], CLAN_GAMES_TARGET
    )
    df["Rush_Score"] = df["RushEvents_Participation_pct"] / 100

    if RUSH_EVENT_ENABLED:
        weights = {
            "Rush": RUSH_WEIGHT,
            "CWL": CWL_WEIGHT,
            "War": WAR_WEIGHT,
            "Capital": CAPITAL_WEIGHT,
            "Games": GAMES_WEIGHT,
        }
    else:
        total = CWL_WEIGHT + WAR_WEIGHT + CAPITAL_WEIGHT + GAMES_WEIGHT
    
        weights = {
            "Rush": 0.0,
            "CWL": CWL_WEIGHT / total,
            "War": WAR_WEIGHT / total,
            "Capital": CAPITAL_WEIGHT / total,
            "Games": GAMES_WEIGHT / total,
        }
    
    df["FinalScore"] = (
        df["Rush_Score"] * weights["Rush"]
        + df["CWL_Score"] * weights["CWL"]
        + df["War_Score"] * weights["War"]
        + df["Capital_Score"] * weights["Capital"]
        + df["Games_Score"] * weights["Games"]
    ) * 100

    df["War_Skill_Score"] = df["War_Score"] * 100
    df["CWL_Skill_Score"] = df["CWL_Score"] * 100
    df["Capital_Display_Score"] = df["Capital_Score"] * 100
    df["Games_Display_Score"] = df["Games_Score"] * 100

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    df["FinalScore"] = df["FinalScore"].clip(0, 100)

    df = df.sort_values(
        by=[
            "FinalScore",
            "Rush_Score",
            "CWL_Score",
            "War_Score",
            "Capital_Score",
            "Games_Score",
            "Name",
        ],
        ascending=[False, False, False, False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    df["Rank"] = np.arange(1, len(df) + 1)
    return df


# --------------------------------------------------
# Header and refresh action
# --------------------------------------------------

header_col, action_col = st.columns([5, 1], vertical_alignment="bottom")
with header_col:
    st.markdown(
        """
        <div class="app-hero">
            <div>
                <div class="app-kicker">ClashIntel Performance System</div>
                <h1 class="app-title">🏆 Top Clan Players</h1>
                <p class="app-subtitle">A contribution-first leaderboard combining rush, CWL, war, capital and clan games performance.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with action_col:
    if st.button("↻ Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    raw_data = load_player_data()
except (RuntimeError, ValueError) as error:
    st.error(str(error))
    st.stop()

if raw_data.empty:
    st.warning("The leaderboard is empty. Check the Google Sheet data.")
    st.stop()

scores = compute_scores(raw_data)

# --------------------------------------------------
# Responsive leaderboard component
# --------------------------------------------------

html_parts = [
    """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {
    color-scheme: dark;
    --surface: rgba(15, 23, 42, .72);
    --surface-hover: rgba(22, 32, 54, .9);
    --border: rgba(148, 163, 184, .14);
    --text: #f1f5f9;
    --muted: #94a3b8;
    --cyan: #5ee7ff;
}
* { box-sizing: border-box; }
html, body {
    width: 100%;
    min-height: 100%;
    margin: 0;
    overflow-x: hidden;
    overflow-y: auto;
    background: transparent;
    color: var(--text);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.leaderboard {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
    padding: 2px 2px 18px;
}
.player-row {
    position: relative;
    display: grid;
    grid-template-columns: 52px minmax(145px, 1.18fr) repeat(5, minmax(118px, 1fr)) 112px;
    gap: 12px;
    align-items: center;
    min-width: 0;
    padding: 15px 16px;
    border: 1px solid var(--border);
    border-radius: 18px;
    background:
        linear-gradient(145deg, rgba(255,255,255,.045), rgba(255,255,255,.012)),
        var(--surface);
    box-shadow: 0 10px 30px rgba(0, 0, 0, .18);
    backdrop-filter: blur(16px);
    transition: transform .2s ease, border-color .2s ease, background .2s ease, box-shadow .2s ease;
}
.player-row::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    border-radius: 18px 0 0 18px;
    background: linear-gradient(#5ee7ff, #8b5cf6);
    opacity: .55;
}
.player-row:hover {
    transform: translateY(-2px);
    border-color: rgba(94, 231, 255, .34);
    background: var(--surface-hover);
    box-shadow: 0 18px 42px rgba(0, 0, 0, .28);
}
.rank-badge {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 13px;
    background: rgba(255,255,255,.06);
    color: var(--muted);
    font-weight: 800;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
}
.rank-badge.gold { background: linear-gradient(135deg, #ffe26f, #ffb300); color: #171000; }
.rank-badge.silver { background: linear-gradient(135deg, #f1f5f9, #94a3b8); color: #111827; }
.rank-badge.bronze { background: linear-gradient(135deg, #e6a46d, #9a5727); color: #fff; }
.player-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
    font-size: clamp(.94rem, 1.2vw, 1.08rem);
    font-weight: 800;
    letter-spacing: -.015em;
}
.stats-bar-wrapper { min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.stats-label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    min-width: 0;
    color: var(--muted);
    font-size: .66rem;
    font-weight: 800;
    letter-spacing: .075em;
    text-transform: uppercase;
    white-space: nowrap;
}
.stat-value {
    overflow: hidden;
    color: #e2e8f0;
    font-size: .68rem;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0;
    text-overflow: ellipsis;
}
.stats-bar-container {
    width: 100%;
    height: 9px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,.025);
    border-radius: 999px;
    background: rgba(255,255,255,.07);
}
.stats-bar { height: 100%; border-radius: inherit; box-shadow: 0 0 14px currentColor; }
.war { background: linear-gradient(90deg, #ff713d, #ffad42); color: #ff8c3d; }
.cwl { background: linear-gradient(90deg, #a855f7, #6366f1); color: #8b5cf6; }
.capital { background: linear-gradient(90deg, #eab308, #fde68a); color: #eab308; }
.games { background: linear-gradient(90deg, #3b82f6, #22d3ee); color: #22d3ee; }
.rush { background: linear-gradient(90deg, #22c55e, #2dd4bf); color: #2dd4bf; }
.final-score {
    min-width: 0;
    padding: 11px 8px;
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 13px;
    text-align: center;
    font-size: clamp(.95rem, 1.3vw, 1.12rem);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
    letter-spacing: -.01em;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.12);
}
.score-gold { background: linear-gradient(135deg, #ffe56f, #ffb300); color: #161000; }
.score-purple { background: linear-gradient(135deg, #9333ea, #4f46e5); color: white; }
.score-blue { background: linear-gradient(135deg, #0891b2, #2563eb); color: white; }
.score-green { background: linear-gradient(135deg, #16a34a, #0d9488); color: white; }
.score-red { background: linear-gradient(135deg, #b91c1c, #ea580c); color: white; }

@media (max-width: 1260px) {
    .player-row {
        grid-template-columns: 50px 1fr 112px;
        grid-template-areas:
            "rank name score"
            "war war war"
            "cwl cwl cwl"
            "capital games rush";
        gap: 12px 14px;
        padding: 16px 17px;
    }
    .rank-badge { grid-area: rank; }
    .player-name { grid-area: name; }
    .final-score { grid-area: score; }
    .stat-war { grid-area: war; }
    .stat-cwl { grid-area: cwl; }
    .stat-capital { grid-area: capital; }
    .stat-games { grid-area: games; }
    .stat-rush { grid-area: rush; }
}
@media (max-width: 620px) {
    .leaderboard { gap: 10px; }
    .player-row {
        grid-template-columns: 46px minmax(0, 1fr) 96px;
        grid-template-areas:
            "rank name score"
            "war war war"
            "cwl cwl cwl"
            "capital capital capital"
            "games games games"
            "rush rush rush";
        padding: 13px 12px;
        border-radius: 16px;
    }
    .rank-badge { width: 40px; height: 40px; border-radius: 12px; }
    .player-name { font-size: .93rem; }
    .final-score { padding: 10px 5px; font-size: .9rem; }
    .stats-label { font-size: .63rem; }
}
@media (prefers-reduced-motion: reduce) {
    .player-row { transition: none; }
    .player-row:hover { transform: none; }
}
</style>
</head>
<body>
<div class="leaderboard" id="leaderboard">
"""
]

for row in scores.itertuples(index=False):
    rank = int(row.Rank)
    badge_class = "rank-badge"
    if rank == 1:
        badge_class += " gold"
    elif rank == 2:
        badge_class += " silver"
    elif rank == 3:
        badge_class += " bronze"

    if row.FinalScore >= 85:
        score_class = "score-gold"
    elif row.FinalScore >= 70:
        score_class = "score-purple"
    elif row.FinalScore >= 55:
        score_class = "score-blue"
    elif row.FinalScore >= 40:
        score_class = "score-green"
    else:
        score_class = "score-red"

    rank_text = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
    player_name = escape(str(row.Name))

    html_parts.append(
        f"""
<div class="player-row">
    <div class="{badge_class}" title="Rank {rank}">{rank_text}</div>
    <div class="player-name" title="{player_name}">{player_name}</div>

    <div class="stats-bar-wrapper stat-war">
        <div class="stats-label">
            <span>⚔️ War</span>
            <span class="stat-value">{int(row.War_Stars)}⭐ / {int(row.War_Attempts)} wars · {row.War_Skill_Score:.1f}</span>
        </div>
        <div class="stats-bar-container" title="War category score: {row.War_Skill_Score:.2f}/100">
            <div class="stats-bar war" style="width:{row.War_Skill_Score:.2f}%"></div>
        </div>
    </div>

    <div class="stats-bar-wrapper stat-cwl">
        <div class="stats-label">
            <span>🛡️ CWL</span>
            <span class="stat-value">{int(row.CWL_Stars)}⭐ / {int(row.CWL_Attempts)} attacks · {row.CWL_Skill_Score:.1f}</span>
        </div>
        <div class="stats-bar-container" title="CWL category score: {row.CWL_Skill_Score:.2f}/100">
            <div class="stats-bar cwl" style="width:{row.CWL_Skill_Score:.2f}%"></div>
        </div>
    </div>

    <div class="stats-bar-wrapper stat-capital">
        <div class="stats-label">
            <span>🏰 Capital</span>
            <span class="stat-value">{int(row.ClanCapital_Gold):,} · {row.Capital_Display_Score:.1f}</span>
        </div>
        <div class="stats-bar-container" title="Capital score against the 100,000 target: {row.Capital_Display_Score:.2f}/100">
            <div class="stats-bar capital" style="width:{row.Capital_Display_Score:.2f}%"></div>
        </div>
    </div>

    <div class="stats-bar-wrapper stat-games">
        <div class="stats-label">
            <span>🎮 Games</span>
            <span class="stat-value">{int(row.ClanGames_Points):,} · {row.Games_Display_Score:.1f}</span>
        </div>
        <div class="stats-bar-container" title="Clan Games score against the 10,000 target: {row.Games_Display_Score:.2f}/100">
            <div class="stats-bar games" style="width:{row.Games_Display_Score:.2f}%"></div>
        </div>
    </div>

    <div class="stats-bar-wrapper stat-rush">
        <div class="stats-label">
            <span>🔥 Rush</span>
            <span class="stat-value">{row.RushEvents_Participation_pct:.0f}%</span>
        </div>
        <div class="stats-bar-container" title="Rush participation: {row.RushEvents_Participation_pct:.0f}%">
            <div class="stats-bar rush" style="width:{row.RushEvents_Participation_pct:.2f}%"></div>
        </div>
    </div>

    <div class="final-score {score_class}" title="Final weighted score">⭐ {row.FinalScore:.2f}</div>
</div>
"""
    )

html_parts.append(
    """
</div>
</body>
</html>
"""
)

# A fixed viewport with iframe scrolling is more reliable than attempting to
# resize the component through Streamlit's private postMessage protocol.
# The leaderboard remains responsive inside this viewport on desktop, tablet,
# and mobile screens.
leaderboard_height = min(max(720, len(scores) * 112), 1200)
components.html(
    "".join(html_parts),
    height=leaderboard_height,
    scrolling=True,
)
