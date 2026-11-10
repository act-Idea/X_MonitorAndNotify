import os
import smtplib
import psycopg2
from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash

# .env ファイルを明示的に読み込む
env_file = Path(__file__).parent / ".env_app"
load_dotenv(env_file)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
MAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER or "no-reply@example.com")
MAIL_TO = os.getenv("MAIL_TO", "act.aida@outlook.jp")

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


def send_email(to: str, subject: str, body: str) -> None:
    """シンプルなテキストメール送信"""
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)


def send_password_reset_notice(target_email: str) -> None:
    """パスワード再設定依頼の通知メールを管理者宛に送信する"""
    body = (
        "入力されたメールアドレスのユーザがパスワードを失効したので、再設定をお願いします。\n\n"
        f"対象メールアドレス: {target_email}"
    )
    send_email(MAIL_TO, "パスワード再設定依頼", body)

@app.route("/")
def home():
    return render_template("login.html")


# Dashboard and related pages are provided by the dashboard blueprint
from dashboard import bp as dashboard_bp
app.register_blueprint(dashboard_bp)

# Setting page blueprint を追加
from setting import bp as setting_bp
app.register_blueprint(setting_bp)

# List page blueprint を追加
from list import bp as list_bp
app.register_blueprint(list_bp)


# YouTube版 Dashboard blueprint を追加
from dashboard_youtube import bp as dashboard_youtube_bp
app.register_blueprint(dashboard_youtube_bp)

# YouTube版 Setting blueprint を追加
from setting_youtube import bp as setting_youtube_bp
app.register_blueprint(setting_youtube_bp)

# YouTube版 List blueprint を追加
from list_youtube import bp as list_youtube_bp
app.register_blueprint(list_youtube_bp)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        remember = request.form.get("remember")
        
        # バリデーション
        if not email or not password:
            flash("メールアドレスとパスワードを入力してください。", "error")
            return render_template("login.html", email=email, remember=remember)
        
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
                try:
                    if check_password_hash(password_hash, password):
                        flash(f"ようこそ、{user_name or db_email}さん！", "success")
                        # セッションにログイン情報を保存（Flask-Login）
                        user_obj = User(user_id, db_email, user_name)
                        remember_flag = bool(remember)
                        login_user(user_obj, remember=remember_flag)
                        # blueprint 'dashboard' defines the view 'dashboard.dashboard'
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
            app.logger.exception("forgot password process failed")
            flash(f"エラーが発生しました: {str(e)}", "error")
        
        return render_template("login.html", email=email, remember=remember)
    
    # GET リクエスト時はログインフォームを表示
    return render_template("login.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            flash("メールアドレスを入力してください。", "error")
            return render_template("forgot.html", email=email)

        try:
            send_password_reset_notice(email)
            flash("管理者宛に通知メールを送信しました。再設定完了までお待ちください。", "success")
            return render_template("forgot.html", email=email)
        except Exception as e:
            app.logger.exception("forgot password process failed")
            flash(f"メール送信中にエラーが発生しました: {str(e)}", "error")
            return render_template("forgot.html", email=email)

    return render_template("forgot.html")

if __name__ == "__main__":
    app.run(debug=True)
