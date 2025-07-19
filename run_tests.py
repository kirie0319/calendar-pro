#!/usr/bin/env python3
"""
🧪 Clean Architecture Calendar App テストランナー
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description):
    """コマンドを実行し結果を表示"""
    print(f"\n🔍 {description}")
    print(f"📝 実行コマンド: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
        else:
            print(f"❌ {description} - 失敗 (exit code: {result.returncode})")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description} - エラー: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Clean Architecture Calendar App テストランナー")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "api", "core", "infrastructure", "service"],
        default="all",
        help="実行するテストタイプ"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="カバレッジレポートを生成"
    )
    parser.add_argument(
        "--parallel", 
        action="store_true",
        help="並列実行（xdistが必要）"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="詳細出力"
    )
    parser.add_argument(
        "--fast", 
        action="store_true",
        help="高速実行（slowマーカーをスキップ）"
    )
    
    args = parser.parse_args()
    
    print("🧪 Clean Architecture Calendar App テストランナー")
    print("=" * 60)
    
    # 基本コマンド構築
    cmd = ["python", "-m", "pytest"]
    
    # テストタイプ別の設定
    if args.type == "unit":
        cmd.extend(["-m", "unit"])
        description = "単体テスト"
    elif args.type == "integration":
        cmd.extend(["-m", "integration"])
        description = "統合テスト"
    elif args.type == "api":
        cmd.extend(["-m", "api"])
        description = "APIテスト"
    elif args.type == "core":
        cmd.append("app/test/test_core/")
        description = "Core層テスト"
    elif args.type == "infrastructure":
        cmd.append("app/test/test_infrastructure/")
        description = "Infrastructure層テスト"
    elif args.type == "service":
        cmd.append("app/test/test_service/")
        description = "Service層テスト"
    else:
        description = "全テスト"
    
    # 高速実行オプション
    if args.fast:
        cmd.extend(["-m", "not slow"])
        description += " (高速実行)"
    
    # 詳細出力
    if args.verbose:
        cmd.extend(["-v", "-s"])
    
    # 並列実行
    if args.parallel:
        try:
            import pytest_xdist
            cmd.extend(["-n", "auto"])
            description += " (並列実行)"
        except ImportError:
            print("⚠️  pytest-xdist がインストールされていません。シーケンシャル実行します。")
    
    # カバレッジレポート
    if args.coverage:
        try:
            import pytest_cov
            cmd.extend([
                "--cov=app",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-report=xml"
            ])
            description += " (カバレッジ付き)"
        except ImportError:
            print("⚠️  pytest-cov がインストールされていません。カバレッジなしで実行します。")
    
    # テスト実行
    success = run_command(cmd, description)
    
    if args.coverage and success:
        print("\n📊 カバレッジレポートが生成されました:")
        print("   📄 HTML: htmlcov/index.html")
        print("   📄 XML: coverage.xml")
    
    # 結果サマリー
    print("\n" + "=" * 60)
    if success:
        print("🎉 テスト実行完了 - 全て成功！")
        return 0
    else:
        print("💥 テスト実行完了 - 一部失敗")
        return 1

def show_test_info():
    """テスト情報を表示"""
    print("\n📋 利用可能なテストコマンド:")
    print("\n🔧 基本実行:")
    print("  python run_tests.py                    # 全テスト実行")
    print("  python run_tests.py --type unit        # 単体テストのみ")
    print("  python run_tests.py --type integration # 統合テストのみ")
    print("  python run_tests.py --type api         # APIテストのみ")
    
    print("\n🏗️ レイヤー別実行:")
    print("  python run_tests.py --type core           # Core層テスト")
    print("  python run_tests.py --type infrastructure # Infrastructure層テスト")
    print("  python run_tests.py --type service        # Service層テスト")
    
    print("\n⚡ オプション:")
    print("  --coverage    # カバレッジレポート生成")
    print("  --parallel    # 並列実行")
    print("  --verbose     # 詳細出力")
    print("  --fast        # 高速実行（時間のかかるテストをスキップ）")
    
    print("\n📁 テスト構造:")
    print("  app/test/")
    print("  ├── conftest.py              # テスト設定")
    print("  ├── test_core/               # Core層テスト")
    print("  │   ├── test_entities.py     # エンティティテスト")
    print("  │   └── test_config.py       # 設定テスト")
    print("  ├── test_infrastructure/     # Infrastructure層テスト")
    print("  │   └── test_repositories.py # リポジトリテスト")
    print("  ├── test_service/            # Service層テスト")
    print("  │   ├── test_group_service.py    # グループサービステスト")
    print("  │   └── test_meeting_service.py  # ミーティングサービステスト")
    print("  └── test_api/                # API層テスト")
    print("      └── test_endpoints.py    # エンドポイントテスト")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 引数なしの場合は情報表示
        show_test_info()
        print("\n" + "=" * 60)
        print("🚀 デフォルトで全テストを実行します...")
        print("   ⏸️  Ctrl+C で中断できます")
        print("   ℹ️  詳細は --help を参照")
        print("=" * 60)
        
        # 少し待機してから実行
        import time
        time.sleep(2)
    
    sys.exit(main()) 