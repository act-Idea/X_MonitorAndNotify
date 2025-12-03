import psycopg2

conn = psycopg2.connect(
    "postgresql://postgres.tjuwdwusejfkzceqxgwp:Idea001!@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
)

cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
print(cur.fetchall())

cur.close()
conn.close()
