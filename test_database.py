#!/usr/bin/env python3
"""
データベースの内容を確認し、機能をテストするスクリプト。このスクリプトからDBを操作したり行う。
"""

import os
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base, CalendarEvent
from database import (
    get_or_create_user, create_group, get_user_groups, 
    get_group_members, add_user_to_group, get_group_by_invite_code
)

def setup_database():
    """データベース接続を設定"""
    load_dotenv()
    DATABASE_URL = os.getenv('DATABASE_URL', "sqlite:///./calendar_app.db")
    
    if DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal(), engine

def initialize_database():
    """データベースを初期化（全テーブル削除→再作成）"""
    print("🔄 データベース初期化を開始します...")
    print("⚠️  既存のデータはすべて削除されます！")
    
    session, engine = setup_database()
    
    try:
        # 既存のテーブルを削除
        print("\n📋 既存のテーブルを確認中...")
        with engine.connect() as conn:
            # 既存テーブル一覧を取得
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            if existing_tables:
                print(f"   既存テーブル: {', '.join(existing_tables)}")
                
                # 外部キー制約を無効化してからテーブル削除
                print("\n🗑️  既存テーブルを削除中...")
                
                # CASCADE で依存関係も含めて削除
                for table in existing_tables:
                    try:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                        print(f"   ✅ {table} テーブル削除完了")
                    except Exception as e:
                        print(f"   ⚠️ {table} テーブル削除中にエラー: {e}")
                
                conn.commit()
            else:
                print("   既存テーブルはありません")
        
        # 新しいテーブルを作成
        print("\n🏗️  新しいテーブルを作成中...")
        Base.metadata.create_all(bind=engine)
        
        # 作成されたテーブルを確認
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            new_tables = [row[0] for row in result.fetchall()]
            
            print(f"✅ 新テーブル作成完了!")
            print(f"   作成されたテーブル: {', '.join(new_tables)}")
            
            # 各テーブルの構造を確認
            for table in new_tables:
                result = conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                print(f"\n📋 {table}テーブル:")
                for col_name, data_type, is_nullable in columns:
                    nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                    print(f"   - {col_name}: {data_type} {nullable}")
        
        print(f"\n🎉 データベース初期化が正常に完了しました！")
        return True
        
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")
        return False
    
    finally:
        session.close()

def show_database_content():
    """データベースの内容を表示"""
    session, engine = setup_database()
    
    print("📊 データベースの現在の内容:")
    print("=" * 60)
    
    try:
        # ユーザー一覧
        users = session.execute(text("SELECT id, name, email, google_user_id, created_at, calendar_last_synced FROM users ORDER BY created_at")).fetchall()
        print(f"\n👥 ユーザー ({len(users)}件):")
        for user in users:
            sync_status = "同期済み" if user[5] else "未同期"
            print(f"  ID: {user[0]}, 名前: {user[1]}, Email: {user[2]}")
            print(f"      Google ID: {user[3]}, 作成: {user[4]}, カレンダー: {sync_status}")
        
        # グループ一覧
        groups = session.execute(text("SELECT id, name, description, invite_code, created_by, created_at FROM groups ORDER BY created_at")).fetchall()
        print(f"\n📝 グループ ({len(groups)}件):")
        for group in groups:
            print(f"  ID: {group[0]}, 名前: {group[1]}")
            print(f"      説明: {group[2]}")
            print(f"      招待コード: {group[3]}, 作成者: {group[4]}, 作成: {group[5]}")
        
        # グループメンバー一覧
        members = session.execute(text("""
            SELECT gm.id, gm.group_id, gm.user_id, gm.role, gm.joined_at, 
                   u.name as user_name, g.name as group_name
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            JOIN groups g ON gm.group_id = g.id
            ORDER BY gm.joined_at
        """)).fetchall()
        print(f"\n👤 グループメンバー ({len(members)}件):")
        for member in members:
            print(f"  {member[5]} の {member[6]} ({member[3]})")
            print(f"      参加日: {member[4]}")
        
        # カレンダーイベント一覧
        events = session.execute(text("""
            SELECT ce.id, ce.user_id, ce.google_event_id, ce.start_datetime, 
                   ce.end_datetime, ce.title, ce.is_all_day, ce.created_at,
                   u.name as user_name
            FROM calendar_events ce
            JOIN users u ON ce.user_id = u.id
            ORDER BY ce.start_datetime
            LIMIT 10
        """)).fetchall()
        print(f"\n📅 カレンダーイベント (最新10件):")
        if events:
            for event in events:
                all_day = "終日" if event[6] else "時間指定"
                print(f"  {event[8]}: {event[5]} ({all_day})")
                print(f"      期間: {event[3]} 〜 {event[4]}")
        else:
            print("  カレンダーイベントはありません")
        
        # カレンダーイベントの統計
        event_stats = session.execute(text("""
            SELECT u.name, COUNT(ce.id) as event_count
            FROM users u
            LEFT JOIN calendar_events ce ON u.id = ce.user_id
            GROUP BY u.id, u.name
            ORDER BY event_count DESC
        """)).fetchall()
        print(f"\n📊 ユーザー別イベント数:")
        for stat in event_stats:
            print(f"  {stat[0]}: {stat[1]}件")
    
    except Exception as e:
        print(f"❌ データ表示エラー: {e}")
    
    finally:
        session.close()

def test_database_operations():
    """データベース操作をテスト"""
    session, engine = setup_database()
    
    print("\n🧪 データベース操作のテスト:")
    print("=" * 60)
    
    try:
        # テストユーザー作成
        print("\n1. テストユーザー作成...")
        user1 = get_or_create_user(session, "test123", "test@example.com", "テストユーザー1")
        user2 = get_or_create_user(session, "test456", "test2@example.com", "テストユーザー2")
        print(f"   ユーザー1: {user1.name} (ID: {user1.id})")
        print(f"   ユーザー2: {user2.name} (ID: {user2.id})")
        
        # グループ作成
        print("\n2. テストグループ作成...")
        group = create_group(session, "テストグループ", "これはテスト用のグループです", user1.id)
        print(f"   グループ: {group.name} (ID: {group.id}, 招待コード: {group.invite_code})")
        
        # ユーザー2をグループに追加
        print("\n3. ユーザー2をグループに追加...")
        success = add_user_to_group(session, group.id, user2.id, "member")
        print(f"   追加結果: {'成功' if success else '失敗'}")
        
        # グループメンバー確認
        print("\n4. グループメンバー確認...")
        members = get_group_members(session, group.id)
        for member in members:
            print(f"   {member['name']} ({member['email']}) - {member['role']}")
        
        # 招待コードでグループ検索
        print("\n5. 招待コードでグループ検索...")
        found_group = get_group_by_invite_code(session, group.invite_code)
        print(f"   見つかったグループ: {found_group.name if found_group else 'なし'}")
        
        print("\n✅ すべてのテストが完了しました！")
        
    except Exception as e:
        print(f"❌ テスト中にエラーが発生しました: {e}")
    
    finally:
        session.close()

def main():
    print("🔍 Railway PostgreSQL データベーステスト")
    print("=" * 60)
    
    # メニュー表示
    print("\n選択してください:")
    print("1. データベース初期化 (全データ削除)")
    print("2. データベース内容表示")
    print("3. データベース操作テスト")
    print("4. すべて実行")
    
    choice = input("\n番号を入力してください (1-4): ").strip()
    
    if choice == "1":
        confirm = input("\n⚠️ 本当にデータベースを初期化しますか？ (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            initialize_database()
        else:
            print("キャンセルしました。")
    
    elif choice == "2":
        show_database_content()
    
    elif choice == "3":
        test_database_operations()
        print("\n" + "=" * 60)
        print("📊 テスト実行後のデータベース内容:")
        show_database_content()
    
    elif choice == "4":
        # 初期化確認
        confirm = input("\n⚠️ データベースを初期化してからテストを実行しますか？ (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            if initialize_database():
                print("\n" + "=" * 60)
                test_database_operations()
                print("\n" + "=" * 60)
                print("📊 最終的なデータベース内容:")
                show_database_content()
        else:
            print("キャンセルしました。")
    
    else:
        print("無効な選択です。")

if __name__ == "__main__":
    main() 