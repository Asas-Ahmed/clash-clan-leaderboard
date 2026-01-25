import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import os

# --- Google Sheet URL ---
SHEET_URL = os.getenv("SHEET_URL")

# --- Streamlit config ---
st.set_page_config(
    page_title="ClashIntel ⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Dark theme ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #0b1020, #05070d 60%);
}
[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# --- Load data with caching (refresh every 60s) ---
@st.cache_data(ttl=60)
def load_player_data():
    try:
        df = pd.read_excel(SHEET_URL)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        df = pd.DataFrame(columns=[
            "Name","War_Attempts","War_Stars","CWL_Attempts",
            "CWL_Stars","ClanCapital_Gold","ClanGames_Points",
            "RushEvents_Participation_pct"
        ])
    return df.fillna(0)

# --- Compute scores ---
def compute_scores(df):
    numeric_cols = [
        "War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
        "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"
    ]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    MAX_WAR, MAX_CWL = 10, 7
    k = 8

    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0, 1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0, 1) / 3

    df["War_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["CWL_Attempts"]/MAX_CWL)-0.5)))

    df["Fair_War_Score"] = df["War_Efficiency"] * df["War_Participation_Factor"]
    df["Fair_CWL_Score"] = df["CWL_Efficiency"] * df["CWL_Participation_Factor"]

    df["War_CWL_Skill_Score"] = (df["Fair_War_Score"]*0.6 + df["Fair_CWL_Score"]*0.4) * 100

    gold_max = df["ClanCapital_Gold"].max() or 1
    games_max = df["ClanGames_Points"].max() or 1

    df["Gold_Scaled"] = df["ClanCapital_Gold"] / gold_max
    df["Games_Scaled"] = df["ClanGames_Points"] / games_max
    df["Events_Scaled"] = df["RushEvents_Participation_pct"] / 100

    df["FinalScore"] = (
        (df["War_CWL_Skill_Score"] / 100) * 0.31 +
        df["Gold_Scaled"] * 0.05 +
        df["Games_Scaled"] * 0.21 +
        df["Events_Scaled"] * 0.43
    ) * 100

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)

    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

# --- Load & compute ---
df = compute_scores(load_player_data())
st.title("🏆 Top Clan Players Leaderboard")

# --- HTML + CSS (unchanged style) ---
html = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root { --bg-card: rgba(255,255,255,0.04); --border-soft: rgba(255,255,255,0.08); --neon: #5ee7ff;
--text-main: #e8ecf1; --text-muted: #9aa4b2; }
html, body { max-width: 100%; overflow-x: hidden; }
body { font-family: 'Inter', sans-serif; background: transparent; color: var(--text-main); }
.leaderboard { width:100%; max-width:min(1400px,96vw); margin:auto; display:flex; flex-direction:column; gap:14px; padding-bottom:40px; padding-inline:clamp(8px,2vw,20px); }
.player-row { display:grid; grid-template-columns:60px minmax(160px,1.3fr) repeat(5,minmax(120px,1fr)) 120px; gap:12px; align-items:center; padding:16px 20px; border-radius:18px; background:linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02)); border:1px solid var(--border-soft); backdrop-filter: blur(14px); transition: all 0.25s ease; }
.player-row:hover { transform:translateY(-2px); border-color: rgba(94,231,255,0.35); box-shadow: 0 0 0 1 rgba(94,231,255,0.25),0 18px 40px rgba(0,0,0,0.45); }
.rank-badge { width:44px; height:44px; border-radius:12px; display:grid; place-items:center; font-weight:700; background:rgba(255,255,255,0.08); color:var(--text-muted); }
.rank-badge.gold { background: linear-gradient(135deg,#FFD700,#FFB700); color:#000; }
.rank-badge.silver { background:#cfd3d6; color:#000; }
.rank-badge.bronze { background:#c27c3d; color:#fff; }
.player-name { font-size:clamp(15px,1.3vw,18px); font-weight:700; letter-spacing:0.3px; color:var(--text-main); }
.stats-bar-wrapper { display:flex; flex-direction:column; gap:6px; }
.stats-label { font-size:clamp(10px,0.9vw,11px); text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); display:flex; justify-content:space-between; align-items:center; white-space:nowrap; }
.stats-label span[style] { font-size:10px; letter-spacing:0.04em; }
.stats-bar-container { width:100%; height:clamp(9px,1vw,12px); background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden; }
.stats-bar { height:100%; border-radius:999px; }
.stat-value { font-size:11px; font-weight:600; color:#e8ecf1; opacity:0.85; margin-left:8px; }
.attack { background: linear-gradient(90deg,#ff6a3d,#ff9a3d); }
.gold { background: linear-gradient(90deg,#f5c542,#ffe08a); }
.games { background: linear-gradient(90deg,#4facfe,#00f2fe); }
.events { background: linear-gradient(90deg,#43e97b,#38f9d7); }
.final-score { text-align:center; font-weight:800; font-size:clamp(16px,1.4vw,20px); padding:12px 0; border-radius:14px; letter-spacing:0.04em; border:1px solid var(--border-soft); }
.score-gold { background: linear-gradient(135deg,#FFD700,#FFB700); color:#000; }
.score-purple { background: linear-gradient(135deg,#8e2de2,#4a00e0); }
.score-blue { background: linear-gradient(135deg,#00c6ff,#0072ff); }
.score-green { background: linear-gradient(135deg,#56ab2f,#a8e063); color:#072b00; }
.score-red { background: linear-gradient(135deg,#cb2d3e,#ef473a); }
@media (max-width:1200px){.player-row{grid-template-columns:50px minmax(140px,1.2fr) repeat(4,1fr) 110px;}.player-row>.stats-bar-wrapper:nth-child(7){display:none;}}
@media (max-width:900px){.player-row{grid-template-columns:1fr 1fr; grid-template-areas:"rank score" "name name" "war war" "cwl cwl" "gold games" "events events"; gap:12px;} .rank-badge{grid-area:rank;} .final-score{grid-area:score;} .player-name{grid-area:name;} .player-row>.stats-bar-wrapper:nth-child(3){grid-area:war;} .player-row>.stats-bar-wrapper:nth-child(4){grid-area:cwl;} .player-row>.stats-bar-wrapper:nth-child(5){grid-area:gold;} .player-row>.stats-bar-wrapper:nth-child(6){grid-area:games;} .player-row>.stats-bar-wrapper:nth-child(7){grid-area:events; display:flex;} }
@media (max-width:520px){.player-row{grid-template-columns:1fr; grid-template-areas:"rank" "name" "score" "war" "cwl" "gold" "games" "events"; padding:14px;} .rank-badge{margin:auto;} .player-name{text-align:center;}}
</style>
<div class="leaderboard">
"""

# --- Build HTML rows efficiently ---
rows = []
for _, row in df.iterrows():
    # Badge
    badge_class = "rank-badge"
    if row.Rank == 1: badge_class += " gold"
    elif row.Rank == 2: badge_class += " silver"
    elif row.Rank == 3: badge_class += " bronze"

    # Score color
    score_class = "score-red"
    if row.FinalScore >= 85: score_class = "score-gold"
    elif row.FinalScore >= 70: score_class = "score-purple"
    elif row.FinalScore >= 55: score_class = "score-blue"
    elif row.FinalScore >= 40: score_class = "score-green"

    # Player row
    rows.append(f"""
    <div class="player-row">
        <div class="{badge_class}">{row.Rank}</div>
        <div class="player-name">{row.Name}</div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">⚔️ War <span style="opacity:0.6;">(Stars / Attacks)</span>
                <span class="stat-value">{int(row.War_Stars)} / {int(row.War_Attempts)}</span>
            </div>
            <div class="stats-bar-container" title="Total Stars / War Attacks">
                <div class="stats-bar attack" style="width:{min((row.War_Stars/(row.War_Attempts if row.War_Attempts>0 else 1))*100,100)}%"></div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">🛡️ CWL <span style="opacity:0.6;">(Stars / Attacks)</span>
                <span class="stat-value">{int(row.CWL_Stars)} / {int(row.CWL_Attempts)}</span>
            </div>
            <div class="stats-bar-container" title="Total Stars / CWL Attacks">
                <div class="stats-bar attack" style="width:{min((row.CWL_Stars/(row.CWL_Attempts if row.CWL_Attempts>0 else 1))*100,100)}%"></div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">💰 Capital Gold
                <span class="stat-value">{int(row.ClanCapital_Gold):,}</span>
            </div>
            <div class="stats-bar-container" title="Capital Gold: {int(row.ClanCapital_Gold):,}">
                <div class="stats-bar gold" style="width:{min(row.Gold_Scaled*100,100)}%"></div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">🎮 Clan Games
                <span class="stat-value">{int(row.ClanGames_Points):,}</span>
            </div>
            <div class="stats-bar-container" title="Clan Games: {int(row.ClanGames_Points):,}">
                <div class="stats-bar games" style="width:{min(row.Games_Scaled*100,100)}%"></div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">🎯 Events
                <span class="stat-value">{row.Events_Scaled*100:.0f}%</span>
            </div>
            <div class="stats-bar-container" title="Events: {row.Events_Scaled*100:.0f}%">
                <div class="stats-bar events" style="width:{min(row.Events_Scaled*100,100)}%"></div>
            </div>
        </div>

        <div class="final-score {score_class}">⭐ {row.FinalScore:.2f}</div>
    </div>
    """)

html += "".join(rows) + "</div>"

components.html(html, height=9000, scrolling=True)
