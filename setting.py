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
                SELECT
                    ms.monitor_id,
                    ms.user_id,
                    ms.monitor_name,
                    ms.keywords,
                    ms.notify_email,
                    ms.is_enabled,
                    ms.created_at,
                    ms.updated_at,
                    mc.min_followers,
                    mc.min_impressions,
                    mc.post_type_image,
                    mc.post_type_video,
                    mc.post_type_link
                FROM
                    monitor_settings AS ms
                INNER JOIN
                    monitor_conditions AS mc
                    ON ms.monitor_id = mc.monitor_id
                    AND ms.user_id = mc.user_id
                WHERE ms.monitor_id = %s AND ms.user_id = %s
                """,
                (monitor_id, current_user.get_id())
            )
            monitor_data = cur.fetchone()
            if monitor_data and isinstance(monitor_data['keywords'], str):
                monitor_data['keywords'] = json.loads(monitor_data['keywords'])
            # post_types をリストにまとめる
            if monitor_data:
                monitor_data['post_types'] = []
                if monitor_data.get('post_type_image'):
                    monitor_data['post_types'].append('image')
                if monitor_data.get('post_type_video'):
                    monitor_data['post_types'].append('video')
                if monitor_data.get('post_type_link'):
                    monitor_data['post_types'].append('link')
                # 古いカラム名に合わせる
                monitor_data['followers_min'] = monitor_data.get('min_followers', 0)
                monitor_data['views_min'] = monitor_data.get('min_impressions', 0)
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
            # バリデーションエラー時にフォームの値を保持
            keywords_list = [kw.strip() for kw in keyword_str.split(',') if kw.strip()]
            form_data = {
                'monitor_name': monitor_name,
                'keywords': keywords_list,
                'notify_email': email,
                'followers_min': int(followers) if followers else 0,
                'views_min': int(views) if views else 0,
                'post_types': post_types,
                'is_enabled': is_enabled
            }
            return render_template('setting.html', monitor_data=form_data)
        
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
                        is_enabled = %s, updated_at = NOW()
                    WHERE monitor_id = %s AND user_id = %s
                    """,
                    (monitor_name, json.dumps(keywords), email, is_enabled,
                     monitor_id, current_user.get_id())
                )
                cur.execute(
                    """
                    UPDATE monitor_conditions
                    SET min_followers = %s, min_impressions = %s,
                        post_type_image = %s, post_type_video = %s, post_type_link = %s
                    WHERE monitor_id = %s AND user_id = %s
                    """,
                    (int(followers) if followers else 0, int(views) if views else 0,
                     'image' in post_types, 'video' in post_types, 'link' in post_types,
                     monitor_id, current_user.get_id())
                )
                flash('モニター設定を更新しました。', 'success')
            else:
                # 新規作成
                # monitor_id を生成（ユーザーごとの最大値 + 1）
                cur.execute("SELECT COALESCE(MAX(monitor_id), 0) + 1 FROM monitor_settings WHERE user_id = %s", (current_user.get_id(),))
                new_monitor_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO monitor_settings
                    (monitor_id, user_id, monitor_name, keywords, notify_email, is_enabled, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (new_monitor_id, current_user.get_id(), monitor_name, json.dumps(keywords), email, is_enabled)
                )
                cur.execute(
                    """
                    INSERT INTO monitor_conditions
                    (monitor_id, user_id, min_followers, min_impressions, post_type_image, post_type_video, post_type_link)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (new_monitor_id, current_user.get_id(),
                     int(followers) if followers else 0, int(views) if views else 0,
                     'image' in post_types, 'video' in post_types, 'link' in post_types)
                )
                flash('モニター設定を追加しました。', 'success')
            
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('dashboard.dashboard'))
        
        except Exception as e:
            flash(f'保存中にエラーが発生しました: {str(e)}', 'error')
            # DBエラー時にもフォームの値を保持
            form_data = {
                'monitor_name': monitor_name,
                'keywords': keywords,
                'notify_email': email,
                'followers_min': int(followers) if followers else 0,
                'views_min': int(views) if views else 0,
                'post_types': post_types,
                'is_enabled': is_enabled
            }
            return render_template('setting.html', monitor_data=form_data)
    
    # GET リクエスト時も POST リクエスト時も monitor_data を渡す
    return render_template('setting.html', monitor_data=monitor_data)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("setting.html")

if __name__ == "__main__":
    app.run(debug=True)