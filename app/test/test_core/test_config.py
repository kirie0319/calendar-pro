import pytest
import os
from unittest.mock import patch, MagicMock
import importlib
import sys

# テスト対象のモジュール
from app.core import config

@pytest.mark.unit
class TestSettings:
    """設定管理のテスト"""
    
    def test_settings_creation_with_env_vars(self):
        """環境変数から設定を読み込むテスト"""
        # テスト用に環境変数を一時的に設定
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
            'SECRET_KEY': 'test_secret_key_for_testing_only'
        }):
            # モジュールをリロードして新しい環境変数を読み込む
            importlib.reload(config)
            settings = config.Settings()
            
            assert settings.GOOGLE_CLIENT_ID == "test_client_id"
            assert settings.GOOGLE_CLIENT_SECRET == "test_client_secret"
            assert settings.GOOGLE_REDIRECT_URI == "http://localhost:8000/auth/callback"
            assert settings.SECRET_KEY == "test_secret_key_for_testing_only"
    
    def test_google_scopes(self):
        """Google APIスコープの設定テスト"""
        settings = config.Settings()
        
        expected_scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
            'openid'
        ]
        
        assert set(settings.GOOGLE_SCOPES) == set(expected_scopes)
    
    def test_google_client_config(self):
        """Google OAuth クライアント設定のテスト"""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
            'SECRET_KEY': 'test_secret_key'
        }):
            importlib.reload(config)
            settings = config.Settings()
            
            config_data = settings.google_client_config
            
            assert "web" in config_data
            assert "client_id" in config_data["web"]
            assert "client_secret" in config_data["web"]
            assert "redirect_uris" in config_data["web"]
            
            assert config_data["web"]["client_id"] == "test_client_id"
            assert config_data["web"]["client_secret"] == "test_client_secret"
            assert "http://localhost:8000/auth/callback" in config_data["web"]["redirect_uris"]
    
    def test_validate_config_success(self):
        """設定の妥当性チェック成功テスト"""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
            'SECRET_KEY': 'test_secret_key'
        }):
            importlib.reload(config)
            settings = config.Settings()
            
            # validate_configメソッドがTrueを返すことを確認
            is_valid = settings.validate_config()
            assert is_valid is True
    
    def test_validate_config_missing_vars(self):
        """設定の妥当性チェック失敗テスト"""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': '',  # 空文字
            'GOOGLE_CLIENT_SECRET': '',
            'GOOGLE_REDIRECT_URI': ''
        }, clear=True):
            importlib.reload(config)
            settings = config.Settings()
            
            # validate_configメソッドがFalseを返すことを確認
            is_valid = settings.validate_config()
            assert is_valid is False
    
    def test_settings_attributes(self):
        """設定オブジェクトの属性テスト"""
        settings = config.Settings()
        
        # 必要な属性が存在することを確認
        assert hasattr(settings, 'GOOGLE_CLIENT_ID')
        assert hasattr(settings, 'GOOGLE_CLIENT_SECRET')
        assert hasattr(settings, 'GOOGLE_REDIRECT_URI')
        assert hasattr(settings, 'SECRET_KEY')
        assert hasattr(settings, 'GOOGLE_SCOPES')
        assert hasattr(settings, 'SESSION_MAX_AGE')
    
    def test_oauth_flow_config_generation(self):
        """OAuth フロー設定の生成テスト"""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
            'SECRET_KEY': 'test_secret_key'
        }):
            importlib.reload(config)
            settings = config.Settings()
            
            # google_client_configが正しい形式で生成されることを確認
            config_data = settings.google_client_config
            
            # 必須フィールドの存在確認
            web_config = config_data["web"]
            required_fields = ["client_id", "client_secret", "auth_uri", "token_uri", "redirect_uris"]
            
            for field in required_fields:
                assert field in web_config, f"Missing required field: {field}"
            
            # URIの正当性確認
            assert "accounts.google.com" in web_config["auth_uri"]
            assert "oauth2.googleapis.com" in web_config["token_uri"]
            
            # リダイレクトURIの確認
            assert isinstance(web_config["redirect_uris"], list)
            assert len(web_config["redirect_uris"]) > 0
    
    def test_scopes_completeness(self):
        """Google APIスコープの完全性テスト"""
        settings = config.Settings()
        scopes = settings.GOOGLE_SCOPES
        
        # 必須スコープの確認
        required_scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        for scope in required_scopes:
            assert scope in scopes, f"Missing required scope: {scope}"
        
        # カレンダー読み取りスコープの確認
        calendar_scope = 'https://www.googleapis.com/auth/calendar.readonly'
        assert calendar_scope in scopes, "Missing calendar read scope"
    
    def test_session_max_age(self):
        """セッション最大期間の確認テスト"""
        settings = config.Settings()
        
        # セッション最大期間が設定されていることを確認
        assert settings.SESSION_MAX_AGE == 86400  # 24時間
    
    @patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "custom_client_id",
        "GOOGLE_CLIENT_SECRET": "custom_client_secret", 
        "GOOGLE_REDIRECT_URI": "https://custom.example.com/callback",
        "SECRET_KEY": "custom_secret_key_with_sufficient_length"
    })
    def test_custom_environment_settings(self):
        """カスタム環境変数設定のテスト"""
        importlib.reload(config)
        settings = config.Settings()
        
        assert settings.GOOGLE_CLIENT_ID == "custom_client_id"
        assert settings.GOOGLE_CLIENT_SECRET == "custom_client_secret"
        assert settings.GOOGLE_REDIRECT_URI == "https://custom.example.com/callback"
        assert settings.SECRET_KEY == "custom_secret_key_with_sufficient_length"
        
        # カスタム設定でもconfigが正しく生成されることを確認
        config_data = settings.google_client_config
        assert config_data["web"]["client_id"] == "custom_client_id"
        assert config_data["web"]["client_secret"] == "custom_client_secret"
        assert "https://custom.example.com/callback" in config_data["web"]["redirect_uris"]

@pytest.mark.unit 
class TestSettingsValidation:
    """設定値の検証テスト"""
    
    def test_google_redirect_uri_validation(self):
        """リダイレクトURIの形式検証テスト"""
        with patch.dict(os.environ, {
            'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
        }):
            importlib.reload(config)
            settings = config.Settings()
            
            redirect_uri = settings.GOOGLE_REDIRECT_URI
            
            # 設定されていることを確認
            assert redirect_uri is not None
            
            # HTTPまたはHTTPSで始まることを確認
            assert redirect_uri.startswith(('http://', 'https://')), "Redirect URI should start with http:// or https://"
    
    def test_database_url_conversion(self):
        """データベースURL変換テスト"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost/dbname'
        }):
            importlib.reload(config)
            settings = config.Settings()
            
            # psycopg URL変換の確認
            psycopg_url = settings.database_url_psycopg
            assert psycopg_url.startswith('postgresql+psycopg://'), "Should convert to psycopg format" 