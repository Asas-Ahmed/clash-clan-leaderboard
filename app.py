import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import os

# --- Google Sheet URL ---
SHEET_URL = os.getenv("SHEET_URL")

st.set_page_config(
    page_title="ClashIntel ⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 1. CACHE THE DATA FETCHING
@st.cache_data(ttl=3600)
def load_player_data(url):
    cols = ["Name","War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
            "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]
    try:
        df = pd.read_excel(url, usecols=cols)
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()
    return df.fillna(0)

# 2. CACHE THE HEAVY CALCULATIONS
@st.cache_data
def compute_scores(df):
    if df.empty:
        return df
    
    # Ensure numeric
    num_cols = ["War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
                "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    MAX_WAR, MAX_CWL, k = 10, 7, 8

    # Efficiencies
    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0, 1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0, 1) / 3

    # Participation Factors
    df["War_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["CWL_Attempts"]/MAX_CWL)-0.5)))

    # Fair Scores
    df["Fair_War_Score"] = df["War_Efficiency"] * df["War_Participation_Factor"]
    df["Fair_CWL_Score"] = df["CWL_Efficiency"] * df["CWL_Participation_Factor"]

    df["War_CWL_Skill_Score"] = (df["Fair_War_Score"]*0.6 + df["Fair_CWL_Score"]*0.4) * 100

    # Scaling
    gold_max = df["ClanCapital_Gold"].max() or 1
    games_max = df["ClanGames_Points"].max() or 1

    df["Gold_Scaled"] = df["ClanCapital_Gold"] / gold_max
    df["Games_Scaled"] = df["ClanGames_Points"] / games_max
    df["Events_Scaled"] = df["RushEvents_Participation_pct"] / 100

    # Final Score
    df["FinalScore"] = ((df["War_CWL_Skill_Score"]/100)*0.32 +
                        df["Gold_Scaled"]*0.05 +
                        df["Games_Scaled"]*0.21 +
                        df["Events_Scaled"]*0.42) * 100

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)

    # Precompute badge class vectorized
    df["Badge_Class"] = np.where(df["Rank"]==1,"rank-badge gold",
                          np.where(df["Rank"]==2,"rank-badge silver",
                          np.where(df["Rank"]==3,"rank-badge bronze","rank-badge")))

    # Precompute score class vectorized
    conditions = [
        df["FinalScore"] >= 85,
        df["FinalScore"] >= 70,
        df["FinalScore"] >= 55,
        df["FinalScore"] >= 40
    ]
    choices = ["score-gold","score-purple","score-blue","score-green"]
    df["Score_Class"] = np.select(conditions, choices, default="score-red")

    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

# --- EXECUTION ---
raw_data = load_player_data(SHEET_URL)
df = compute_scores(raw_data)

st.title("🏆 Top Clan Players Leaderboard")

# 3. BUILD HTML FAST
container_html = ["""
<style>
    /* ... (Your CSS remains the same) ... */
</style>
<div class="leaderboard">
"""]

for row in df.itertuples(index=False):
    container_html.append(f"""
    <div class="player-row">
        <div class="{row.Badge_Class}">{row.Rank}</div>
        <div class="player-name">{row.Name}</div>
        ...
        <div class="final-score {row.Score_Class}">⭐ {row.FinalScore:.2f}</div>
    </div>
    """)

container_html.append("</div>")

full_html = "".join(container_html)

# Dynamic height: 50px per row
components.html(full_html, height=min(1200, 50*len(df)), scrolling=True)
