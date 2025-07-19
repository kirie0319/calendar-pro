from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session, get_templates, get_current_user
from app.service.group_service import group_service
from app.core.entities import User

router = APIRouter(prefix="/groups")

@router.get("/", response_class=HTMLResponse)
async def groups_list(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """グループ一覧画面"""
    try:
        # ユーザーが所属するグループを取得
        groups = group_service.get_user_groups(db, current_user.id)
        
        return templates.TemplateResponse("groups.html", {
            "request": request, 
            "user": current_user, 
            "groups": groups
        })
        
    except Exception as e:
        print(f"❌ グループ一覧取得エラー: {e}")
        return RedirectResponse(url="/", status_code=302)

@router.get("/create", response_class=HTMLResponse)
async def group_create_form(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: User = Depends(get_current_user)
):
    """グループ作成画面"""
    return templates.TemplateResponse("group_create.html", {
        "request": request, 
        "user": current_user
    })

@router.post("/create")
async def group_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """グループ作成処理"""
    try:
        # 入力検証
        if not name or len(name.strip()) == 0:
            raise HTTPException(status_code=400, detail="グループ名を入力してください")
        
        if len(name) > 100:
            raise HTTPException(status_code=400, detail="グループ名は100文字以内で入力してください")
        
        if len(description) > 500:
            raise HTTPException(status_code=400, detail="説明は500文字以内で入力してください")
        
        # 新しいグループを作成
        group = group_service.create_group(db, name.strip(), description.strip(), current_user.id)
        
        print(f"✅ グループ作成成功: {group.name} (ID: {group.id})")
        return RedirectResponse(url=f"/groups/{group.id}", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ グループ作成エラー: {e}")
        raise HTTPException(status_code=500, detail="グループの作成に失敗しました")

@router.get("/{group_id}", response_class=HTMLResponse)
async def group_detail(
    request: Request,
    group_id: int,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """グループ詳細画面"""
    try:
        # グループ詳細情報を取得（アクセス権限チェック付き）
        group_detail_info = group_service.get_group_detail_for_user(db, group_id, current_user.id)
        
        group = group_detail_info['group']
        members = group_detail_info['members']
        membership = group_detail_info['membership']
        invite_url = group_detail_info['invite_url']
        
        # リクエストのベースURLを使って正しい招待URLを生成
        base_url = str(request.base_url).rstrip('/')
        invite_url = f"{base_url}/groups/join/{group.invite_code}"
        
        return templates.TemplateResponse("group_detail.html", {
            "request": request,
            "user": current_user,
            "group": group,
            "membership": membership,
            "members": members,
            "invite_url": invite_url
        })
        
    except HTTPException:
        # アクセス権限エラーなどの場合
        return RedirectResponse(url="/groups", status_code=302)
    except Exception as e:
        print(f"❌ グループ詳細取得エラー: {e}")
        return RedirectResponse(url="/groups", status_code=302)

@router.get("/join/{invite_code}")
async def group_join(
    invite_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """グループ参加処理"""
    try:
        # 招待コードでグループに参加
        group = group_service.join_group_by_invite_code(db, invite_code, current_user.id)
        
        if group:
            print(f"✅ ユーザー {current_user.name} がグループ {group.name} に参加しました")
            return RedirectResponse(url=f"/groups/{group.id}", status_code=302)
        else:
            raise HTTPException(status_code=404, detail="無効な招待コードです")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ グループ参加エラー: {e}")
        return RedirectResponse(url="/groups", status_code=302)

@router.get("/{group_id}/schedule", response_class=HTMLResponse)
async def meeting_scheduler_page(
    request: Request,
    group_id: int,
    templates: Jinja2Templates = Depends(get_templates),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """ミーティングスケジューラーページ"""
    try:
        # アクセス権限チェック付きでグループを取得
        group = group_service.get_group_with_access_check(db, group_id, current_user.id)
        
        # グループメンバー一覧を取得
        members = group_service.get_group_members(db, group_id)
        
        return templates.TemplateResponse("meeting_scheduler.html", {
            "request": request,
            "user": current_user,
            "group": group,
            "members": members
        })
        
    except HTTPException:
        return RedirectResponse(url="/groups", status_code=302)
    except Exception as e:
        print(f"❌ スケジューラーページエラー: {e}")
        return RedirectResponse(url="/groups", status_code=302)

@router.post("/{group_id}/schedule")
async def meeting_scheduler_search(
    request: Request,
    group_id: int,
    selected_members: list = Form(...),
    search_start_date: str = Form(...),
    search_end_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    duration_minutes: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """ミーティング空き時間検索（フォーム処理）"""
    try:
        # パラメータをクエリ文字列形式に変換
        from urllib.parse import urlencode
        
        query_params = {
            'selected_members': ','.join(selected_members),
            'start_date': search_start_date,
            'end_date': search_end_date,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration_minutes
        }
        
        # 結果ページにリダイレクト
        redirect_url = f"/groups/{group_id}/schedule/search?{urlencode(query_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        print(f"❌ ミーティング検索フォーム処理エラー: {e}")
        return RedirectResponse(url=f"/groups/{group_id}/schedule", status_code=302)
