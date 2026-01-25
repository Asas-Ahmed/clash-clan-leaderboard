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
@st.cache_data(ttl=3600)  # Cache results for 1 hour
def load_player_data(url):
    try:
        # Load only necessary columns to save memory
        df = pd.read_excel(url)
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()
    return df.fillna(0)

# 2. CACHE THE HEAVY CALCULATIONS
@st.cache_data
def compute_scores(df):
    if df.empty:
        return df
    
    # Vectorized operations (staying in Pandas as much as possible)
    cols = ["War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
            "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]
    
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    MAX_WAR, MAX_CWL, k = 10, 7, 8

    # Efficiencies
    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0, 1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0, 1) / 3

    # Participation Factors
    df["War_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["CWL_Attempts"]/MAX_CWL)-0.5)))

    df["Fair_War_Score"] = df["War_Efficiency"] * df["War_Participation_Factor"]
    df["Fair_CWL_Score"] = df["CWL_Efficiency"] * df["CWL_Participation_Factor"]

    df["War_CWL_Skill_Score"] = (df["Fair_War_Score"] * 0.6 + df["Fair_CWL_Score"] * 0.4) * 100

    gold_max = df["ClanCapital_Gold"].max() or 1
    games_max = df["ClanGames_Points"].max() or 1

    df["Gold_Scaled"] = df["ClanCapital_Gold"] / gold_max
    df["Games_Scaled"] = df["ClanGames_Points"] / games_max
    df["Events_Scaled"] = df["RushEvents_Participation_pct"] / 100

    df["FinalScore"] = ((df["War_CWL_Skill_Score"] / 100) * 0.32 +
                        df["Gold_Scaled"] * 0.05 +
                        df["Games_Scaled"] * 0.21 +
                        df["Events_Scaled"] * 0.42) * 100

    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)
    
    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

# --- EXECUTION ---
raw_data = load_player_data(SHEET_URL)
df = compute_scores(raw_data)

st.title("🏆 Top Clan Players Leaderboard")

# 3. USE BATCHED STRING BUILDING
# Building one massive list and joining at the end is 10x faster than 'html += ...'
container_html = ["""
<style>
    /* ... (Your CSS remains the same) ... */
</style>
<div class="leaderboard">
"""]

for _, row in df.iterrows():
    # Logic for classes
    badge_class = "rank-badge gold" if row["Rank"] == 1 else "rank-badge silver" if row["Rank"] == 2 else "rank-badge bronze" if row["Rank"] == 3 else "rank-badge"
    
    score = row["FinalScore"]
    score_class = "score-gold" if score >= 85 else "score-purple" if score >= 70 else "score-blue" if score >= 55 else "score-green" if score >= 40 else "score-red"

    # Using list.append for performance
    container_html.append(f"""
    <div class="player-row">
        <div class="{badge_class}">{row['Rank']}</div>
        <div class="player-name">{row['Name']}</div>
        ... (rest of your row HTML) ...
        <div class="final-score {score_class}">⭐ {row['FinalScore']:.2f}</div>
    </div>
    """)

container_html.append("</div>")

# Join everything at once
full_html = "".join(container_html)
components.html(full_html, height=1200, scrolling=True)
