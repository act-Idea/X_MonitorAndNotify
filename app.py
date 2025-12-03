import os
from dotenv import load_dotenv
import psycopg2
from flask import Flask, render_template, request, flash, redirect, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

def get_db_connection():
    """DB接続を取得"""
    conn = psycopg2.connect(os.getenv("SUPABASE_DB_URL"))
    return conn

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        remember = request.form.get("remember")
        
        # バリデーション
        if not email or not password:
            flash("メールアドレスとパスワードを入力してください。", "error")
            return redirect(url_for("login"))
        
        try:
            # DB接続してユーザー認証
            conn = get_db_connection()
            cur = conn.cursor()
            
            # TODO: 実際のテーブル名とカラム名に合わせて修正
            # 例: SELECT id, password_hash FROM users WHERE email = %s;
            cur.execute(
                "SELECT id, email, password FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user:
                # TODO: パスワードハッシュの検証処理を追加（bcryptやwerkzeugなど）
                # 今は簡易的に直接比較（本番環境では絶対にNG）
                if user[2] == password:  # user[2] はパスワード列と仮定
                    flash(f"ようこそ、{email}さん！", "success")
                    # TODO: セッション/ログイン状態を管理する処理を追加
                    return redirect(url_for("home"))
                else:
                    flash("パスワードが正しくありません。", "error")
            else:
                flash("このメールアドレスは登録されていません。", "error")
        
        except psycopg2.Error as e:
            flash(f"DB接続エラー: {str(e)}", "error")
        except Exception as e:
            flash(f"エラーが発生しました: {str(e)}", "error")
        
        return redirect(url_for("login"))
    
    # GET リクエスト時はログインフォームを表示
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
