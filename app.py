import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import os

# --- Google Sheet URL ---
SHEET_URL = os.getenv("SHEET_URL")

# --- Streamlit global config ---
st.set_page_config(
    page_title="ClashIntel",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Deep dark background for the Streamlit container
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top, #0b1020, #05070d 60%);
}
[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# --- Data Loading & Processing ---
@st.cache_data(ttl=3600)
def load_and_compute():
    try:
        df = pd.read_excel(SHEET_URL)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

    # Numeric conversion
    cols = ["War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
            "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Scoring Logic
    MAX_WAR, MAX_CWL, k = 10, 7, 8
    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0,1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0,1) / 3
    
    df["War_Part"] = 1 / (1 + np.exp(-k*((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Part"] = 1 / (1 + np.exp(-k*((df["CWL_Attempts"]/MAX_CWL)-0.5)))
    
    skill_score = ((df["War_Efficiency"] * df["War_Part"] * 0.6) + 
                   (df["CWL_Efficiency"] * df["CWL_Part"] * 0.4)) * 100

    gold_max = df["ClanCapital_Gold"].max() or 1
    games_max = df["ClanGames_Points"].max() or 1

    df["FinalScore"] = (
        (skill_score / 100) * 0.32 +
        (df["ClanCapital_Gold"] / gold_max) * 0.05 +
        (df["ClanGames_Points"] / games_max) * 0.21 +
        (df["RushEvents_Participation_pct"] / 100) * 0.42
    ) * 100
    
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

df = load_and_compute()

st.title("🏆 Top Clan Players Leaderboard")

# --- RESTORED RESPONSIVE HTML + CSS ---
html_content = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root {
    --bg-card: rgba(255,255,255,0.04);
    --border-soft: rgba(255,255,255,0.08);
    --text-main: #e8ecf1;
    --text-muted: #9aa4b2;
}

body { font-family: 'Inter', sans-serif; background: transparent; color: var(--text-main); margin: 0; }

.leaderboard {
    width: 100%;
    max-width: 1400px;
    margin: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 10px;
}

/* DESKTOP LAYOUT (Default) */
.player-row {
    display: grid;
    grid-template-columns: 60px minmax(160px, 1.3fr) repeat(5, 1fr) 120px;
    gap: 12px;
    align-items: center;
    padding: 16px 20px;
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border: 1px solid var(--border-soft);
    backdrop-filter: blur(14px);
}

.rank-badge { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; font-weight: 700; background: rgba(255,255,255,0.08); }
.rank-badge.gold { background: linear-gradient(135deg,#FFD700,#FFB700); color:#000; }
.rank-badge.silver { background:#cfd3d6; color:#000; }
.rank-badge.bronze { background:#c27c3d; color:#fff; }

.player-name { font-size: 18px; font-weight: 700; }

.stats-bar-wrapper { display: flex; flex-direction: column; gap: 6px; }
.stats-label { font-size: 10px; text-transform: uppercase; color: var(--text-muted); display: flex; justify-content: space-between; }
.stats-bar-container { width: 100%; height: 10px; background: rgba(255,255,255,0.08); border-radius: 10px; overflow: hidden; }
.stats-bar { height: 100%; border-radius: 10px; }

.attack { background: linear-gradient(90deg,#ff6a3d,#ff9a3d); }
.gold { background: linear-gradient(90deg,#f5c542,#ffe08a); }
.games { background: linear-gradient(90deg,#4facfe,#00f2fe); }
.events { background: linear-gradient(90deg,#43e97b,#38f9d7); }

.final-score { text-align: center; font-weight: 800; font-size: 18px; padding: 10px; border-radius: 12px; border: 1px solid var(--border-soft); }
.score-gold { background: linear-gradient(135deg,#FFD700,#FFB700); color:#000; }
.score-red { background: linear-gradient(135deg,#cb2d3e,#ef473a); }

/* RESPONSIVE: TABLETS */
@media (max-width: 1000px) {
    .player-row {
        grid-template-columns: 1fr 1fr;
        grid-template-areas: 
            "rank score"
            "name name"
            "war cwl"
            "gold games"
            "events events";
    }
    .rank-badge { grid-area: rank; }
    .final-score { grid-area: score; }
    .player-name { grid-area: name; text-align: center; margin: 10px 0; }
    .war-box { grid-area: war; }
    .cwl-box { grid-area: cwl; }
    .gold-box { grid-area: gold; }
    .games-box { grid-area: games; }
    .events-box { grid-area: events; }
}

/* RESPONSIVE: PHONES */
@media (max-width: 500px) {
    .player-row {
        grid-template-columns: 1fr;
        grid-template-areas: "rank" "name" "score" "war" "cwl" "gold" "games" "events";
    }
    .rank-badge { margin: auto; }
}
</style>
<div class="leaderboard">
"""

for _, row in df.iterrows():
    b_class = "rank-badge gold" if row["Rank"]==1 else "rank-badge silver" if row["Rank"]==2 else "rank-badge bronze" if row["Rank"]==3 else "rank-badge"
    s_class = "score-gold" if row["FinalScore"] >= 85 else "score-red" if row["FinalScore"] < 40 else ""
    
    # Calculate bar widths
    war_w = min((row['War_Stars']/(row['War_Attempts'] if row['War_Attempts']>0 else 1))*33.3, 100)
    cwl_w = min((row['CWL_Stars']/(row['CWL_Attempts'] if row['CWL_Attempts']>0 else 1))*33.3, 100)
    
    html_content += f"""
    <div class="player-row">
        <div class="{b_class}">{row['Rank']}</div>
        <div class="player-name">{row['Name']}</div>
        
        <div class="stats-bar-wrapper war-box">
            <div class="stats-label">War <span>{int(row['War_Stars'])}★</span></div>
            <div class="stats-bar-container"><div class="stats-bar attack" style="width:{war_w}%"></div></div>
        </div>
        
        <div class="stats-bar-wrapper cwl-box">
            <div class="stats-label">CWL <span>{int(row['CWL_Stars'])}★</span></div>
            <div class="stats-bar-container"><div class="stats-bar attack" style="width:{cwl_w}%"></div></div>
        </div>

        <div class="stats-bar-wrapper gold-box">
            <div class="stats-label">Gold <span>{int(row['ClanCapital_Gold']):,}</span></div>
            <div class="stats-bar-container"><div class="stats-bar gold" style="width:{row['FinalScore']}%"></div></div>
        </div>

        <div class="stats-bar-wrapper games-box">
            <div class="stats-label">Games <span>{int(row['ClanGames_Points'])}</span></div>
            <div class="stats-bar-container"><div class="stats-bar games" style="width:{row['FinalScore']}%"></div></div>
        </div>

        <div class="stats-bar-wrapper events-box">
            <div class="stats-label">Events <span>{row['RushEvents_Participation_pct']}%</span></div>
            <div class="stats-bar-container"><div class="stats-bar events" style="width:{row['RushEvents_Participation_pct']}%"></div></div>
        </div>

        <div class="final-score {s_class}">⭐ {row['FinalScore']:.2f}</div>
    </div>
    """

html_content += "</div>"
components.html(html_content, height=1200, scrolling=True)
