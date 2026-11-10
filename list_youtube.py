
import os
import json
import math

import psycopg2
import psycopg2.extras

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user


# YouTube版モニター結果一覧のBlueprint
bp = Blueprint('list_youtube', __name__)


def get_db_connection():
    """DB接続を取得"""
    dsn = os.getenv('SUPABASE_DB_URL')

    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL is not set')

    return psycopg2.connect(dsn)


@bp.route('/youtube/results')
@login_required
def results_youtube():

    user_id = current_user.get_id()

    # URLからモニターIDとページ番号を取得
    monitor_id = request.args.get('monitor', type=int)
    page = request.args.get('page', 1, type=int)

    # ページ番号が1未満の場合は1にする
    if page is None or page < 1:
        page = 1

    # 1ページに表示する件数
    per_page = 9

    if not monitor_id:
        flash('モニターが指定されていません。', 'error')
        return redirect(url_for('dashboard_youtube.dashboard_youtube'))

    monitor = None
    results = []
    total_count = 0
    total_pages = 0

    try:
        conn = get_db_connection()

        try:
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:

                # --------------------------------
                # モニター情報を取得
                # --------------------------------
                cur.execute("""
                    SELECT
                        monitor_id,
                        user_id,
                        monitor_name,
                        keywords
                    FROM monitor_settings_y
                    WHERE monitor_id = %s
                      AND user_id = %s
                """, (
                    monitor_id,
                    user_id
                ))

                monitor = cur.fetchone()

                # 自分のモニター設定でなければ表示しない
                if not monitor:
                    flash('指定されたモニター設定が見つかりません。', 'error')
                    return redirect(
                        url_for('dashboard_youtube.dashboard_youtube')
                    )

                # キーワードの形式を確認
                keywords = monitor.get('keywords')

                if isinstance(keywords, str):
                    try:
                        monitor['keywords'] = json.loads(keywords)
                    except Exception:
                        monitor['keywords'] = []

                # --------------------------------
                # 検知結果の全件数を取得
                # --------------------------------
                cur.execute("""
                    SELECT COUNT(*) AS total_count
                    FROM monitor_results_y
                    WHERE monitor_id = %s
                      AND user_id = %s
                """, (
                    monitor_id,
                    user_id
                ))

                total_count = cur.fetchone()['total_count']

                # 総ページ数を計算
                total_pages = math.ceil(total_count / per_page)

                # ページ番号が総ページ数を超えていた場合
                if total_pages > 0 and page > total_pages:
                    page = total_pages

                # --------------------------------
                # モニター結果一覧を取得
                # --------------------------------
                offset = (page - 1) * per_page

                cur.execute("""
                    SELECT
                        result_id,
                        monitor_id,
                        user_id,
                        video_id,
                        video_title,
                        video_description,
                        channel_id,
                        channel_title,
                        thumbnail_url,
                        video_url,
                        published_at,
                        view_count,
                        like_count,
                        comment_count,
                        detected_at
                    FROM monitor_results_y
                    WHERE monitor_id = %s
                      AND user_id = %s
                    ORDER BY detected_at DESC
                    LIMIT %s OFFSET %s
                """, (
                    monitor_id,
                    user_id,
                    per_page,
                    offset
                ))

                results = cur.fetchall()

        finally:
            conn.close()

    except Exception:
        current_app.logger.exception(
            'YouTube版モニター結果取得エラー'
        )

        flash(
            'YouTube版モニター結果の取得中にエラーが発生しました。',
            'error'
        )

        return redirect(
            url_for('dashboard_youtube.dashboard_youtube')
        )

    # --------------------------------
    # 結果一覧画面を表示
    # --------------------------------
    return render_template(
        'list_youtube.html',
        user_id=user_id,
        user_name=getattr(current_user, 'name', None),
        monitor=monitor,
        monitor_id=monitor_id,
        monitor_name=monitor['monitor_name'],
        results=results,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )
