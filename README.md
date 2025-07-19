# 📅 Google Calendar OAuth アプリ

Google OAuth認証を使用してGoogleカレンダーにアクセスし、今週の予定を表示するシンプルなFastAPIアプリケーションです。

## 🚀 機能

- Google OAuth 2.0認証
- Googleカレンダーへの安全なアクセス
- 今週の予定（7日間）の表示
- レスポンシブデザイン
- 美しいUI/UX
- **FastAPI**: 高速で自動ドキュメント生成
- **非同期処理**: 高パフォーマンス
- **自動API文書**: `/docs` でSwagger UI利用可能

## 📋 必要な環境

- Python 3.7以上
- Google Cloud Platform アカウント
- Googleカレンダーアカウント

## 🔧 セットアップ手順

### 1. Google Cloud Platform での設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. APIとサービス → 有効なAPI とサービス → APIを有効にする
4. 「Google Calendar API」を検索して有効化

### 2. OAuth 2.0 認証情報の作成

1. APIとサービス → 認証情報 → 認証情報を作成 → OAuth クライアント ID
2. アプリケーションの種類：「ウェブアプリケーション」を選択
3. 名前：任意の名前を入力
4. 承認済みのリダイレクト URI：`http://localhost:8000/auth/callback` を追加
5. 「作成」をクリック
6. クライアントIDとクライアントシークレットをメモ

### 3. 環境変数の設定

`.env`ファイルが既に存在しますが、以下の値を確認・更新してください：

```env
GOOGLE_CLIENT_ID=あなたのクライアントID
GOOGLE_CLIENT_SECRET=あなたのクライアントシークレット
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

### 4. 依存関係のインストール

```bash
# 仮想環境の作成（推奨）
python -m venv venv

# 仮想環境の有効化
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 5. アプリケーションの起動

```bash
# 方法1: main.pyから直接起動
python main.py

# 方法2: uvicornコマンドから起動
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

ブラウザで `http://localhost:8000` にアクセスしてください。

## 📱 使用方法

1. **ログイン**: メインページの「Googleでログイン」ボタンをクリック
2. **認証**: Googleアカウントでログインし、カレンダーアクセスを許可
3. **カレンダー表示**: 自動的にカレンダーページにリダイレクトされ、今週の予定が表示されます
4. **ログアウト**: 右上の「ログアウト」ボタンでセッションを終了

## 🛠️ 技術スタック

- **Backend**: FastAPI (Python)
- **認証**: Google OAuth 2.0
- **API**: Google Calendar API
- **Frontend**: HTML5, CSS3, Jinja2テンプレート
- **スタイリング**: カスタムCSS（レスポンシブデザイン）
- **サーバー**: Uvicorn ASGI

## 📁 プロジェクト構造

```
calendar_project/
├── main.py                 # メインアプリケーション
├── requirements.txt        # Python依存関係
├── .env                   # 環境変数
├── README.md              # このファイル
└── templates/
    ├── index.html         # ログインページ
    └── calendar.html      # カレンダー表示ページ
```

## 🔒 セキュリティ機能

- OAuth 2.0による安全な認証
- セッション管理
- CSRF保護（stateパラメータ）
- 最小権限の原則（Calendar読み取り専用スコープ）

## 🎨 UI/UX 特徴

- モダンなグラディエント背景
- カード型レイアウト
- ホバーエフェクト
- レスポンシブデザイン
- 絵文字アイコンによる視覚的な魅力

## 🔧 カスタマイズ

### 表示期間の変更

`main.py`の`calendar()`関数内で期間を調整できます：

```python
# 今日から30日間に変更する場合
week_later = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
```

### 取得するイベント数の変更

```python
# 最大50件に変更する場合
events_result = service.events().list(
    calendarId='primary',
    # ...
    maxResults=50,  # ここを変更
    # ...
).execute()
```

## 🚨 トラブルシューティング

### よくある問題

1. **認証エラー**: `.env`ファイルのクライアントIDとシークレットが正しいか確認
2. **リダイレクトエラー**: Google Cloud ConsoleのリダイレクトURIが正確に設定されているか確認
3. **API無効エラー**: Google Calendar APIが有効化されているか確認
4. **モジュールエラー**: `pip install -r requirements.txt`が正常に実行されたか確認

### デバッグモード

開発中は`main.py`の最後の行でリロードモードを有効にしています：

```python
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### FastAPI 固有の機能

- **自動API文書**: `http://localhost:8000/docs` でSwagger UIにアクセス
- **ReDoc**: `http://localhost:8000/redoc` で代替ドキュメント
- **JSON Schema**: 自動的な型検証とドキュメント生成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 貢献

プルリクエストや Issue の報告を歓迎します。

---

**注意**: 本番環境で使用する場合は、`OAUTHLIB_INSECURE_TRANSPORT`環境変数を削除し、HTTPSを使用してください。 