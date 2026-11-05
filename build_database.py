import sqlite3
import pandas as pd
import os

# 1. Σύνδεση στη βάση δεδομένων (αν δεν υπάρχει, δημιουργείται αυτόματα)
db_path = 'football_analytics.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Η σύνδεση με τη βάση SQLite ενεργοποιήθηκε!")

# 2. Λίστα με τα αρχεία που θέλουμε να φορτώσουμε
files = {
    'players': 'data/players.csv',
    'transfers': 'data/transfers.csv',
    'appearances': 'data/appearances.csv',
    'player_valuations': 'data/player_valuations.csv',
    'clubs': 'data/clubs.csv'
}

# 3. Φόρτωση κάθε CSV σε πίνακα της SQLite
for table_name, file_path in files.items():
    if os.path.exists(file_path):
        print(f"Φόρτωση του {file_path} στον πίνακα '{table_name}'...")
        # Διαβάζουμε το CSV σε chunks αν είναι πολύ μεγάλο (π.χ. appearances.csv)
        df = pd.read_csv(file_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Ο πίνακας '{table_name}' δημιουργήθηκε με επιτυχία ({len(df):,} εγγραφές).")
    else:
        print(f"Προσοχή: Το αρχείο {file_path} δεν βρέθηκε!")

conn.close()
print("\nΗ βάση δεδομένων 'football_analytics.db' είναι έτοιμη!")