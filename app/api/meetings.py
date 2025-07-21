from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.api.dependencies import get_database_session, get_templates, get_current_user, get_user_credentials
from app.service.meeting_service import meeting_service
from app.service.group_service import group_service
from app.core.entities import User
from app.infrastructure.repositories.calendar_repository import calendar_repository
from app.infrastructure.repositories.user_repository import user_repository

router = APIRouter()

@router.post("/api/meeting/create")
async def create_meeting(
    request: Request,
    title: str = Form(...),
    start_datetime: str = Form(...),
    end_datetime: str = Form(...),
    attendee_emails: List[str] = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    credentials: dict = Depends(get_user_credentials)
):
    """ミーティング作成API"""
    try:
        print(f"🔍 ミーティング作成リクエスト受信:")
        print(f"   タイトル: {title}")
        print(f"   開始時刻: {start_datetime}")
        print(f"   終了時刻: {end_datetime}")
        print(f"   参加者: {attendee_emails}")
        
        # 認証情報チェック
        if not credentials:
            raise HTTPException(status_code=401, detail="Google認証情報が見つかりません")
        
        # 日時文字列をdatetimeオブジェクトに変換
        try:
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="無効な日時形式です")
        
        # 基本的なバリデーション
        if not title.strip():
            raise HTTPException(status_code=400, detail="ミーティングタイトルは必須です")
        
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="開始時刻は終了時刻より前である必要があります")
        
        if len(attendee_emails) < 1:
            raise HTTPException(status_code=400, detail="少なくとも1名の参加者が必要です")
        
        # ミーティングイベントを作成
        result = meeting_service.create_meeting_event(
            credentials=credentials,
            title=title.strip(),
            start_datetime=start_dt,
            end_datetime=end_dt,
            attendee_emails=attendee_emails,
            description=description.strip()
        )
        
        print(f"✅ ミーティング作成成功: {result['event_id']}")
        
        return JSONResponse(content={
            "status": "success",
            "message": "ミーティングが正常に作成されました",
            "event_id": result['event_id'],
            "html_link": result.get('html_link'),
            "meeting_details": {
                "title": title,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "attendees": attendee_emails
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ミーティング作成APIエラー: {e}")
        raise HTTPException(status_code=500, detail=f"ミーティングの作成に失敗しました: {str(e)}")

@router.post("/api/meeting/search")
async def search_meeting_times(
    request: Request,
    group_id: int = Form(...),
    selected_members: List[str] = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    duration: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session),
    credentials: dict = Depends(get_user_credentials)
):
    """ミーティング時間検索API"""
    try:
        # パラメータ検証
        meeting_service.validate_search_parameters(
            selected_members, start_date, end_date, start_time, end_time, duration
        )
        
        # グループアクセス権限チェック
        group_service.get_group_with_access_check(db, group_id, current_user.id)
        
        # 空き時間を検索
        search_result = meeting_service.find_available_times(
            db=db,
            member_emails=selected_members,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            member_credentials=credentials if credentials else {},
            current_user_email=current_user.email
        )
        
        return JSONResponse(content=search_result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ミーティング検索APIエラー: {e}")
        raise HTTPException(status_code=500, detail=f"検索中にエラーが発生しました: {str(e)}")

@router.get("/groups/{group_id}/schedule/search", response_class=HTMLResponse)
async def meeting_results_page(
    request: Request,
    group_id: int,
    # クエリパラメータで検索条件を受け取る
    selected_members: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    duration: int = Query(...),
    templates: Jinja2Templates = Depends(get_templates),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session),
    credentials: dict = Depends(get_user_credentials)
):
    """ミーティング検索結果ページ"""
    try:
        # selected_membersをリストに変換
        member_emails = [email.strip() for email in selected_members.split(',') if email.strip()]
        
        # パラメータ検証
        meeting_service.validate_search_parameters(
            member_emails, start_date, end_date, start_time, end_time, duration
        )
        
        # グループアクセス権限チェック
        group = group_service.get_group_with_access_check(db, group_id, current_user.id)
        
        # 空き時間を検索
        search_result = meeting_service.find_available_times(
            db=db,
            member_emails=member_emails,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            member_credentials=credentials if credentials else {}
        )
        
        available_slots = search_result['available_slots']
        member_schedules = search_result['member_schedules']
        
        # 検索パラメータを再構築
        search_params = {
            'start_date': start_date,
            'end_date': end_date,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'selected_members': member_emails
        }
        
        # デバッグ情報
        print(f"🔍 検索結果: {len(available_slots)}個のスロットが見つかりました")
        
        return templates.TemplateResponse("meeting_results.html", {
            "request": request,
            "user": current_user,
            "group": group,
            "available_slots": available_slots,
            "member_schedules": member_schedules,
            "search_params": search_params,
            "total_slots": len(available_slots)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 検索結果ページエラー: {e}")
        raise HTTPException(status_code=500, detail=f"結果表示中にエラーが発生しました: {str(e)}")

@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """カレンダー表示ページ"""
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # 今週の開始と終了を計算
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # 週の各日付を生成
    week_dates = []
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        week_dates.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': ['月', '火', '水', '木', '金', '土', '日'][i],
            'day_number': current_date.day,
            'is_today': current_date == today
        })
    
    # 時間のリスト（カレンダー表示用）
    hours = [f"{hour:02d}:00" for hour in range(9, 18)]  # 9:00-17:00
    
    # カレンダーイベントを取得
    events_by_day = defaultdict(list)
    total_events = 0
    
    try:
        # 週の開始と終了をdatetimeに変換
        start_datetime = datetime.combine(week_start, datetime.min.time())
        end_datetime = datetime.combine(week_end, datetime.max.time())
        
        # ユーザーのカレンダーイベントを取得
        events = calendar_repository.get_user_calendar_events_for_period(
            db, current_user.id, start_datetime, end_datetime
        )
        
        # イベントを日別に整理
        for event in events:
            event_date = event.start_datetime.date().strftime('%Y-%m-%d')
            
            # グリッド位置を計算（9:00を基準として）
            start_hour = event.start_datetime.hour
            start_minute = event.start_datetime.minute
            end_hour = event.end_datetime.hour
            end_minute = event.end_datetime.minute
            
            # 9:00基準での位置計算（1時間 = 60px）
            grid_top = max(0, (start_hour - 9) * 60 + start_minute)
            duration_minutes = (end_hour - start_hour) * 60 + (end_minute - start_minute)
            grid_height = max(30, duration_minutes)  # 最小30px
            
            events_by_day[event_date].append({
                'id': event.id,
                'summary': event.title,  # テンプレートはsummaryを期待
                'title': event.title,
                'start_time': event.start_datetime.strftime('%H:%M'),
                'end_time': event.end_datetime.strftime('%H:%M'),
                'is_all_day': event.is_all_day,
                'google_event_id': event.google_event_id,
                'grid_top': grid_top,
                'grid_height': grid_height,
                'description': '',  # 空文字で初期化
                'location': ''  # 空文字で初期化
            })
            total_events += 1
    
    except Exception as e:
        print(f"❌ カレンダーイベント取得エラー: {e}")
        # エラーが発生しても空のデータで継続
    
    # デバッグ情報を出力
    print(f"🔍 今週の期間: {week_start} 〜 {week_end}")
    print(f"🔍 取得したイベント総数: {total_events}")
    print(f"🔍 events_by_day keys: {list(events_by_day.keys())}")
    for date, events in events_by_day.items():
        print(f"🔍 {date}: {len(events)}件のイベント")
        for event in events[:3]:  # 最初の3件だけ表示
            print(f"  - {event['summary']} ({event['start_time']}-{event['end_time']})")
    
    # weekly_dataを構築
    weekly_data = {
        'week_start': week_start.strftime('%m/%d'),
        'week_end': week_end.strftime('%m/%d'),
        'week_dates': week_dates,
        'events_by_day': dict(events_by_day),
        'hours': hours,
        'debug_info': {
            'total_events': total_events
        }
    }
    
    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "user": current_user,
        "weekly_data": weekly_data
    })

@router.get("/api/calendar/events")
async def get_calendar_events(
    start: str = Query(...),
    end: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """カレンダーイベント取得API（FullCalendar用）"""
    try:
        from datetime import datetime
        
        # 日付文字列をdatetimeに変換
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        # ユーザーのカレンダーイベントを取得
        events = calendar_repository.get_user_calendar_events_for_period(db, current_user.id, start_date, end_date)
        
        # FullCalendar形式に変換
        calendar_events = []
        for event in events:
            calendar_event = {
                'id': f"event_{event.id}",
                'title': event.title,
                'start': event.start_datetime.isoformat(),
                'end': event.end_datetime.isoformat(),
                'allDay': event.is_all_day,
                'backgroundColor': '#3788d8',
                'borderColor': '#3788d8'
            }
            calendar_events.append(calendar_event)
        
        return JSONResponse(content=calendar_events)
        
    except Exception as e:
        print(f"❌ カレンダーイベント取得エラー: {e}")
        return JSONResponse(content=[])

@router.get("/api/member/schedule/{member_email}")
async def get_member_schedule_summary(
    member_email: str,
    date: str = Query(...),
    start_time: str = Query(...),
    duration: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """特定メンバーの予定サマリーを取得（フロントエンド用）"""
    try:
        from datetime import datetime, timedelta
        
        # 指定日の範囲でイベントを取得
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start_datetime = target_date
        end_datetime = target_date + timedelta(days=1)
        
        # メンバーのユーザーIDを取得
        member_user = user_repository.get_user_by_email(db, member_email)
        
        if not member_user:
            return JSONResponse(content={'events': [], 'status': 'no_data'})
        
        # イベントを取得
        events = calendar_repository.get_user_calendar_events_for_period(db, member_user.id, start_datetime, end_datetime)
        
        # フロントエンド用にフォーマット
        formatted_events = []
        for event in events:
            formatted_event = {
                'title': event.title,
                'start_time': event.start_datetime.strftime('%H:%M'),
                'end_time': event.end_datetime.strftime('%H:%M'),
                'start_datetime': event.start_datetime.isoformat(),
                'end_datetime': event.end_datetime.isoformat(),
                'is_all_day': event.is_all_day
            }
            formatted_events.append(formatted_event)
        
        return JSONResponse(content={
            'events': formatted_events,
            'status': 'success',
            'member_email': member_email,
            'date': date
        })
        
    except Exception as e:
        print(f"❌ メンバー予定取得エラー: {e}")
        return JSONResponse(content={'events': [], 'status': 'error', 'message': str(e)})
