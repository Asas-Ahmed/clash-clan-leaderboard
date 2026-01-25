import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import os
from datetime import datetime
import pytz

# --- Timezone Logic ---
sl_tz = pytz.timezone('Asia/Colombo')
current_time = datetime.now(sl_tz).strftime('%I:%M:%S %p')

# --- Google Sheet URL ---
SHEET_URL = os.getenv("SHEET_URL")

# --- Streamlit global config ---
st.set_page_config(
    page_title="ClashIntel",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sidebar Heartbeat
st.sidebar.markdown(f"""
    <style>
    .status-card {{ background-color: #161b22; padding: 12px; border-radius: 8px; border: 1px solid #30363d; font-family: sans-serif; }}
    .time-val {{ color: #ffffff; font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
    .status-dot {{ height: 8px; width: 8px; background-color: #238636; border-radius: 50%; box-shadow: 0 0 5px #238636; }}
    </style>
    <div class="status-card">
        <div style="color: #8b949e; font-size: 10px; font-weight: 600; text-transform: uppercase;">System Heartbeat</div>
        <div class="time-val"><span class="status-dot"></span>{current_time}</div>
        <div style="color: #484f58; font-size: 9px; margin-top: 4px;">GMT+5:30 • Colombo, SL</div>
    </div>
""", unsafe_allow_html=True)

# App Background
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: radial-gradient(circle at top, #0b1020, #05070d 60%); }
[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# --- Data Loading & Processing ---
@st.cache_data(ttl=3600)
def load_and_compute():
    try:
        df = pd.read_excel(SHEET_URL)
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

    cols = ["War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
            "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    MAX_WAR, MAX_CWL, k = 10, 7, 8
    df["War_Eff"] = df["War_Stars"] / df["War_Attempts"].replace(0,1) / 3
    df["CWL_Eff"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0,1) / 3
    df["War_P"] = 1 / (1 + np.exp(-k*((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_P"] = 1 / (1 + np.exp(-k*((df["CWL_Attempts"]/MAX_CWL)-0.5)))
    
    skill = ((df["War_Eff"] * df["War_P"] * 0.6) + (df["CWL_Eff"] * df["CWL_P"] * 0.4)) * 100
    g_max, gm_max = df["ClanCapital_Gold"].max() or 1, df["ClanGames_Points"].max() or 1

    df["FinalScore"] = ((skill / 100) * 0.32 + (df["ClanCapital_Gold"]/g_max) * 0.05 + 
                        (df["ClanGames_Points"]/gm_max) * 0.21 + (df["RushEvents_Participation_pct"]/100) * 0.42) * 100
    
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

df = load_and_compute()
st.title("🏆 Top Clan Players Leaderboard")

# --- HTML/CSS with Full Responsive Restoration ---
html_code = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
:root { --border-soft: rgba(255,255,255,0.08); --text-main: #e8ecf1; --text-muted: #9aa4b2; }
html, body { max-width: 100%; overflow-x: hidden; background: transparent; color: var(--text-main); font-family: 'Inter', sans-serif; }
.leaderboard { width: 100%; max-width: 1400px; margin: auto; display: flex; flex-direction: column; gap: 14px; padding: 10px; }

/* DESKTOP GRID */
.player-row {
    display: grid;
    grid-template-columns: 60px minmax(160px, 1.3fr) repeat(5, 1fr) 120px;
    gap: 12px; align-items: center; padding: 16px 20px; border-radius: 18px;
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border: 1px solid var(--border-soft); backdrop-filter: blur(14px);
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
.score-purple { background: linear-gradient(135deg,#8e2de2,#4a00e0); }
.score-blue { background: linear-gradient(135deg,#00c6ff,#0072ff); }
.score-green { background: linear-gradient(135deg,#56ab2f,#a8e063); color:#072b00; }
.score-red { background: linear-gradient(135deg,#cb2d3e,#ef473a); }

/* TABLET LAYOUT */
@media (max-width: 900px) {
    .player-row {
        grid-template-columns: 1fr 1fr;
        grid-template-areas: "rank score" "name name" "war war" "cwl cwl" "gold games" "events events";
    }
    .area-rank { grid-area: rank; } .area-score { grid-area: score; } .area-name { grid-area: name; text-align: center; }
    .area-war { grid-area: war; } .area-cwl { grid-area: cwl; } .area-gold { grid-area: gold; } .area-games { grid-area: games; } .area-events { grid-area: events; }
}

/* MOBILE LAYOUT */
@media (max-width: 520px) {
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
    # Style Classes
    b_cls = "rank-badge gold" if row["Rank"]==1 else "rank-badge silver" if row["Rank"]==2 else "rank-badge bronze" if row["Rank"]==3 else "rank-badge"
    s_val = row["FinalScore"]
    s_cls = "score-gold" if s_val>=85 else "score-purple" if s_val>=70 else "score-blue" if s_val>=55 else "score-green" if s_val>=40 else "score-red"
    
    # Progress Calculation
    war_p = min((row['War_Stars']/(row['War_Attempts'] or 1))*33.3, 100)
    cwl_p = min((row['CWL_Stars']/(row['CWL_Attempts'] or 1))*33.3, 100)
    g_p = (row['ClanCapital_Gold'] / df['ClanCapital_Gold'].max()) * 100
    gm_p = (row['ClanGames_Points'] / df['ClanGames_Points'].max()) * 100

    html_code += f"""
    <div class="player-row">
        <div class="{b_cls} area-rank">{row['Rank']}</div>
        <div class="player-name area-name">{row['Name']}</div>
        
        <div class="stats-bar-wrapper area-war">
            <div class="stats-label">War <span>{int(row['War_Stars'])}★ / {int(row['War_Attempts'])}</span></div>
            <div class="stats-bar-container"><div class="stats-bar attack" style="width:{war_p}%"></div></div>
        </div>
        
        <div class="stats-bar-wrapper area-cwl">
            <div class="stats-label">CWL <span>{int(row['CWL_Stars'])}★ / {int(row['CWL_Attempts'])}</span></div>
            <div class="stats-bar-container"><div class="stats-bar attack" style="width:{cwl_p}%"></div></div>
        </div>

        <div class="stats-bar-wrapper area-gold">
            <div class="stats-label">Gold <span>{int(row['ClanCapital_Gold']):,}</span></div>
            <div class="stats-bar-container"><div class="stats-bar gold" style="width:{g_p}%"></div></div>
        </div>

        <div class="stats-bar-wrapper area-games">
            <div class="stats-label">Games <span>{int(row['ClanGames_Points']):,}</span></div>
            <div class="stats-bar-container"><div class="stats-bar games" style="width:{gm_p}%"></div></div>
        </div>

        <div class="stats-bar-wrapper area-events">
            <div class="stats-label">Events <span>{row['RushEvents_Participation_pct']}%</span></div>
            <div class="stats-bar-container"><div class="stats-bar events" style="width:{row['RushEvents_Participation_pct']}%"></div></div>
        </div>

        <div class="final-score {s_cls} area-score">⭐ {s_val:.2f}</div>
    </div>
    """

html_code += "</div>"
components.html(html_code, height=6000, scrolling=True)
