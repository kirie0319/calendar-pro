import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

class Settings:
    """アプリケーション設定"""
    
    # データベース設定
    DATABASE_URL: str = os.getenv('DATABASE_URL')
    
    # アプリケーション設定
    BASE_URL: str = os.getenv('BASE_URL', 'http://localhost:8000')
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'https://calendar-pro-frontend.vercel.app')
    
    # Google OAuth設定
    GOOGLE_CLIENT_ID: str = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET: str = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI: str = os.getenv('GOOGLE_REDIRECT_URI')
    
    # セッション設定
    SECRET_KEY: str = os.getenv('SECRET_KEY')
    SESSION_MAX_AGE: int = 86400  # 24時間
    
    def __init__(self):
        """設定初期化時のバリデーション"""
        print(f"🔍 SECRET_KEY loaded: {'***' + self.SECRET_KEY[-4:] if self.SECRET_KEY else 'None'}")
        print(f"🔍 GOOGLE_CLIENT_ID loaded: {'***' + self.GOOGLE_CLIENT_ID[-4:] if self.GOOGLE_CLIENT_ID else 'None'}")
        print(f"🔍 GOOGLE_REDIRECT_URI: {self.GOOGLE_REDIRECT_URI}")
        print(f"🔍 BASE_URL: {self.BASE_URL}")
        
        # 必須設定の確認
        if not self.SECRET_KEY:
            print("❌ SECRET_KEY が設定されていません")
        if not self.GOOGLE_CLIENT_ID:
            print("❌ GOOGLE_CLIENT_ID が設定されていません")
        if not self.GOOGLE_CLIENT_SECRET:
            print("❌ GOOGLE_CLIENT_SECRET が設定されていません")
    
    # Google Calendar APIスコープ
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/calendar',  # 読み書き権限
        'https://www.googleapis.com/auth/calendar.readonly',  # 読み取り権限（Googleが自動追加するため明示的に含める）
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]
    
    # OAuth設定
    @property
    def google_client_config(self) -> dict:
        return {
            "web": {
                "client_id": self.GOOGLE_CLIENT_ID,
                "client_secret": self.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.GOOGLE_REDIRECT_URI]
            }
        }
    
    # PostgreSQL URL変換
    @property
    def database_url_psycopg(self) -> str:
        """psycopg3用のURL形式に変換"""
        if self.DATABASE_URL.startswith('postgresql://'):
            return self.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
        return self.DATABASE_URL
    
    def validate_config(self) -> bool:
        """設定の妥当性をチェック"""
        required_vars = [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'GOOGLE_REDIRECT_URI'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        
        if missing_vars:
            print(f"❌ 不足している環境変数: {', '.join(missing_vars)}")
            return False
        
        print("✅ 設定の妥当性チェック完了")
        return True

# グローバル設定インスタンス
settings = Settings()
