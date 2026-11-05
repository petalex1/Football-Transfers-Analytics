import sqlite3
import numpy as np
import pandas as pd

conn = sqlite3.connect('football_analytics.db')


query = """
WITH transfer_history AS (
    SELECT 
        t.player_id,
        t.player_name,
        t.to_club_id,
        t.to_club_name,
        t.transfer_season,
        t.transfer_date AS start_date,
        t.transfer_fee,
        LEAD(t.transfer_date) OVER (PARTITION BY t.player_id ORDER BY t.transfer_date) AS end_date
    FROM transfers t
),
player_spells AS (
    SELECT th.*, p.position, p.sub_position
    FROM transfer_history th
    JOIN players p ON th.player_id = p.player_id
    WHERE th.transfer_fee >= 5000000
      AND (
          LOWER(p.position) = 'attack' 
          OR LOWER(p.sub_position) LIKE '%attacking midfield%'
          OR LOWER(p.sub_position) LIKE '%second striker%'
      )
),
team_matches AS (
    SELECT 
        ps.player_id,
        ps.to_club_id,
        ps.start_date,
        COUNT(DISTINCT a_team.game_id) AS team_total_games
    FROM player_spells ps
    LEFT JOIN appearances a_team 
        ON a_team.player_club_id = ps.to_club_id 
        AND a_team.date >= ps.start_date
        AND (ps.end_date IS NULL OR a_team.date < ps.end_date)
    GROUP BY ps.player_id, ps.to_club_id, ps.start_date
)
SELECT 
    ps.player_id,
    ps.player_name,
    ps.position,
    ps.sub_position,
    ps.to_club_name,
    ps.transfer_season,
    ps.transfer_fee,
    tm.team_total_games,
    COUNT(DISTINCT a.game_id) AS player_matches_played, -- ΕΔΩ: Η SQL πλέον φέρνει τους αγώνες του παίκτη!
    SUM(a.minutes_played) AS total_minutes,
    SUM(a.goals) AS total_goals,
    SUM(a.assists) AS total_assists
FROM player_spells ps
LEFT JOIN appearances a 
    ON a.player_id = ps.player_id 
    AND a.player_club_id = ps.to_club_id 
    AND a.date >= ps.start_date
    AND (ps.end_date IS NULL OR a.date < ps.end_date)
LEFT JOIN team_matches tm
    ON ps.player_id = tm.player_id 
    AND ps.to_club_id = tm.to_club_id 
    AND ps.start_date = tm.start_date
GROUP BY ps.player_id, ps.to_club_id, ps.start_date, ps.transfer_fee, tm.team_total_games
HAVING total_minutes > 0
ORDER BY ps.transfer_fee DESC
LIMIT 100;
"""

df_analysis = pd.read_sql_query(query, conn)



df_analysis['goal_contributions'] = df_analysis['total_goals'] + df_analysis['total_assists']


df_analysis['contributions_per_match'] = df_analysis.apply(
    lambda row: round(row['goal_contributions'] / row['player_matches_played'], 2) if row['player_matches_played'] > 0 else 0,
    axis=1,
)


df_analysis['team_max_minutes'] = df_analysis['team_total_games'] * 90
df_analysis['minutes_played_pct'] = df_analysis.apply(
    lambda row: round((row['total_minutes'] / row['team_max_minutes']) * 100, 1) if row['team_max_minutes'] > 0 else 0,
    axis=1,
)
df_analysis['minutes_played_pct'] = df_analysis['minutes_played_pct'].clip(upper=100.0)


df_analysis['availability_ratio'] = df_analysis['minutes_played_pct'] / 100


df_analysis['effective_contributions_per_match'] = round(
    df_analysis['contributions_per_match'] * df_analysis['availability_ratio'], 2
)


df_analysis['overall_attacker_score'] = round(df_analysis['effective_contributions_per_match'] , 2)


df_analysis['offense_score'] = round(df_analysis['contributions_per_match'] * 100, 1) 

# 4. ΣΥΓΚΡΙΣΗ ΜΕ ΤΗΝ ΤΙΜΗ (VALUE FOR MONEY)
df_analysis['cost_per_effective_contribution'] = df_analysis.apply(
    lambda row: round(row['transfer_fee'] / row['effective_contributions_per_match']/100000000, 2) 
    if row['effective_contributions_per_match'] > 0 else row['transfer_fee'], 
    axis=1
)

df_analysis['player_label'] = df_analysis['player_name'] + ' (' + df_analysis['to_club_name'] + ' - ' + df_analysis['transfer_season'].astype(str) + ')'


pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print(f"\n--- ΤΕΛΙΚΗ ΑΝΑΛΥΣΗ: EFFECTIVE CONTRIBUTIONS & VALUE FOR MONEY ---")
print(
    df_analysis[[
        'player_label',
        'transfer_fee',
        'contributions_per_match',
        'availability_ratio',
        'overall_attacker_score',
        'cost_per_effective_contribution'
    ]].head(15)
)

df_analysis.to_csv('processed_transfer_roi.csv', index=False)
print("\nΤο dataset ολοκληρώθηκε χωρίς errors και είναι έτοιμο: 'processed_transfer_roi.csv'")

conn.close()