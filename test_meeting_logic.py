#!/usr/bin/env python3
"""
空き時間計算ロジックのテスト
ダミーデータを使ってMeetingServiceの計算機能をテスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import pytz
from app.service.meeting_service import MeetingService

class MockMeetingService(MeetingService):
    """テスト用のMeetingServiceクラス"""
    
    def __init__(self):
        super().__init__()
    
    def test_calculate_available_slots_with_dummy_data(self):
        """ダミーデータで空き時間計算をテスト"""
        print("🧪 空き時間計算ロジックテスト開始")
        print("=" * 50)
        
        # テスト設定
        start_date = "2025-01-21"  # 火曜日
        end_date = "2025-01-23"    # 木曜日
        start_time = "09:00"
        end_time = "17:00"
        duration_minutes = 60
        
        print(f"📅 検索期間: {start_date} 〜 {end_date}")
        print(f"⏰ 時間帯: {start_time} - {end_time}")
        print(f"⏱️  ミーティング時間: {duration_minutes}分")
        print("")
        
        # ダミーデータ作成
        all_busy_times = self._create_dummy_busy_times()
        
        # メンバーの予定を表示
        print("👥 メンバーの予定:")
        for email, busy_times in all_busy_times.items():
            print(f"  📧 {email}:")
            for busy in busy_times:
                print(f"    - {busy['start'].strftime('%m/%d %H:%M')} - {busy['end'].strftime('%H:%M')}: {busy['title']}")
        print("")
        
        # 空き時間を計算
        available_slots = self._calculate_available_slots(
            all_busy_times,
            start_date,
            end_date,
            start_time,
            end_time,
            duration_minutes
        )
        
        # 結果を表示
        print(f"✅ 計算結果: {len(available_slots)}件の空き時間が見つかりました")
        print("")
        
        if available_slots:
            print("🟢 利用可能な時間スロット:")
            for i, slot in enumerate(available_slots[:10], 1):  # 最初の10件を表示
                print(f"  {i}. {slot['date_str']} {slot['start_time']}-{slot['end_time']}")
        else:
            print("❌ 空き時間が見つかりませんでした")
        
        print("")
        return available_slots
    
    def _create_dummy_busy_times(self):
        """テスト用のダミー予定データを作成"""
        
        # 日本時間のタイムゾーン
        jst = pytz.timezone('Asia/Tokyo')
        
        # ユーザーA（user1@example.com）の予定
        user_a_busy = [
            {
                'start': jst.localize(datetime(2025, 1, 21, 10, 0)),  # 火曜 10:00-11:00
                'end': jst.localize(datetime(2025, 1, 21, 11, 0)),
                'title': 'チームミーティング'
            },
            {
                'start': jst.localize(datetime(2025, 1, 21, 14, 0)),  # 火曜 14:00-15:30
                'end': jst.localize(datetime(2025, 1, 21, 15, 30)),
                'title': '顧客打ち合わせ'
            },
            {
                'start': jst.localize(datetime(2025, 1, 22, 13, 0)),  # 水曜 13:00-14:00
                'end': jst.localize(datetime(2025, 1, 22, 14, 0)),
                'title': 'ランチミーティング'
            },
        ]
        
        # ユーザーB（user2@example.com）の予定
        user_b_busy = [
            {
                'start': jst.localize(datetime(2025, 1, 21, 9, 30)),   # 火曜 9:30-10:30
                'end': jst.localize(datetime(2025, 1, 21, 10, 30)),
                'title': '朝会'
            },
            {
                'start': jst.localize(datetime(2025, 1, 21, 15, 0)),   # 火曜 15:00-16:00
                'end': jst.localize(datetime(2025, 1, 21, 16, 0)),
                'title': 'レビュー会議'
            },
            {
                'start': jst.localize(datetime(2025, 1, 22, 10, 0)),   # 水曜 10:00-12:00
                'end': jst.localize(datetime(2025, 1, 22, 12, 0)),
                'title': 'プロジェクト会議'
            },
        ]
        
        # ユーザーC（user3@example.com）の予定（空いている）
        user_c_busy = []
        
        return {
            'user1@example.com': user_a_busy,
            'user2@example.com': user_b_busy,
            'user3@example.com': user_c_busy,
        }
    
    def test_merge_overlapping_periods(self):
        """重複期間のマージ処理をテスト"""
        print("🧪 重複期間マージテスト開始")
        print("=" * 30)
        
        jst = pytz.timezone('Asia/Tokyo')
        
        # テストケース1: 重複する期間
        periods1 = [
            {
                'start': jst.localize(datetime(2025, 1, 21, 10, 0)),
                'end': jst.localize(datetime(2025, 1, 21, 11, 0)),
            },
            {
                'start': jst.localize(datetime(2025, 1, 21, 10, 30)),
                'end': jst.localize(datetime(2025, 1, 21, 12, 0)),
            },
        ]
        
        merged1 = self._merge_overlapping_periods(periods1)
        print(f"テスト1 - 重複期間:")
        print(f"  入力: 10:00-11:00, 10:30-12:00")
        print(f"  結果: {merged1[0]['start'].strftime('%H:%M')}-{merged1[0]['end'].strftime('%H:%M')}")
        
        # テストケース2: 離れている期間
        periods2 = [
            {
                'start': jst.localize(datetime(2025, 1, 21, 10, 0)),
                'end': jst.localize(datetime(2025, 1, 21, 11, 0)),
            },
            {
                'start': jst.localize(datetime(2025, 1, 21, 14, 0)),
                'end': jst.localize(datetime(2025, 1, 21, 15, 0)),
            },
        ]
        
        merged2 = self._merge_overlapping_periods(periods2)
        print(f"テスト2 - 離れた期間:")
        print(f"  入力: 10:00-11:00, 14:00-15:00")
        print(f"  結果: {len(merged2)}個の期間 (マージされない)")
        
        print("")
        return merged1, merged2

def run_tests():
    """全テストを実行"""
    print("🚀 空き時間計算ロジック テスト実行")
    print("=" * 60)
    print("")
    
    # MeetingServiceのテストインスタンスを作成
    service = MockMeetingService()
    
    try:
        # テスト1: 重複期間のマージ
        service.test_merge_overlapping_periods()
        
        # テスト2: 空き時間計算
        available_slots = service.test_calculate_available_slots_with_dummy_data()
        
        # 統計情報
        print("📊 テスト統計:")
        print(f"  - 見つかった空き時間: {len(available_slots)}件")
        
        if available_slots:
            # 日別の空き時間数
            slots_by_date = {}
            for slot in available_slots:
                date = slot['date']
                slots_by_date[date] = slots_by_date.get(date, 0) + 1
            
            for date, count in slots_by_date.items():
                print(f"  - {date}: {count}件")
        
        print("")
        print("✅ テスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_tests() 