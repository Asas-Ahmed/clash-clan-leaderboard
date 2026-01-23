import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
from datetime import datetime
import pytz

# --- Get the current time for Sri Lanka ---
sl_tz = pytz.timezone('Asia/Colombo')
current_time = datetime.now(sl_tz).strftime('%I:%M:%S %p')

 # --- Display the Static Status Card ---
st.sidebar.markdown(f"""
    <style>
    .status-card {{
        background-color: #161b22;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #30363d;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    .time-val {{
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .status-dot {{
        height: 8px;
        width: 8px;
        background-color: #238636;
        border-radius: 50%;
        box-shadow: 0 0 5px #238636;
    }}
    </style>
    
    <div class="status-card">
        <div style="color: #8b949e; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
            System Heartbeat
        </div>
        <div class="time-val">
            <span class="status-dot"></span>
            {current_time}
        </div>
        <div style="color: #484f58; font-size: 9px; margin-top: 4px;">
            GMT+5:30 • Colombo, SL
        </div>
    </div>
""", unsafe_allow_html=True)

# --- Google Sheet URL ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/118gjjn-oFYt4-hy8HVxius8LzeMA6V0SGVI_Mto5Heg/export?format=xlsx"

# --- Streamlit global dark config ---
st.set_page_config(
    page_title="ClashIntel",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #0b1020, #05070d 60%);
}
[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# --- Load data ---
def load_player_data():
    try:
        df = pd.read_excel(SHEET_URL)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        df = pd.DataFrame(columns=["Name","War_Attempts","War_Stars","CWL_Attempts",
                                   "CWL_Stars","ClanCapital_Gold","ClanGames_Points",
                                   "RushEvents_Participation_pct"])
    return df.fillna(0)

# --- Compute scores ---
def compute_scores(df):
    for col in [
        "War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
        "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    MAX_WAR, MAX_CWL = 10, 7

    # Efficiencies
    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0, 1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0, 1) / 3

    k = 8
    df["War_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["CWL_Attempts"]/MAX_CWL)-0.5)))

    df["Fair_War_Score"] = df["War_Efficiency"] * df["War_Participation_Factor"]
    df["Fair_CWL_Score"] = df["CWL_Efficiency"] * df["CWL_Participation_Factor"]

    # 🔥 SAME AS PySide
    df["War_CWL_Skill_Score"] = (
        (df["Fair_War_Score"] * 0.6 + df["Fair_CWL_Score"] * 0.4) * 100
    )

    # Scaling
    gold_max = df["ClanCapital_Gold"].max() or 1
    games_max = df["ClanGames_Points"].max() or 1

    df["Gold_Scaled"] = df["ClanCapital_Gold"] / gold_max
    df["Games_Scaled"] = df["ClanGames_Points"] / games_max
    df["Events_Scaled"] = df["RushEvents_Participation_pct"] / 100

    # 🔥 FINAL SCORE — IDENTICAL WEIGHTS
    df["FinalScore"] = (
        (df["War_CWL_Skill_Score"] / 100) * 0.32 +
        df["Gold_Scaled"] * 0.05 +
        df["Games_Scaled"] * 0.21 +
        df["Events_Scaled"] * 0.42
    ) * 100

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    df["Rank"] = df["FinalScore"].rank(
        ascending=False, method="min"
    ).astype(int)

    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

# --- UI ---
st.set_page_config(page_title="ClashIntel ⚔️", layout="wide")
st.title("🏆 Top Clan Players Leaderboard")

df = compute_scores(load_player_data())

# --- HTML + CSS ---
html = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

:root {
    --bg-card: rgba(255,255,255,0.04);
    --border-soft: rgba(255,255,255,0.08);
    --neon: #5ee7ff;
    --text-main: #e8ecf1;
    --text-muted: #9aa4b2;
}

/* =====================
   BASE / GLOBAL
===================== */

html, body {
    max-width: 100%;
    overflow-x: hidden;
}

body {
    font-family: 'Inter', sans-serif;
    background: transparent;
    color: var(--text-main);
}

.leaderboard {
    width: 100%;
    max-width: min(1400px, 96vw);
    margin: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding-bottom: 40px;
    padding-inline: clamp(8px, 2vw, 20px);
}

/* =====================
   PLAYER CARD
===================== */

.player-row {
    display: grid;
    grid-template-columns:
        60px
        minmax(160px, 1.3fr)
        repeat(5, minmax(120px, 1fr))
        120px;
    gap: 12px;
    align-items: center;
    padding: 16px 20px;
    border-radius: 18px;
    background: linear-gradient(
        180deg,
        rgba(255,255,255,0.05),
        rgba(255,255,255,0.02)
    );
    border: 1px solid var(--border-soft);
    backdrop-filter: blur(14px);
    transition: all 0.25s ease;
}

.player-row:hover {
    transform: translateY(-2px);
    border-color: rgba(94,231,255,0.35);
    box-shadow:
        0 0 0 1px rgba(94,231,255,0.25),
        0 18px 40px rgba(0,0,0,0.45);
}

/* =====================
   RANK
===================== */

.rank-badge {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    font-weight: 700;
    background: rgba(255,255,255,0.08);
    color: var(--text-muted);
}

.rank-badge.gold   { background: linear-gradient(135deg,#FFD700,#FFB700); color:#000; }
.rank-badge.silver { background:#cfd3d6; color:#000; }
.rank-badge.bronze { background:#c27c3d; color:#fff; }

/* =====================
   NAME
===================== */

.player-name {
    font-size: clamp(15px, 1.3vw, 18px);
    font-weight: 700;
    letter-spacing: 0.3px;
    color: var(--text-main);
}

/* =====================
   STATS
===================== */

.stats-bar-wrapper {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.stats-label {
    font-size: clamp(10px, 0.9vw, 11px);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
    align-items: center;
    white-space: nowrap;
}

.stats-label span[style] {
    font-size: 10px;
    letter-spacing: 0.04em;
}

.stats-bar-container {
    width: 100%;
    height: clamp(9px, 1vw, 12px);
    background: rgba(255,255,255,0.08);
    border-radius: 999px;
    overflow: hidden;
}

.stats-bar {
    height: 100%;
    border-radius: 999px;
}

.stat-value {
    font-size: 11px;
    font-weight: 600;
    color: #e8ecf1;
    opacity: 0.85;
    margin-left: 8px;
}

/* Bar colors */
.attack { background: linear-gradient(90deg,#ff6a3d,#ff9a3d); }
.gold   { background: linear-gradient(90deg,#f5c542,#ffe08a); }
.games  { background: linear-gradient(90deg,#4facfe,#00f2fe); }
.events { background: linear-gradient(90deg,#43e97b,#38f9d7); }

/* =====================
   FINAL SCORE
===================== */

.final-score {
    text-align: center;
    font-weight: 800;
    font-size: clamp(16px, 1.4vw, 20px);
    padding: 12px 0;
    border-radius: 14px;
    letter-spacing: 0.04em;
    border: 1px solid var(--border-soft);
}

/* Score tiers */
.score-gold   { background: linear-gradient(135deg,#FFD700,#FFB700); color:#000; }
.score-purple { background: linear-gradient(135deg,#8e2de2,#4a00e0); }
.score-blue   { background: linear-gradient(135deg,#00c6ff,#0072ff); }
.score-green  { background: linear-gradient(135deg,#56ab2f,#a8e063); color:#072b00; }
.score-red    { background: linear-gradient(135deg,#cb2d3e,#ef473a); }

/* =====================
   RESPONSIVE BREAKPOINTS
===================== */

/* Large tablets / small laptops */
@media (max-width: 1200px) {
    .player-row {
        grid-template-columns:
            50px
            minmax(140px, 1.2fr)
            repeat(4, 1fr)
            110px;
    }

    /* hide least important stat */
    .player-row > .stats-bar-wrapper:nth-child(7) {
        display: none;
    }
}

/* Tablets */
@media (max-width: 900px) {
    .player-row {
        grid-template-columns: 1fr 1fr;
        grid-template-areas:
            "rank score"
            "name name"
            "war war"
            "cwl cwl"
            "gold games"
            "events events";
        gap: 12px;
    }

    .rank-badge   { grid-area: rank; }
    .final-score  { grid-area: score; }
    .player-name  { grid-area: name; }

    .player-row > .stats-bar-wrapper:nth-child(3) { grid-area: war; }
    .player-row > .stats-bar-wrapper:nth-child(4) { grid-area: cwl; }
    .player-row > .stats-bar-wrapper:nth-child(5) { grid-area: gold; }
    .player-row > .stats-bar-wrapper:nth-child(6) { grid-area: games; }
    .player-row > .stats-bar-wrapper:nth-child(7) {
        grid-area: events;
        display: flex;
    }
}

/* Phones */
@media (max-width: 520px) {
    .player-row {
        grid-template-columns: 1fr;
        grid-template-areas:
            "rank"
            "name"
            "score"
            "war"
            "cwl"
            "gold"
            "games"
            "events";
        padding: 14px;
    }

    .rank-badge {
        margin: auto;
    }

    .player-name {
        text-align: center;
    }
}
</style>

<div class="leaderboard">
"""

# --- Add player rows with dynamic score color ---
for _, row in df.iterrows():

    # Badge colors
    if row["Rank"] == 1:
        badge_class = "rank-badge gold"
    elif row["Rank"] == 2:
        badge_class = "rank-badge silver"
    elif row["Rank"] == 3:
        badge_class = "rank-badge bronze"
    else:
        badge_class = "rank-badge"

    # Dynamic Final Score color
    score = row["FinalScore"]
    if score >= 85:
        score_class = "score-gold"
    elif score >= 70:
        score_class = "score-purple"
    elif score >= 55:
        score_class = "score-blue"
    elif score >= 40:
        score_class = "score-green"
    else:
        score_class = "score-red"

    html += f"""
    <div class="player-row">
        <div class="{badge_class}">{row['Rank']}</div>
        <div class="player-name">{row['Name']}</div>

        <!-- ⚔️ WAR -->
        <div class="stats-bar-wrapper">
            <div class="stats-label">
                ⚔️ War <span style="opacity:0.6;">(Stars / Attacks)</span>
                <span class="stat-value">
                    {int(row['War_Stars'])} / {int(row['War_Attempts'])}
                </span>
            </div>
            <div class="stats-bar-container"
                 title="Total Stars / War Attacks">
                <div class="stats-bar attack"
                     style="width:{min((row['War_Stars']/(row['War_Attempts'] if row['War_Attempts']>0 else 1))*100,100)}%">
                </div>
            </div>
        </div>
        
        <!-- 🛡️ CWL -->
        <div class="stats-bar-wrapper">
            <div class="stats-label">
                🛡️ CWL <span style="opacity:0.6;">(Stars / Attacks)</span>
                <span class="stat-value">
                    {int(row['CWL_Stars'])} / {int(row['CWL_Attempts'])}
                </span>
            </div>
            <div class="stats-bar-container"
                 title="Total Stars / CWL Attacks">
                <div class="stats-bar attack"
                     style="width:{min((row['CWL_Stars']/(row['CWL_Attempts'] if row['CWL_Attempts']>0 else 1))*100,100)}%">
                </div>
            </div>
        </div>
        
        <!-- 💰 CAPITAL GOLD -->
        <div class="stats-bar-wrapper">
            <div class="stats-label">
                💰 Capital Gold
                <span class="stat-value">
                    {int(row['ClanCapital_Gold']):,}
                </span>
            </div>
            <div class="stats-bar-container"
                 title="Capital Gold: {int(row['ClanCapital_Gold']):,}">
                <div class="stats-bar gold"
                     style="width:{min(row['Gold_Scaled']*100,100)}%">
                </div>
            </div>
        </div>
        
        <!-- 🎮 CLAN GAMES -->
        <div class="stats-bar-wrapper">
            <div class="stats-label">
                🎮 Clan Games
                <span class="stat-value">
                    {int(row['ClanGames_Points']):,}
                </span>
            </div>
            <div class="stats-bar-container"
                 title="Clan Games: {int(row['ClanGames_Points']):,}">
                <div class="stats-bar games"
                     style="width:{min(row['Games_Scaled']*100,100)}%">
                </div>
            </div>
        </div>
        
        <!-- 🎯 EVENTS -->
        <div class="stats-bar-wrapper">
            <div class="stats-label">
                🎯 Events
                <span class="stat-value">
                    {row['Events_Scaled']*100:.0f}%
                </span>
            </div>
            <div class="stats-bar-container"
                 title="Events: {row['Events_Scaled']*100:.0f}%">
                <div class="stats-bar events"
                     style="width:{min(row['Events_Scaled']*100,100)}%">
                </div>
            </div>
        </div>

        <div class="final-score {score_class}">⭐ {row['FinalScore']:.2f}</div>
    </div>
    """

html += "</div>"

components.html(html, height=9000, scrolling=True)
