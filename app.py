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


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/setting")
def setting_page():
    return render_template("setting.html")


@app.route("/list")
def list_page():
    return render_template("list.html")

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
            
            # 実際のテーブル定義に合わせたクエリ
            # テーブル定義:
            # user_id PK, email UNIQUE NOT NULL, password_hash NOT NULL, user_name, created_at, updated_at
            cur.execute(
                "SELECT user_id, email, password_hash, user_name FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()  # None or tuple(user_id, email, password_hash, user_name)
            cur.close()
            conn.close()
            
            if user:
                user_id, db_email, password_hash, user_name = user
                # パスワードハッシュの検証
                # 簡易比較: 入力値とDBから取得した値が完全一致ならログイン成功とする（開発用、一時対応）
                try:
                    if password_hash == password:
                        flash(f"ようこそ、{user_name or db_email}さん！", "success")
                        # TODO: セッション/ログイン状態を管理する処理を追加（Flask-Login など）
                        return redirect(url_for("dashboard"))
                    else:
                        flash("パスワードが正しくありません。", "error")
                except Exception as e:
                    app.logger.exception("password comparison error")
                    flash("パスワード検証中にエラーが発生しました。", "error")
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
