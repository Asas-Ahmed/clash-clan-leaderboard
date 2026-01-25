import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import os

# --- CONFIG ---
SHEET_URL = os.getenv("SHEET_URL")

st.set_page_config(
    page_title="ClashIntel ⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 1. FASTER DATA FETCHING (CSV is faster than Excel)
@st.cache_data(ttl=3600)
def load_player_data(url):
    try:
        # Convert Google Sheets URL to CSV export link for instant loading
        if "edit" in url:
            csv_url = url.split('/edit')[0] + '/export?format=csv'
        else:
            csv_url = url
        df = pd.read_csv(csv_url)
    except Exception as e:
        # Fallback to excel if CSV fails
        try:
            df = pd.read_excel(url)
        except:
            st.error(f"Failed to load data: {e}")
            return pd.DataFrame()
    return df.fillna(0)

# 2. CACHE CALCULATIONS
@st.cache_data
def compute_scores(df):
    if df.empty: return df
    
    # Pre-convert columns to numeric in bulk
    cols = ["War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
            "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    MAX_WAR, MAX_CWL, k = 10, 7, 8

    # Vectorized Math (No loops here)
    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0, 1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0, 1) / 3

    df["War_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["CWL_Attempts"]/MAX_CWL)-0.5)))

    df["War_CWL_Skill_Score"] = ((df["War_Efficiency"] * df["War_Participation_Factor"] * 0.6) + 
                                 (df["CWL_Efficiency"] * df["CWL_Participation_Factor"] * 0.4)) * 100

    df["Gold_Scaled"] = df["ClanCapital_Gold"] / (df["ClanCapital_Gold"].max() or 1)
    df["Games_Scaled"] = df["ClanGames_Points"] / (df["ClanGames_Points"].max() or 1)
    df["Events_Scaled"] = df["RushEvents_Participation_pct"] / 100

    df["FinalScore"] = ((df["War_CWL_Skill_Score"] / 100) * 0.32 +
                        df["Gold_Scaled"] * 0.05 +
                        df["Games_Scaled"] * 0.21 +
                        df["Events_Scaled"] * 0.42) * 100

    df = df.replace([np.inf, -np.inf], 0).fillna(0)
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)
    
    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

# 3. VECTORIZED HTML BUILDING (The biggest speed boost)
def render_leaderboard(df):
    # This logic runs inside a vectorized environment
    def build_row(row):
        rank = int(row['Rank'])
        score = row['FinalScore']
        
        badge = "gold" if rank == 1 else "silver" if rank == 2 else "bronze" if rank == 3 else ""
        s_class = "gold" if score >= 85 else "purple" if score >= 70 else "blue" if score >= 55 else "green" if score >= 40 else "red"
        
        return f"""
        <div class="player-row">
            <div class="rank-badge {badge}">{rank}</div>
            <div class="player-name">{row['Name']}</div>
            <div class="final-score score-{s_class}">⭐ {score:.2f}</div>
        </div>"""

    # Combine rows using join on the results of 'apply'
    rows_html = "".join(df.apply(build_row, axis=1))
    
    style = """<style>
        .leaderboard { font-family: sans-serif; background: #1a1a1a; color: white; padding: 10px; border-radius: 10px; }
        .player-row { display: flex; align-items: center; padding: 8px; border-bottom: 1px solid #333; }
        .rank-badge { width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: 50%; margin-right: 15px; background: #444; font-weight: bold; }
        .gold { background: #FFD700; color: black; }
        .silver { background: #C0C0C0; color: black; }
        .bronze { background: #CD7F32; color: black; }
        .player-name { flex-grow: 1; font-size: 1.1rem; }
        .final-score { font-weight: bold; padding: 4px 10px; border-radius: 5px; }
        .score-gold { color: #FFD700; } .score-purple { color: #A020F0; } .score-blue { color: #00BFFF; }
        .score-green { color: #32CD32; } .score-red { color: #FF4444; }
    </style>"""
    
    return f"{style}<div class='leaderboard'>{rows_html}</div>"

# --- EXECUTION ---
raw_data = load_player_data(SHEET_URL)
processed_df = compute_scores(raw_data)

st.title("🏆 Top Clan Players Leaderboard")

# Generate the HTML
if not processed_df.empty:
    # Use only the top results if the list is massive to prevent browser lag
    leaderboard_html = render_leaderboard(processed_df.head(100))
    components.html(leaderboard_html, height=800, scrolling=True)
else:
    st.warning("No data found.")
