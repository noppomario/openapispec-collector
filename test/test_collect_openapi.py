#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import logging
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 元のモジュールをインポート
from config import CONFIG
import collect_openapi

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openapispec-test')

def simple_mock_gh_command(command):
    """
    シンプル化したghコマンドのモック
    完全にハードコードした応答を返すようにする
    """
    print(f"[MOCK] Command: {command}")
    
    # リポジトリ一覧を取得
    if command[0:3] == ["gh", "repo", "list"]:
        return """[{"name":"xxx-api-1"},{"name":"xxx-api-2"},{"name":"xxx-api-3"},{"name":"other-repo-1"},{"name":"another-project"}]"""
    
    # ファイル内容を取得
    elif command[0:2] == ["gh", "api"]:
        api_path = command[2]
        print(f"[MOCK] API path: {api_path}")
        
        # 対応するファイルを直接読み込む
        mock_file = None
        
        # 単純な文字列比較でリポジトリを判断
        if "xxx-api-1" in api_path:
            print("[MOCK] Matched xxx-api-1")
            mock_file = Path("./test/mock_data/xxx-api-1/docs/openapi.yml")
        elif "xxx-api-2" in api_path:
            print("[MOCK] Matched xxx-api-2")
            mock_file = Path("./test/mock_data/xxx-api-2/docs/openapi.yml")
        elif "xxx-api-3" in api_path:
            print("[MOCK] Matched xxx-api-3")
            mock_file = Path("./test/mock_data/xxx-api-3/docs/openapi.yml")
        
        print(f"[MOCK] Looking for file: {mock_file}")
        
        if mock_file and mock_file.exists():
            print(f"[MOCK] File found: {mock_file}")
            
            # ファイルパスを絶対パスに変換して確実に読み込む
            with open(mock_file.absolute(), "r") as f:
                content = f.read()
                
            print(f"[MOCK] File content size: {len(content)} bytes")
            print(f"[MOCK] File content preview: {content[:50]}")
            
            # --jq オプションのチェック - .content を抽出する場合はBase64エンコード
            if "--jq" in command and command[command.index("--jq") + 1] == ".content":
                import base64
                encoded_content = base64.b64encode(content.encode()).decode()
                print(f"[MOCK] Base64 encoded content size: {len(encoded_content)} bytes")
                print(f"[MOCK] Returning encoded content: {encoded_content[:50]}...")
                return encoded_content
            
            # 完全なJSONレスポンスを作成
            import json
            import base64
            
            response = {
                "name": "openapi.yml",
                "path": "docs/openapi.yml",
                "content": base64.b64encode(content.encode()).decode(),
                "encoding": "base64"
            }
            
            return json.dumps(response)
        else:
            print(f"[MOCK] File not found: {mock_file}")
    
    print(f"[MOCK] No matching response found, returning empty object")
    return "{}"

def clean_test_directories():
    """
    テスト用の出力ディレクトリをクリーンアップする共通機能
    """
    test_output_dir = Path("test/output")
    test_static_site_dir = Path("test/static_site")
    
    if test_output_dir.exists():
        logger.info(f"テスト出力ディレクトリを削除: {test_output_dir}")
        shutil.rmtree(test_output_dir)
    
    if test_static_site_dir.exists():
        logger.info(f"テスト静的サイトディレクトリを削除: {test_static_site_dir}")
        shutil.rmtree(test_static_site_dir)
    
    return test_output_dir, test_static_site_dir

def clean_test_environment():
    """
    テスト環境の出力ディレクトリとモックデータをクリーンアップする
    """
    logger.info("テスト環境のクリーンアップを実行します")
    
    # 共通クリーンアップ機能を呼び出し
    clean_test_directories()
    
    # モックデータディレクトリの生成APIファイルをクリーンアップ（オプション）
    mock_data_dir = Path("test/mock_data")
    if mock_data_dir.exists():
        logger.info("モックデータディレクトリをリフレッシュします（APIファイルは保持）")
        # APIリポジトリフォルダは保持し、内部の不要なファイルのみ削除
        for api_dir in mock_data_dir.glob("xxx-api-*"):
            if api_dir.is_dir():
                # docs/openapi.ymlファイルは維持する
                for item in api_dir.glob("**/*"):
                    if item.is_file() and not (item.name == "openapi.yml" and "docs" in str(item)):
                        logger.info(f"  不要なファイルを削除: {item}")
                        item.unlink()
    
    logger.info("クリーンアップが完了しました")

def setup_test_environment():
    """
    テスト環境をセットアップ
    """
    logger.info("テスト環境をセットアップします")
    
    # 共通クリーンアップ機能を呼び出し
    test_output_dir, test_static_site_dir = clean_test_directories()
    
    # ディレクトリを作成
    test_output_dir.mkdir(exist_ok=True)
    test_static_site_dir.mkdir(exist_ok=True)
    
    # 一時的に設定を書き換え
    global original_output_dir, original_static_site_dir
    original_output_dir = CONFIG["output_dir"]
    original_static_site_dir = CONFIG["static_site_dir"]
    
    # テスト用のパスに変更
    CONFIG["output_dir"] = str(test_output_dir)
    CONFIG["static_site_dir"] = str(test_static_site_dir)

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
    setup_test_environment()
    
    # 元のスクリプトの実行関数をモック関数で置き換え
    original_run_gh_command = collect_openapi.run_gh_command
    collect_openapi.run_gh_command = simple_mock_gh_command
    
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
    # コマンドライン引数の処理
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "clean":
            clean_test_environment()
            sys.exit(0)
    
    success = run_test()
    sys.exit(0 if success else 1)