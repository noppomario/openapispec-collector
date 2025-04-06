#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# モックモジュールをインポート
from test.mock_gh import MockGitHub, run_mock_gh_command

# 元のモジュールをインポート
from config import CONFIG
import collect_openapi

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openapispec-test')

def setup_test_environment():
    """
    テスト環境をセットアップ
    """
    # テスト用の出力ディレクトリをクリア
    test_output_dir = Path("test/output")
    test_static_site_dir = Path("test/static_site")
    
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)
    
    if test_static_site_dir.exists():
        shutil.rmtree(test_static_site_dir)
        
    test_output_dir.mkdir(exist_ok=True)
    test_static_site_dir.mkdir(exist_ok=True)
    
    # 一時的に設定を書き換え
    global original_output_dir, original_static_site_dir
    original_output_dir = CONFIG["output_dir"]
    original_static_site_dir = CONFIG["static_site_dir"]
    
    # テスト用のパスに変更
    CONFIG["output_dir"] = str(test_output_dir)
    CONFIG["static_site_dir"] = str(test_static_site_dir)
    
    # モック環境を作成
    return MockGitHub()

def restore_config():
    """
    元の設定を復元する
    """
    CONFIG["output_dir"] = original_output_dir
    CONFIG["static_site_dir"] = original_static_site_dir

def run_test():
    """
    テストを実行
    """
    logger.info("テスト環境をセットアップします")
    mock_gh = setup_test_environment()
    
    # 元のスクリプトの実行関数をモック関数で置き換え
    original_run_gh_command = collect_openapi.run_gh_command
    collect_openapi.run_gh_command = lambda command: run_mock_gh_command(mock_gh, command)
    
    try:
        # スクリプトを実行
        logger.info("OpenAPI仕様書収集スクリプトを実行します")
        collect_openapi.main()
        
        # 結果を確認
        test_output_dir = Path(CONFIG["output_dir"])
        test_static_site_dir = Path(CONFIG["static_site_dir"])
        
        if test_output_dir.exists() and test_static_site_dir.exists():
            logger.info("テスト成功: 出力ディレクトリとサイトが生成されました")
            
            # 作成されたファイル一覧を表示
            logger.info("--- 出力ディレクトリの内容 ---")
            for item in test_output_dir.glob("**/*"):
                if item.is_file():
                    logger.info(f"  {item.relative_to(test_output_dir)}")
            
            logger.info("--- 静的サイトディレクトリの内容 ---")
            for item in test_static_site_dir.glob("**/*"):
                if item.is_file():
                    logger.info(f"  {item.relative_to(test_static_site_dir)}")
            
            logger.info(f"テスト出力は {test_output_dir} と {test_static_site_dir} に保存されています")
            return True
        else:
            logger.error("テスト失敗: 出力ディレクトリまたはサイトが生成されませんでした")
            return False
    
    finally:
        # 元の関数と設定を復元
        collect_openapi.run_gh_command = original_run_gh_command
        restore_config()

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)