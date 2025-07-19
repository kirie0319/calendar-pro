import os
from typing import Dict, Optional
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pytz
from datetime import datetime, timedelta

# 開発環境でHTTP localhost を許可（本番環境では削除推奨）
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from app.core.config import settings
from app.core.entities import User
from app.infrastructure.repositories.user_repository import user_repository
from app.infrastructure.repositories.calendar_repository import calendar_repository

class AuthService:
    def __init__(self):
        self.timezone = pytz.timezone('Asia/Tokyo')
    
    def create_oauth_flow(self, state: Optional[str] = None) -> Flow:
        """OAuth認証フローを作成"""
        flow = Flow.from_client_config(
            settings.google_client_config,
            scopes=settings.GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        if state:
            flow.state = state
            
        return flow
    
    def get_authorization_url(self) -> tuple[str, str]:
        """認証URLと state を取得"""
        flow = self.create_oauth_flow()
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return authorization_url, state
    
    def handle_oauth_callback(self, request: Request, db: Session) -> Dict:
        """OAuth認証コールバックを処理"""
        # デバッグ情報を追加
        print(f"🔍 OAuth コールバック処理開始")
        print(f"🔍 セッション keys: {list(request.session.keys())}")
        print(f"🔍 Request URL: {request.url}")
        
        # 既に認証済みかチェック
        if 'user_id' in request.session and 'credentials' in request.session:
            print(f"✅ 既に認証済みのユーザーです (user_id: {request.session.get('user_id')})")
            
            # 既存のユーザー情報を返す
            user_id = request.session['user_id']
            db_user = user_repository.get_user_by_id(db, user_id)
            
            if db_user:
                user = User(
                    id=db_user.id,
                    google_user_id=db_user.google_user_id,
                    email=db_user.email,
                    name=db_user.name,
                    created_at=db_user.created_at,
                    calendar_last_synced=db_user.calendar_last_synced
                )
                
                return {
                    'user': user,
                    'credentials': request.session['credentials'],
                    'sync_success': True  # 既に同期済みとして扱う
                }
        
        # セッションから state を取得
        state = request.session.get('state')
        print(f"🔍 セッションから取得した state: {state}")
        
        if not state:
            print(f"❌ セッションに state が見つかりません")
            print(f"🔍 現在のセッション内容: {dict(request.session)}")
            
            # 既に認証済みの場合は、専用の例外を投げる
            if 'user_id' in request.session:
                print(f"🔄 既に認証済みのため、リダイレクトが必要です")
                raise HTTPException(status_code=409, detail="User already authenticated")
            
            raise HTTPException(status_code=400, detail="Invalid state - セッションの状態が無効です。再度ログインしてください。")
        
        try:
            flow = self.create_oauth_flow(state)
            
            # 認証コードからトークンを取得
            authorization_response = str(request.url)
            print(f"🔍 Authorization response: {authorization_response}")
            flow.fetch_token(authorization_response=authorization_response)
            
            credentials = flow.credentials
            
            # ユーザー情報を取得
            user_info = self._get_user_info_from_google(credentials)
            
            # データベースにユーザーを保存
            user = user_repository.get_or_create_user(
                db, 
                user_info['google_user_id'], 
                user_info['email'], 
                user_info['name']
            )
            
            # カレンダーデータを同期
            sync_success = self._sync_user_calendar(db, user.id, credentials)
            
            return {
                'user': user,
                'credentials': self._credentials_to_dict(credentials),
                'sync_success': sync_success
            }
            
        except Exception as e:
            print(f"❌ OAuth認証エラー: {e}")
            print(f"🔍 エラータイプ: {type(e)}")
            raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    
    def _get_user_info_from_google(self, credentials: Credentials) -> Dict:
        """Google APIからユーザー情報を取得"""
        try:
            oauth2_service = build('oauth2', 'v2', credentials=credentials)
            user_info = oauth2_service.userinfo().get().execute()
            
            return {
                'google_user_id': user_info.get('id', ''),
                'email': user_info.get('email', ''),
                'name': user_info.get('name', '')
            }
        except Exception as e:
            print(f"❌ ユーザー情報取得エラー: {e}")
            raise
    
    def _sync_user_calendar(self, db: Session, user_id: int, credentials: Credentials) -> bool:
        """ユーザーのカレンダーデータを同期"""
        try:
            print(f"🔄 ユーザー {user_id} のカレンダー同期を開始...")
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # 3ヶ月の期間を設定
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=90)
            
            start_time_str = start_date.isoformat() + 'Z'
            end_time_str = end_date.isoformat() + 'Z'
            
            # カレンダーイベントを取得
            all_events = []
            page_token = None
            
            while True:
                events_result = service.events().list(
                    calendarId='primary',
                    timeMin=start_time_str,
                    timeMax=end_time_str,
                    maxResults=250,
                    singleEvents=True,
                    orderBy='startTime',
                    pageToken=page_token
                ).execute()
                
                events = events_result.get('items', [])
                all_events.extend(events)
                
                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break
            
            print(f"📊 取得したイベント数: {len(all_events)}件")
            
            # データベース用にイベントデータを変換
            events_data = []
            for event in all_events:
                event_data = self._convert_google_event_to_db_format(event)
                if event_data:
                    events_data.append(event_data)
            
            # データベースに同期
            synced_count = calendar_repository.sync_user_calendar_events(db, user_id, events_data)
            print(f"✅ カレンダー同期完了: {synced_count}件のイベントを保存")
            
            return True
            
        except Exception as e:
            print(f"❌ カレンダー同期エラー (ユーザー {user_id}): {e}")
            return False
    
    def _convert_google_event_to_db_format(self, event: Dict) -> Optional[Dict]:
        """GoogleカレンダーイベントをDB保存形式に変換"""
        try:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # 終日イベントの処理
            is_all_day = 'date' in event['start']
            
            if is_all_day:
                start_dt = datetime.fromisoformat(start).replace(tzinfo=self.timezone)
                end_dt = datetime.fromisoformat(end).replace(tzinfo=self.timezone)
            else:
                if start.endswith('Z'):
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    start_dt = start_dt.astimezone(self.timezone)
                    end_dt = end_dt.astimezone(self.timezone)
                else:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
            
            return {
                'google_event_id': event['id'],
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'title': event.get('summary', '無題'),
                'is_all_day': is_all_day
            }
        except Exception as e:
            print(f"⚠️ イベント変換エラー: {e}")
            return None
    
    def _credentials_to_dict(self, credentials: Credentials) -> Dict:
        """Credentialsオブジェクトを辞書に変換"""
        return {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
    
    def get_current_user(self, request: Request, db: Session) -> User:
        """現在のユーザーを取得"""
        if 'user_id' not in request.session:
            raise HTTPException(status_code=401, detail="認証が必要です")
        
        user_id = request.session['user_id']
        db_user = user_repository.get_user_by_id(db, user_id)
        
        if not db_user:
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        
        # SQLAlchemyオブジェクトをエンティティに変換
        return User(
            id=db_user.id,
            google_user_id=db_user.google_user_id,
            email=db_user.email,
            name=db_user.name,
            created_at=db_user.created_at,
            calendar_last_synced=db_user.calendar_last_synced
        )
    
    def update_session(self, request: Request, user: User, credentials: Dict):
        """セッションを更新"""
        request.session['user_id'] = user.id
        request.session['user_email'] = user.email
        request.session['user_name'] = user.name
        request.session['credentials'] = credentials
    
    def clear_session(self, request: Request):
        """セッションをクリア"""
        request.session.clear()

# グローバルインスタンス
auth_service = AuthService()
