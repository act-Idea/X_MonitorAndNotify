from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, logout_user, current_user
import os
import psycopg2
import psycopg2.extras
import json

bp = Blueprint('dashboard', __name__)


def get_db_connection():
    """ダッシュボード専用のDB接続（簡易）"""
    dsn = os.getenv('SUPABASE_DB_URL')
    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL is not set')
    return psycopg2.connect(dsn)


@bp.route('/dashboard')
@login_required
def dashboard():
    # current_user is available via Flask-Login
    user_id = current_user.get_id()
    monitors = []
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT monitor_id, user_id, monitor_name, keywords, notify_email, is_enabled, created_at, updated_at
            FROM monitor_settings
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )
        rows = cur.fetchall()
        # ensure keywords is a Python object (list)
        for r in rows:
            kw = r.get('keywords')
            if isinstance(kw, str):
                try:
                    r['keywords'] = json.loads(kw)
                except Exception:
                    r['keywords'] = []
        monitors = rows
        cur.close()
        conn.close()
    except Exception as e:
        app_logger = getattr(__import__('flask').current_app, 'logger', None)
        if app_logger:
            app_logger.exception('failed to fetch monitor_settings')
        flash('モニター設定の取得中にエラーが発生しました。', 'error')

    return render_template('dashboard.html', user_id=user_id, user_name=getattr(current_user, 'name', None), monitors=monitors)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。', 'success')
    return redirect(url_for('home'))


@bp.route('/monitor/<int:monitor_id>/toggle', methods=['POST'])
@login_required
def toggle_monitor(monitor_id):
    """トグルでモニター有効状態を更新"""
    from flask import jsonify, request
    data = request.get_json(silent=True) or {}
    if 'is_enabled' not in data:
        return jsonify({'success': False, 'error': 'missing is_enabled'}), 400
    
    is_enabled = bool(data.get('is_enabled'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # verify ownership
        cur.execute("SELECT user_id FROM monitor_settings WHERE monitor_id = %s", (monitor_id,))
        row = cur.fetchone()
        if not row or str(row[0]) != str(current_user.get_id()):
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'not found or unauthorized'}), 404

        cur.execute(
            "UPDATE monitor_settings SET is_enabled = %s, updated_at = NOW() WHERE monitor_id = %s",
            (is_enabled, monitor_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'is_enabled': is_enabled})
    except Exception as e:
        app_logger = getattr(__import__('flask').current_app, 'logger', None)
        if app_logger:
            app_logger.exception('failed to toggle monitor %s', monitor_id)
        return jsonify({'success': False, 'error': 'server error'}), 500