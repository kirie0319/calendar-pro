from typing import List, Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.entities import Group, GroupMember, User, GroupRole
from app.infrastructure.repositories.group_repository import group_repository
from app.core.config import settings

class GroupService:
    def create_group(self, db: Session, name: str, description: str, created_by: int) -> Group:
        """グループを作成"""
        try:
            # データベースでグループを作成
            db_group = group_repository.create_group(db, name, description, created_by)
            
            # エンティティに変換
            return Group(
                id=db_group.id,
                name=db_group.name,
                description=db_group.description,
                invite_code=db_group.invite_code,
                created_by=db_group.created_by,
                created_at=db_group.created_at,
                is_active=db_group.is_active
            )
        except Exception as e:
            print(f"❌ グループ作成エラー: {e}")
            raise HTTPException(status_code=500, detail="グループの作成に失敗しました")
    
    def get_group_by_id(self, db: Session, group_id: int) -> Optional[Group]:
        """IDでグループを取得"""
        db_group = group_repository.get_group_by_id(db, group_id)
        
        if not db_group:
            return None
        
        return Group(
            id=db_group.id,
            name=db_group.name,
            description=db_group.description,
            invite_code=db_group.invite_code,
            created_by=db_group.created_by,
            created_at=db_group.created_at,
            is_active=db_group.is_active
        )
    
    def get_group_by_invite_code(self, db: Session, invite_code: str) -> Optional[Group]:
        """招待コードでグループを取得"""
        db_group = group_repository.get_group_by_invite_code(db, invite_code)
        
        if not db_group:
            return None
        
        return Group(
            id=db_group.id,
            name=db_group.name,
            description=db_group.description,
            invite_code=db_group.invite_code,
            created_by=db_group.created_by,
            created_at=db_group.created_at,
            is_active=db_group.is_active
        )
    
    def get_user_groups(self, db: Session, user_id: int) -> List[Dict]:
        """ユーザーが所属するグループを取得"""
        try:
            groups_data = group_repository.get_user_groups(db, user_id)
            
            # データベースの結果をそのまま返す（既に辞書形式）
            return groups_data
        except Exception as e:
            print(f"❌ ユーザーグループ取得エラー: {e}")
            return []
    
    def get_group_members(self, db: Session, group_id: int) -> List[Dict]:
        """グループメンバーを取得"""
        try:
            members_data = group_repository.get_group_members(db, group_id)
            
            # データベースの結果をそのまま返す（既に辞書形式）
            return members_data
        except Exception as e:
            print(f"❌ グループメンバー取得エラー: {e}")
            return []
    
    def get_user_membership(self, db: Session, group_id: int, user_id: int) -> Optional[GroupMember]:
        """ユーザーのグループメンバーシップを取得"""
        db_membership = group_repository.get_user_membership(db, group_id, user_id)
        
        if not db_membership:
            return None
        
        # SQLAlchemyの role 文字列を GroupRole enum に変換
        role = GroupRole.ADMIN if db_membership.role == "admin" else GroupRole.MEMBER
        
        return GroupMember(
            id=db_membership.id,
            group_id=db_membership.group_id,
            user_id=db_membership.user_id,
            role=role,
            joined_at=db_membership.joined_at
        )
    
    def join_group(self, db: Session, group_id: int, user_id: int, role: str = "member") -> bool:
        """ユーザーをグループに追加"""
        try:
            success = group_repository.add_user_to_group(db, group_id, user_id, role)
            
            if success:
                print(f"✅ ユーザー {user_id} がグループ {group_id} に参加しました")
            else:
                print(f"⚠️ ユーザー {user_id} は既にグループ {group_id} のメンバーです")
            
            return success
        except Exception as e:
            print(f"❌ グループ参加エラー: {e}")
            return False
    
    def join_group_by_invite_code(self, db: Session, invite_code: str, user_id: int) -> Optional[Group]:
        """招待コードでグループに参加"""
        try:
            # 招待コードでグループを検索
            group = self.get_group_by_invite_code(db, invite_code)
            
            if not group:
                raise HTTPException(status_code=404, detail="無効な招待コードです")
            
            # グループに参加
            success = self.join_group(db, group.id, user_id, "member")
            
            if success:
                return group
            else:
                # 既にメンバーの場合も成功とみなす
                return group
                
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ 招待コード参加エラー: {e}")
            raise HTTPException(status_code=500, detail="グループ参加に失敗しました")
    
    def check_user_access(self, db: Session, group_id: int, user_id: int) -> bool:
        """ユーザーがグループにアクセス権限を持つかチェック"""
        membership = self.get_user_membership(db, group_id, user_id)
        return membership is not None
    
    def is_group_admin(self, db: Session, group_id: int, user_id: int) -> bool:
        """ユーザーがグループの管理者かチェック"""
        membership = self.get_user_membership(db, group_id, user_id)
        return membership is not None and membership.is_admin()
    
    def get_group_with_access_check(self, db: Session, group_id: int, user_id: int) -> Group:
        """アクセス権限をチェックしてグループを取得"""
        group = self.get_group_by_id(db, group_id)
        
        if not group:
            raise HTTPException(status_code=404, detail="グループが見つかりません")
        
        if not self.check_user_access(db, group_id, user_id):
            raise HTTPException(status_code=403, detail="このグループのメンバーではありません")
        
        return group
    
    def get_group_detail_for_user(self, db: Session, group_id: int, user_id: int) -> Dict:
        """ユーザー向けのグループ詳細情報を取得"""
        try:
            # アクセス権限チェック付きでグループを取得
            group = self.get_group_with_access_check(db, group_id, user_id)
            
            # メンバー情報を取得
            members = self.get_group_members(db, group_id)
            
            # ユーザーのメンバーシップ情報を取得
            membership = self.get_user_membership(db, group_id, user_id)
            
            # 招待URL生成（configから取得）
            invite_url = f"{settings.BASE_URL}/groups/join/{group.invite_code}"
            
            return {
                'group': group,
                'members': members,
                'membership': membership,
                'invite_url': invite_url,
                'member_count': len(members)
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ グループ詳細取得エラー: {e}")
            raise HTTPException(status_code=500, detail="グループ詳細の取得に失敗しました")

# グローバルインスタンス
group_service = GroupService()
