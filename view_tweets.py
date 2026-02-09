import os
import sys
import requests
import json   
import time
from pathlib import Path


# 標準出力/標準エラーのエンコーディングを UTF-8 に設定し、
# 表示できない文字は置換する（Windows の cp932 環境での UnicodeEncodeError 対策）
try:
    # Python 3.7+ の場合
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    try:
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        # どの方法でも設定できなければ無視（最低限例外は出ないように）
        pass

# 環境変数から Bearer Token を取得
BEARER = os.getenv("X_BEARER_TOKEN")

# ツイート検索用URL（公式API v2）
SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# スタブファイルのパス
STUB_FILE = Path("stub_tweet.json")

# ヘッダに Bearer Token を設定
headers = {
    "Authorization": f"Bearer {BEARER}"
}

# 検索ワードはコマンドライン引数、もしくは環境変数 `X_QUERY` から取得可能
default_query = ""  # デフォルトは空（画面入力に頼る）
cli_query = None
if len(sys.argv) > 1:
    cli_query = sys.argv[1]
env_query = os.getenv("X_QUERY")
query = cli_query or env_query or default_query

if not query:
    print("[ERROR] 検索ワードが指定されていません。")
    sys.exit(1)

# 検索条件
params = {
    "query": query,
    "max_results": 10,
    "tweet.fields": "public_metrics",
    "user.fields": "id,name,username,profile_image_url,verified,created_at"
}

# APIを呼び出す
response = requests.get(SEARCH_URL, headers=headers, params=params)

# # 結果のステータスコードを表示
# print("ステータスコード:", response.status_code)

# print("ステータスコード:", response.status_code)

# # レスポンスヘッダに制限情報が含まれている
# print("X-Rate-Limit-Limit:", response.headers.get("x-rate-limit-limit"))
# print("X-Rate-Limit-Remaining:", response.headers.get("x-rate-limit-remaining"))
# print("X-Rate-Limit-Reset:", response.headers.get("x-rate-limit-reset"))

# 成功すればツイートのJSONを表示

USE_MOCK = "--mock" in sys.argv or STUB_FILE.exists()
if USE_MOCK:
    # スタブデータを使う
    try:
        with open(STUB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("[INFO] MOCK MODE ENABLED (API is not called)")
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except FileNotFoundError:
        print("[WARNING] stub_tweets.json not found, falling back to API call")
        USE_MOCK = False

if not USE_MOCK:
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=4, ensure_ascii=False))
    elif response.status_code == 429:
        # レート制限に引っかかった場合
        reset_time = int(response.headers.get("x-rate-limit-reset", 0))
        current_time = int(time.time())
        wait_seconds = max(0, reset_time - current_time)
        wait_minutes = wait_seconds // 60
        wait_seconds_remainder = wait_seconds % 60
        print(f"[WARNING] Rate limit reached. Please wait {wait_minutes} minutes and {wait_seconds_remainder} seconds before retrying.")
        # 機械的にパースしやすい行を追加（秒数）。test_runner がこれを探してカウントダウン表示します。
        print(f"RATELIMIT_SECONDS:{wait_seconds}")
        
    else:
        print("API呼び出し失敗:", response.text)
