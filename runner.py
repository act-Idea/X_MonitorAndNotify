import os
import sys
import subprocess
import json
from pathlib import Path
from flask import Flask, render_template, request, session

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

PROJECT_ROOT = Path(__file__).resolve().parent
TEST_SCRIPT = PROJECT_ROOT / "view_tweets.py"


@app.route("/test_run", methods=["GET"])
def test_run_start():
    """起動画面: 実行ボタンを表示"""
    error = request.args.get("error", "")
    countdown_seconds = session.get('countdown_seconds', 0)
    return render_template("runner_start.html", error=error, countdown_seconds=countdown_seconds)


@app.route("/test_run/run", methods=["POST"])
def test_run_execute():
    """ボタン押下で `python test_tweets.py` をサブプロセス実行し、出力をキャプチャして表示する。"""
    # フォームから渡された検索ワードがあれば引数で渡す
    query = request.form.get("query", "").strip()
    if not query:
        return render_template("runner_start.html", error="検索ワードを入力してください。")

    if not TEST_SCRIPT.exists():
        return render_template("view_tweets.html", output="[ERROR] view_tweets.py が見つかりません。",
                               returncode=1, stderr="")

    # 実行コマンド（同じ Python 実行環境を使う）
    
    cmd = [sys.executable, str(TEST_SCRIPT)]
    # cmd = [sys.executable, str(TEST_SCRIPT), "--mock"]
    # フォームから渡された検索ワードがあれば引数で渡す
    if query:
        cmd.append(query)
    try:
        completed = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8", timeout=60)
        output = completed.stdout or ""
        stderr = completed.stderr or ""
        returncode = completed.returncode
        # 出力から RATELIMIT_SECONDS:<n> を探す
        import re
        countdown_seconds = None
        m = re.search(r"RATELIMIT_SECONDS:(\d+)", output)
        if not m:
            m = re.search(r"RATELIMIT_SECONDS:(\d+)", stderr)
        if m:
            try:
                countdown_seconds = int(m.group(1))
            except Exception:
                countdown_seconds = None
        
        # 出力から JSON を抽出してパース
        tweets = []
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                tweets = data.get("data", [])
            except json.JSONDecodeError:
                pass
        
        # セッションにカウントダウンを保存
        session['countdown_seconds'] = countdown_seconds or 0
    except subprocess.TimeoutExpired as e:
        output = e.stdout or ""
        stderr = (e.stderr or "") + "\n[ERROR] 実行がタイムアウトしました。"
        returncode = 124
    except Exception as e:
        output = ""
        stderr = f"[ERROR] 実行失敗: {e}"
        returncode = 2

    return render_template("view_tweets.html", output=output, stderr=stderr, returncode=returncode, countdown_seconds=countdown_seconds, tweets=tweets, query=query)


if __name__ == "__main__":
    # ポート 5004 を使用（他と衝突しないように）
    app.run(debug=True, port=5004, host='0.0.0.0')
