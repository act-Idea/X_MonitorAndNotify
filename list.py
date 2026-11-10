import os
from flask import Flask, Blueprint, render_template, request
from flask_login import login_required, current_user
import psycopg2
import psycopg2.extras
import json

app = Flask(__name__)
bp = Blueprint('list', __name__)
RESULTS_PER_PAGE = 9

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
    requested_page = request.args.get('page', default=1, type=int) or 1
    monitor_name = 'モニター設定'
    results_data = []
    total_count = 0
    total_pages = 1
    page = max(1, requested_page)
    
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
            
            cur.execute(
                """
                SELECT COUNT(*) AS total_count
                FROM monitor_results
                WHERE monitor_id = %s
                """,
                (monitor_id,)
            )
            total_count = cur.fetchone()['total_count']
            total_pages = max(1, (total_count + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
            page = min(page, total_pages)
            offset = (page - 1) * RESULTS_PER_PAGE

            cur.execute(
                """
                SELECT result_id, monitor_id, user_id, post_id,
                       user_handle, content, hashtags, image_url,
                       post_url,
                       to_char(posted_at, 'YYYY-MM-DD HH24:MI:SS') AS posted_at,
                       to_char(detected_at, 'YYYY-MM-DD HH24:MI:SS') AS detected_at
                FROM monitor_results
                WHERE monitor_id = %s
                ORDER BY posted_at DESC, result_id DESC
                LIMIT %s OFFSET %s
                """,
                (monitor_id, RESULTS_PER_PAGE, offset)
            )
            results_data = cur.fetchall()
            for result in results_data:
                image_urls = result.get('image_url')
                if isinstance(image_urls, str):
                    try:
                        image_urls = json.loads(image_urls)
                    except json.JSONDecodeError:
                        image_urls = [image_urls]
                if isinstance(image_urls, str):
                    image_urls = [image_urls]
                result['image_urls'] = (
                    [url for url in image_urls if isinstance(url, str) and url]
                    if isinstance(image_urls, list)
                    else []
                )
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching results: {e}")
            results_data = []
    
    return render_template(
        'list.html',
        monitor_name=monitor_name,
        results=results_data,
        monitor_id=monitor_id,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )

if __name__ == "__main__":
    app.run(debug=True)