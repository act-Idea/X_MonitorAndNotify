import os
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

# 環境変数 X_BEARER_TOKEN を取得
bearer = os.getenv("X_BEARER_TOKEN")

# 確認用に表示
print("Bearer Token =", bearer)