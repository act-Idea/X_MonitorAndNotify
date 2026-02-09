import os
from flask import Flask, Blueprint, render_template, request
from flask_login import login_required, current_user
import psycopg2
import psycopg2.extras
import json

app = Flask(__name__)
bp = Blueprint('list', __name__)

def get_db_connection():
    """DB接続を取得"""
    dsn = os.getenv('SUPABASE_DB_URL')
    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL is not set')
    return psycopg2.connect(dsn)

@app.route("/")
def home():
    return render_template("list.html")

@bp.route('/results')
@login_required
def results():
    monitor_id = request.args.get('monitor')
    monitor_name = 'モニター設定'
    results_data = []
    
    if monitor_id:
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # モニター設定情報を取得
            cur.execute(
                """
                SELECT monitor_name FROM monitor_settings
                WHERE monitor_id = %s AND user_id = %s
                """,
                (monitor_id, current_user.get_id())
            )
            monitor = cur.fetchone()
            if monitor:
                monitor_name = monitor['monitor_name']
            
            # 検知結果を取得（テーブル名は実装に合わせて調整してください）
            cur.execute(
                """
                SELECT result_id, post_content, username, followers_count, 
                       views_count, posted_at, post_url
                FROM monitor_results
                WHERE monitor_id = %s
                ORDER BY posted_at DESC
                LIMIT 50
                """,
                (monitor_id,)
            )
            results_data = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching results: {e}")
            results_data = []
    
    return render_template('list.html', monitor_name=monitor_name, results=results_data)

if __name__ == "__main__":
    app.run(debug=True)