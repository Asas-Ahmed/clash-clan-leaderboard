import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components

# --- Google Sheet URL ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/118gjjn-oFYt4-hy8HVxius8LzeMA6V0SGVI_Mto5Heg/export?format=xlsx"

# --- Load data from Google Sheet ---
def load_player_data():
    try:
        df = pd.read_excel(SHEET_URL)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheet: {e}")
        df = pd.DataFrame(columns=["Name","War_Attempts","War_Stars","CWL_Attempts",
                                   "CWL_Stars","ClanCapital_Gold","ClanGames_Points",
                                   "RushEvents_Participation_pct"])
    return df.fillna(0)

# --- Compute Scores ---
def compute_scores(df):
    for col in ["War_Attempts","War_Stars","CWL_Attempts","CWL_Stars",
                "ClanCapital_Gold","ClanGames_Points","RushEvents_Participation_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    MAX_WAR, MAX_CWL = 10, 7
    df["War_Efficiency"] = df["War_Stars"] / df["War_Attempts"].replace(0,1) / 3
    df["CWL_Efficiency"] = df["CWL_Stars"] / df["CWL_Attempts"].replace(0,1) / 3

    k = 8
    df["War_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["War_Attempts"]/MAX_WAR)-0.5)))
    df["CWL_Participation_Factor"] = 1 / (1 + np.exp(-k * ((df["CWL_Attempts"]/MAX_CWL)-0.5)))

    df["Fair_War_Score"] = df["War_Efficiency"] * df["War_Participation_Factor"]
    df["Fair_CWL_Score"] = df["CWL_Efficiency"] * df["CWL_Participation_Factor"]

    df["Attack_Success_pct"] = ((df["Fair_War_Score"]*0.6 + df["Fair_CWL_Score"]*0.4)*100).round(2)
    df["Gold_Scaled"] = df["ClanCapital_Gold"]/df["ClanCapital_Gold"].max()
    df["Games_Scaled"] = df["ClanGames_Points"]/df["ClanGames_Points"].max()
    df["Events_Scaled"] = df["RushEvents_Participation_pct"]/100

    df["FinalScore"] = (df["Attack_Success_pct"]*0.35 + df["Gold_Scaled"]*25 + df["Games_Scaled"]*20 + df["Events_Scaled"]*20).round(2)
    df["Rank"] = df["FinalScore"].rank(ascending=False, method="min").astype(int)

    return df.sort_values("FinalScore", ascending=False).reset_index(drop=True)

# --- Streamlit UI ---
st.set_page_config(page_title="ClashIntel ⚔️", layout="wide")
st.title("🏆 Top Clan Players Leaderboard")
if st.button("🔄 Refresh Data"):
    st.experimental_rerun()

df = compute_scores(load_player_data())

# --- HTML + CSS ---
html = """
<style>
body { font-family: 'Orbitron', sans-serif; background: #0f0f2e; color: #fff; }
.leaderboard { display: flex; flex-direction: column; gap: 15px; width: 90%; margin: 0 auto; }
.player-row { display: flex; align-items: center; justify-content: space-between; padding: 15px 20px; border-radius: 15px; background: rgba(0,0,0,0.6); box-shadow: 0 0 15px rgba(0,255,255,0.3); flex-wrap: wrap; transition: 0.3s; }
.player-row:hover { transform: scale(1.02); box-shadow: 0 0 25px #00FFFF; }
.rank-badge { width: 50px; height: 50px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; color: #000; background: #00FFFF; margin-right: 15px; flex-shrink: 0; }
.rank-badge.silver { background: #C0C0C0; color: #000; }
.rank-badge.bronze { background: #CD7F32; color: #fff; }
.player-name { font-size: 20px; font-weight: bold; color: #00FFFF; flex: 1; min-width:150px; }
.stats-bar-wrapper { flex: 1; min-width: 150px; margin: 5px 10px; }
.stats-label { font-size: 12px; margin-bottom: 2px; }
.stats-bar-container { width: 100%; background: rgba(255,255,255,0.1); border-radius: 12px; overflow: hidden; height: 20px; }
.stats-bar { height: 100%; text-align: center; padding: 0 5px; color: #000; font-weight: bold; line-height: 20px; border-radius: 12px 0 0 12px; overflow: visible; width: var(--bar-width); }
.attack { background: linear-gradient(90deg, #FF4500, #FF6347); }
.gold { background: linear-gradient(90deg, #FFD700, #FFEA70); }
.games { background: linear-gradient(90deg, #00BFFF, #1E90FF); }
.events { background: linear-gradient(90deg, #32CD32, #7CFC00); }
.final-score { font-weight: bold; min-width:80px; text-align:center; }
@media screen and (max-width: 800px){ .player-row { flex-direction: column; align-items: flex-start; } .stats-bar-wrapper { width: 100%; margin:5px 0; } }
</style>
<div class="leaderboard">
"""

# --- Add player rows ---
for _, row in df.iterrows():
    badge_class = "rank-badge"
    if row['Rank'] == 2: badge_class = "rank-badge silver"
    elif row['Rank'] == 3: badge_class = "rank-badge bronze"

    html += f"""
    <div class="player-row">
        <div class="{badge_class}">{row['Rank']}</div>
        <div class="player-name">{row['Name']}</div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">⚔️ War Stars / Attempts</div>
            <div class="stats-bar-container">
                <div class="stats-bar attack" style="--bar-width:{min((row['War_Stars']/ (row['War_Attempts'] if row['War_Attempts']>0 else 1))*100,100)}%">
                    {int(row['War_Stars'])}/{int(row['War_Attempts'])}
                </div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">🛡️ CWL Stars / Attempts</div>
            <div class="stats-bar-container">
                <div class="stats-bar attack" style="--bar-width:{min((row['CWL_Stars']/ (row['CWL_Attempts'] if row['CWL_Attempts']>0 else 1))*100,100)}%">
                    {int(row['CWL_Stars'])}/{int(row['CWL_Attempts'])}
                </div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">💰 Capital Gold</div>
            <div class="stats-bar-container">
                <div class="stats-bar gold" style="--bar-width:{min(row['Gold_Scaled']*100,100)}%">
                    {int(row['ClanCapital_Gold']):,}
                </div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">🎮 Clan Games</div>
            <div class="stats-bar-container">
                <div class="stats-bar games" style="--bar-width:{min(row['Games_Scaled']*100,100)}%">
                    {int(row['ClanGames_Points']):,}
                </div>
            </div>
        </div>

        <div class="stats-bar-wrapper">
            <div class="stats-label">🎯 Events</div>
            <div class="stats-bar-container">
                <div class="stats-bar events" style="--bar-width:{min(row['Events_Scaled']*100,100)}%">
                    {row['Events_Scaled']*100:.0f}%
                </div>
            </div>
        </div>

        <div class="final-score">{row['FinalScore']:.2f}</div>
    </div>
    """

html += "</div>"

# --- Render HTML ---
components.html(html, height=8000, scrolling=True)
