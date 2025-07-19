from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List, Dict

from app.infrastructure.models import Group, GroupMember, User, generate_invite_code

class GroupRepository:
    def create_group(self, session: Session, name: str, description: str, created_by: int) -> Group:
        """グループを作成し、作成者を管理者として追加"""
        # グループ作成
        group = Group(
            name=name,
            description=description,
            invite_code=generate_invite_code(),
            created_by=created_by,
            is_active=True
        )
        session.add(group)
        session.commit()
        session.refresh(group)
        
        # 作成者を管理者として追加
        membership = GroupMember(
            group_id=group.id,
            user_id=created_by,
            role="admin"
        )
        session.add(membership)
        session.commit()
        
        print(f"✅ グループを作成しました: {name} (招待コード: {group.invite_code})")
        return group
    
    def get_group_by_id(self, session: Session, group_id: int) -> Optional[Group]:
        """IDでグループを取得"""
        result = session.execute(select(Group).where(Group.id == group_id))
        return result.scalar_one_or_none()
    
    def get_group_by_invite_code(self, session: Session, invite_code: str) -> Optional[Group]:
        """招待コードでグループを取得"""
        result = session.execute(select(Group).where(
            Group.invite_code == invite_code,
            Group.is_active == True
        ))
        return result.scalar_one_or_none()
    
    def get_user_groups(self, session: Session, user_id: int) -> List[Dict]:
        """ユーザーが所属するグループ一覧を取得"""
        # ユーザーのメンバーシップを取得
        result = session.execute(
            select(GroupMember, Group)
            .join(Group, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user_id, Group.is_active == True)
        )
        
        groups = []
        for membership, group in result.fetchall():
            groups.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'role': membership.role,
                'joined_at': membership.joined_at,
                'invite_code': group.invite_code
            })
        
        return groups
    
    def get_group_members(self, session: Session, group_id: int) -> List[Dict]:
        """グループメンバー一覧を取得"""
        result = session.execute(
            select(GroupMember, User)
            .join(User, GroupMember.user_id == User.id)
            .where(GroupMember.group_id == group_id)
        )
        
        members = []
        for membership, user in result.fetchall():
            members.append({
                'name': user.name,
                'email': user.email,
                'role': membership.role,
                'joined_at': membership.joined_at
            })
        
        return members
    
    def get_user_membership(self, session: Session, group_id: int, user_id: int) -> Optional[GroupMember]:
        """ユーザーのグループメンバーシップを取得"""
        result = session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    def add_user_to_group(self, session: Session, group_id: int, user_id: int, role: str = "member") -> bool:
        """ユーザーをグループに追加"""
        # 既にメンバーかチェック
        if self.get_user_membership(session, group_id, user_id):
            return False
        
        membership = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role=role
        )
        session.add(membership)
        session.commit()
        
        return True

# グローバルインスタンス
group_repository = GroupRepository() 