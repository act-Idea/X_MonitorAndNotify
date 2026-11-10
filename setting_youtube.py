
import os
import json

import psycopg2
import psycopg2.extras

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user


# YouTube版モニター設定のBlueprint
bp = Blueprint('setting_youtube', __name__)


def get_db_connection():
    """DB接続を取得"""
    dsn = os.getenv('SUPABASE_DB_URL')

    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL is not set')

    return psycopg2.connect(dsn)


def get_optional_int(value, label):
    """数値が入力されていれば整数に変換する"""
    value = value.strip()

    if value == '':
        return None

    try:
        number = int(value)
    except ValueError:
        raise ValueError(f'{label}は整数で入力してください。')

    if number < 0:
        raise ValueError(f'{label}は0以上で入力してください。')

    return number


@bp.route('/youtube/setting', methods=['GET', 'POST'])
@login_required
def setting_youtube():

    user_id = current_user.get_id()

    # 編集時のモニターID
    monitor_id = request.args.get('id', type=int)

    # POST時はフォームのIDも確認
    if request.method == 'POST':
        monitor_id = request.form.get('monitor_id', type=int) or monitor_id

    monitor = None

    try:
        conn = get_db_connection()

        try:
            with conn:
                with conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as cur:

                    # --------------------------------
                    # POST：新規登録・編集
                    # --------------------------------
                    if request.method == 'POST':

                        monitor_name = request.form.get(
                            'monitor_name', ''
                        ).strip()

                        keywords_text = request.form.get(
                            'keywords', ''
                        ).strip()

                        notify_email = request.form.get(
                            'notify_email', ''
                        ).strip()

                        # キーワードを1行ずつリストにする
                        keywords = [
                            keyword.strip()
                            for keyword in keywords_text.splitlines()
                            if keyword.strip()
                        ]

                        # 入力チェック
                        if not monitor_name:
                            raise ValueError('モニター名を入力してください。')

                        if not keywords:
                            raise ValueError('検索キーワードを1つ以上入力してください。')

                        if len(monitor_name) > 100:
                            raise ValueError('モニター名は100文字以内で入力してください。')

                        if notify_email == '':
                            notify_email = None

                        min_views = get_optional_int(
                            request.form.get('min_views', ''),
                            '最低再生回数'
                        )

                        min_likes = get_optional_int(
                            request.form.get('min_likes', ''),
                            '最低いいね数'
                        )

                        min_comments = get_optional_int(
                            request.form.get('min_comments', ''),
                            '最低コメント数'
                        )

                        # 編集の場合
                        if monitor_id:

                            cur.execute("""
                                UPDATE monitor_settings_y
                                SET
                                    monitor_name = %s,
                                    keywords = %s,
                                    notify_email = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE monitor_id = %s
                                  AND user_id = %s
                                RETURNING monitor_id
                            """, (
                                monitor_name,
                                psycopg2.extras.Json(keywords),
                                notify_email,
                                monitor_id,
                                user_id
                            ))

                            updated = cur.fetchone()

                            if not updated:
                                raise ValueError('編集対象のモニター設定が見つかりません。')

                            # 取得条件を更新
                            cur.execute("""
                                INSERT INTO monitor_conditions_y (
                                    monitor_id,
                                    user_id,
                                    min_views,
                                    min_likes,
                                    min_comments
                                )
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (monitor_id, user_id)
                                DO UPDATE SET
                                    min_views = EXCLUDED.min_views,
                                    min_likes = EXCLUDED.min_likes,
                                    min_comments = EXCLUDED.min_comments
                            """, (
                                monitor_id,
                                user_id,
                                min_views,
                                min_likes,
                                min_comments
                            ))

                            flash('モニター設定を更新しました。', 'success')

                        # 新規登録の場合
                        else:

                            cur.execute("""
                                INSERT INTO monitor_settings_y (
                                    user_id,
                                    monitor_name,
                                    keywords,
                                    notify_email
                                )
                                VALUES (%s, %s, %s, %s)
                                RETURNING monitor_id
                            """, (
                                user_id,
                                monitor_name,
                                psycopg2.extras.Json(keywords),
                                notify_email
                            ))

                            new_monitor = cur.fetchone()
                            new_monitor_id = new_monitor['monitor_id']

                            # 取得条件を登録
                            cur.execute("""
                                INSERT INTO monitor_conditions_y (
                                    monitor_id,
                                    user_id,
                                    min_views,
                                    min_likes,
                                    min_comments
                                )
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                new_monitor_id,
                                user_id,
                                min_views,
                                min_likes,
                                min_comments
                            ))

                            flash('モニター設定を登録しました。', 'success')

                        return redirect(url_for('dashboard_youtube.dashboard_youtube'))

                    # --------------------------------
                    # GET：編集画面の初期表示
                    # --------------------------------
                    if monitor_id:

                        cur.execute("""
                            SELECT
                                ms.monitor_id,
                                ms.monitor_name,
                                ms.keywords,
                                ms.notify_email,
                                mc.min_views,
                                mc.min_likes,
                                mc.min_comments
                            FROM monitor_settings_y AS ms
                            LEFT JOIN monitor_conditions_y AS mc
                                ON ms.monitor_id = mc.monitor_id
                                AND ms.user_id = mc.user_id
                            WHERE ms.monitor_id = %s
                              AND ms.user_id = %s
                        """, (monitor_id, user_id))

                        monitor = cur.fetchone()

                        if not monitor:
                            flash('指定されたモニター設定が見つかりません。', 'error')
                            return redirect(url_for('dashboard_youtube.dashboard_youtube'))

                        # キーワードがJSON文字列の場合に備える
                        keywords = monitor.get('keywords')

                        if isinstance(keywords, str):
                            try:
                                monitor['keywords'] = json.loads(keywords)
                            except Exception:
                                monitor['keywords'] = []

        finally:
            conn.close()

    except ValueError as e:
        flash(str(e), 'error')

        return render_template(
            'setting_youtube.html',
            user_id=user_id,
            user_name=getattr(current_user, 'name', None),
            monitor=monitor
        )

    except Exception:
        current_app.logger.exception(
            'YouTube版モニター設定処理エラー'
        )

        flash(
            'モニター設定の処理中にエラーが発生しました。',
            'error'
        )

        return redirect(url_for('dashboard_youtube.dashboard_youtube'))

    return render_template(
        'setting_youtube.html',
        user_id=user_id,
        user_name=getattr(current_user, 'name', None),
        monitor=monitor
    )
