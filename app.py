import os
from dotenv import load_dotenv
import psycopg2
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

# --- Flask-Login setup ---
login_manager = LoginManager()
login_manager.login_view = 'home'  # redirect to login page when required
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id, email, user_name=None):
        self.id = str(user_id)
        self.email = email
        self.name = user_name


@login_manager.user_loader
def load_user(user_id):
    """ユーザIDから DB を参照して User オブジェクトを返す"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id, email, user_name FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            uid, email, user_name = row
            return User(uid, email, user_name)
    except Exception:
        app.logger.exception("failed to load user")
    return None

def get_db_connection():
    """DB接続を取得"""
    conn = psycopg2.connect(os.getenv("SUPABASE_DB_URL"))
    return conn

@app.route("/")
def home():
    return render_template("login.html")


# Dashboard and related pages are provided by the dashboard blueprint
from dashboard import bp as dashboard_bp
app.register_blueprint(dashboard_bp)

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
                        # セッションにログイン情報を保存（Flask-Login）
                        user_obj = User(user_id, db_email, user_name)
                        remember_flag = bool(remember)
                        login_user(user_obj, remember=remember_flag)
                        # blueprint 'dashboard' defines the view 'dashboard', so endpoint is 'dashboard.dashboard'
                        return redirect(url_for("dashboard.dashboard"))
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
