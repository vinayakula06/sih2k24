import sqlite3
import pandas as pd
df = pd.read_csv('VSKP.csv')
conn = sqlite3.connect('bo_po_data.db')
df.to_sql('postal_data', conn, if_exists='replace', index=False)
conn.close()
