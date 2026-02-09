import os
from flask import Blueprint, Flask, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
import psycopg2
import psycopg2.extras
import json

bp = Blueprint('setting', __name__)

def get_db_connection():
    """DB接続を取得"""
    dsn = os.getenv('SUPABASE_DB_URL')
    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL is not set')
    return psycopg2.connect(dsn)

@bp.route('/setting', methods=['GET', 'POST'])
@login_required
def setting():
    monitor_id = request.args.get('id')  # 編集時のモニターID
    monitor_data = None
    
    if monitor_id:
        # 編集モード：既存データを取得
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                SELECT monitor_id, monitor_name, keywords, notify_email, 
                       followers_min, views_min, post_types, is_enabled
                FROM monitor_settings
                WHERE monitor_id = %s AND user_id = %s
                """,
                (monitor_id, current_user.get_id())
            )
            monitor_data = cur.fetchone()
            if monitor_data and isinstance(monitor_data['keywords'], str):
                monitor_data['keywords'] = json.loads(monitor_data['keywords'])
            if monitor_data and isinstance(monitor_data['post_types'], str):
                monitor_data['post_types'] = json.loads(monitor_data['post_types'])
            cur.close()
            conn.close()
        except Exception as e:
            flash('モニター設定の読み込みに失敗しました。', 'error')
    
    if request.method == 'POST':
        monitor_name = request.form.get('monitor_name', '').strip()
        keyword_str = request.form.get('keyword', '').strip()
        email = request.form.get('email', '').strip()
        followers = request.form.get('followers', 0)
        views = request.form.get('views', 0)
        post_types = request.form.getlist('type')
        is_enabled = request.form.get('enabled') == 'on'
        
        # バリデーション
        if not monitor_name or not keyword_str:
            flash('モニター名とキーワードは必須です。', 'error')
            return render_template('setting.html', monitor_data=monitor_data)
        
        # キーワードをリストに変換
        keywords = [kw.strip() for kw in keyword_str.split(',') if kw.strip()]
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            if monitor_id:
                # 更新
                cur.execute(
                    """
                    UPDATE monitor_settings
                    SET monitor_name = %s, keywords = %s, notify_email = %s,
                        followers_min = %s, views_min = %s, post_types = %s,
                        is_enabled = %s, updated_at = NOW()
                    WHERE monitor_id = %s AND user_id = %s
                    """,
                    (monitor_name, json.dumps(keywords), email,
                     int(followers) if followers else 0,
                     int(views) if views else 0,
                     json.dumps(post_types), is_enabled,
                     monitor_id, current_user.get_id())
                )
                flash('モニター設定を更新しました。', 'success')
            else:
                # 新規作成
                cur.execute(
                    """
                    INSERT INTO monitor_settings
                    (user_id, monitor_name, keywords, notify_email, followers_min, 
                     views_min, post_types, is_enabled, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (current_user.get_id(), monitor_name, json.dumps(keywords), email,
                     int(followers) if followers else 0,
                     int(views) if views else 0,
                     json.dumps(post_types), is_enabled)
                )
                flash('モニター設定を追加しました。', 'success')
            
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('dashboard.dashboard'))
        
        except Exception as e:
            flash(f'保存中にエラーが発生しました: {str(e)}', 'error')
    
    # GET リクエスト時も POST リクエスト時も monitor_data を渡す
    return render_template('setting.html', monitor_data=monitor_data)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("setting.html")

if __name__ == "__main__":
    app.run(debug=True)