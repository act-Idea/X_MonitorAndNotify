import os
# 必要に応じて追加のインポート　pip install python-dotenv
from dotenv import load_dotenv
import psycopg2

load_dotenv()
conn = psycopg2.connect(os.getenv("SUPABASE_DB_URL"))

cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
print(cur.fetchall())

cur.close()
conn.close()
