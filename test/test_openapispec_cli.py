#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import logging
from pathlib import Path

# src配下のモジュールをimportするよう修正
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import CONFIG
import src.gh_utils as gh_utils
import src.site_generator as site_generator
import src.cleaner as cleaner

# collect_openapi.pyの代わりにCLIの関数を直接importする場合は、
# openapispec_cli.pyのcollect_only/all_processなどをimportしてもよい

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openapispec-test')

def simple_mock_gh_command(command):
    print(f"[MOCK] Command: {command}")
    # リポジトリ一覧を取得
    if command[0:3] == ["gh", "repo", "list"]:
        return """[{\"name\":\"xxx-api-1\"},{\"name\":\"xxx-api-2\"},{\"name\":\"xxx-api-3\"},{\"name\":\"other-repo-1\"},{\"name\":\"another-project\"}]"""
    # パターン付きYAML一覧取得
    elif command[0:2] == ["gh", "api"] and "/contents/docs/paths" in command[2] and "--jq" in command and "/contents/docs/paths/" not in command[2]:
        import re
        jq_arg = command[command.index("--jq") + 1]
        import re as _re
        m = _re.search(r'test\\?\("(.*?)\\?"\)', jq_arg)
        if m:
            regex = m.group(1)
        else:
            regex = None
        files = ["openapi.yml", "subapi.yml"]
        if regex:
            files = [f for f in files if re.match(regex, f)]
        print(f"[MOCK] Returning file list for {command[2]}: {files}")
        return "\n".join(files)
    # docs/paths配下のYAMLファイル内容取得
    elif command[0:2] == ["gh", "api"] and "/contents/docs/paths/" in command[2] and "--jq" in command and command[-1] == ".content":
        import base64
        api_path = command[2]
        repo = None
        yml = None
        for r in ["xxx-api-1", "xxx-api-2", "xxx-api-3"]:
            if r in api_path:
                repo = r
        if repo:
            yml = api_path.split("/contents/docs/paths/")[-1]
            mock_file = Path(f"test/mock_data/{repo}/docs/paths/{yml}")
            print(f"[MOCK] Looking for file: {mock_file} (abs: {mock_file.absolute()}) exists={mock_file.exists()}")
            if mock_file.exists():
                with open(mock_file, "r") as f:
                    content = f.read()
                encoded_content = base64.b64encode(content.encode()).decode()
                print(f"[MOCK] Returning base64 for {mock_file}: {encoded_content[:60]} ...")
                return encoded_content
            else:
                print(f"[MOCK] File not found for base64: {mock_file}")
                return ""
        return ""

    print(f"[MOCK] No matching response found, returning empty object")
    return "{}"

def clean_test_directories():
    """
    テスト用の出力ディレクトリをクリーンアップする共通機能
    """
    test_static_site_dir = Path("static_site")
    
    if test_static_site_dir.exists():
        logger.info(f"テスト静的サイトディレクトリを削除: {test_static_site_dir}")
        shutil.rmtree(test_static_site_dir)
    
    return test_static_site_dir

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
    test_static_site_dir = clean_test_directories()
    
    # ディレクトリを作成
    test_static_site_dir.mkdir(exist_ok=True)
    
    # 一時的に設定を書き換え
    global original_static_site_dir
    original_static_site_dir = CONFIG["static_site_dir"]
    
    # テスト用のパスに変更
    CONFIG["static_site_dir"] = str(test_static_site_dir)

def restore_config():
    """
    元の設定を復元する
    """
    CONFIG["static_site_dir"] = original_static_site_dir

def run_test():
    logger.info("テスト環境をセットアップします")
    setup_test_environment()
    original_run_gh_command = gh_utils.run_gh_command
    gh_utils.run_gh_command = simple_mock_gh_command
    try:
        logger.info("OpenAPI仕様書収集スクリプトを実行します")
        test_static_site_dir = Path(CONFIG["static_site_dir"])
        test_static_site_dir.mkdir(exist_ok=True)
        api_repos = gh_utils.get_api_repositories()
        successful_specs = 0
        for repo in api_repos:
            output_files = gh_utils.fetch_openapi_specs(repo)
            if output_files:
                successful_specs += len(output_files)
        if successful_specs > 0:
            site_generator.generate_static_site()
            site_generator.generate_integrated_viewer()
        
        # 結果を確認
        if test_static_site_dir.exists():
            logger.info("テスト成功: 静的サイトが生成されました")
            
            # 必須ファイルの存在を確認
            required_files = [
                "index.html",
                "swagger-ui.html",
                "redoc.html",
                "api-spec-viewer.html",
                "xxx-api-1/docs/paths/openapi.yml",
                "xxx-api-1/docs/paths/subapi.yml",
                "xxx-api-2/docs/paths/openapi.yml",
                "xxx-api-2/docs/paths/subapi.yml",
                "xxx-api-3/docs/paths/openapi.yml",
                "xxx-api-3/docs/paths/subapi.yml"
            ]
            
            # 作成されたファイル一覧を表示
            logger.info("--- 静的サイトディレクトリの内容 ---")
            missing_files = []
            for required_file in required_files:
                file_path = test_static_site_dir / required_file
                if file_path.exists():
                    logger.info(f"  {required_file}")
                else:
                    missing_files.append(required_file)
                    logger.error(f"  {required_file} - 見つかりません")
            
            if missing_files:
                logger.error(f"必須ファイルが {len(missing_files)} 個見つかりませんでした")
                return False
            
            logger.info(f"テスト出力は {test_static_site_dir} に保存されています")
            return True
        else:
            logger.error("テスト失敗: 静的サイトが生成されませんでした")
            return False
    
    finally:
        # 元の関数と設定を復元
        gh_utils.run_gh_command = original_run_gh_command
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