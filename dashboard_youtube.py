
import os
import json

import psycopg2
import psycopg2.extras

from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user


# YouTube版ダッシュボードのBlueprint
bp = Blueprint('dashboard_youtube', __name__)


def get_db_connection():
    """DB接続を取得"""
    dsn = os.getenv('SUPABASE_DB_URL')

    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL is not set')

    return psycopg2.connect(dsn)


@bp.route('/dashboard_youtube')
@login_required
def dashboard_youtube():

    user_id = current_user.get_id()

    # モニター設定一覧
    monitors = []

    try:
        conn = get_db_connection()

        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        # YouTube版のモニター設定と取得条件を取得
        cur.execute("""
            SELECT
                ms.monitor_id,
                ms.user_id,
                ms.monitor_name,
                ms.keywords,
                ms.notify_email,
                ms.is_enabled,
                ms.created_at,
                ms.updated_at,
                mc.min_views,
                mc.min_likes,
                mc.min_comments
            FROM monitor_settings_y AS ms
            LEFT JOIN monitor_conditions_y AS mc
                ON ms.monitor_id = mc.monitor_id
                AND ms.user_id = mc.user_id
            WHERE ms.user_id = %s
            ORDER BY ms.created_at DESC
        """, (user_id,))

        monitors = cur.fetchall()

        # キーワードの形式を確認
        for monitor in monitors:
            keywords = monitor.get('keywords')

            if isinstance(keywords, str):
                try:
                    monitor['keywords'] = json.loads(keywords)
                except Exception:
                    monitor['keywords'] = []

        cur.close()
        conn.close()

    except Exception as e:
        print(f"YouTube版ダッシュボード取得エラー: {e}")

        flash(
            'YouTube版モニター設定の取得中にエラーが発生しました。',
            'error'
        )

    return render_template(
        'dashboard_youtube.html',
        user_id=user_id,
        user_name=getattr(current_user, 'name', None),
        monitors=monitors
    )
