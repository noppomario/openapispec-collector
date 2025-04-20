import json
import subprocess
import base64
import logging
from pathlib import Path
from src.config import CONFIG

logger = logging.getLogger('openapispec-collector')

def run_gh_command(command):
    """
    ghコマンドを実行する関数
    """
    logger.info(f"実行: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"コマンド実行エラー: {e}")
        logger.error(f"エラー出力: {e.stderr}")
        raise

def get_api_repositories():
    """
    GitHub上のxxx-apiというパターンに一致するリポジトリ一覧を取得
    """
    logger.info("APIリポジトリの取得を開始します")
    command = [
        "gh", "repo", "list",
        CONFIG["organization"],
        "--json", "name",
        "--limit", str(CONFIG["repo_limit"])
    ]
    output = run_gh_command(command)
    repos = json.loads(output)
    api_repos = [repo["name"] for repo in repos if CONFIG["repo_pattern"] in repo["name"]]
    logger.info(f"{len(api_repos)}個のAPIリポジトリが見つかりました")
    return api_repos

def fetch_openapi_spec(repo_name):
    """
    指定されたリポジトリからOpenAPI仕様書を取得
    """
    logger.info(f"{repo_name}からOpenAPI仕様書を取得します")
    command = [
        "gh", "api",
        f"/repos/{CONFIG['organization']}/{repo_name}/contents/{CONFIG['spec_path']}",
        "--jq", ".content"
    ]
    try:
        encoded_content = run_gh_command(command)
        if not encoded_content:
            logger.warning(f"{repo_name}の仕様書が見つかりませんでした")
            return None
        content = base64.b64decode(encoded_content).decode('utf-8')
        static_site_dir = Path(CONFIG["static_site_dir"])
        repo_dir = static_site_dir / repo_name
        repo_dir.mkdir(exist_ok=True, parents=True)
        spec_file = repo_dir / "openapi.yml"
        with open(spec_file, "w", encoding='utf-8') as f:
            f.write(content)
        logger.info(f"{repo_name}の仕様書を正常に取得しました: {spec_file}")
        return spec_file
    except Exception as e:
        logger.error(f"{repo_name}の仕様書取得中にエラーが発生しました: {e}")
        return None

def fetch_openapi_specs(repo_name):
    """
    指定されたリポジトリからspec_pathで指定されたパターンに一致するYAMLファイルをすべて取得し、
    それぞれを独立したAPI仕様書として保存する
    保存先は static_site/リポジトリ名/パス/ファイル名.yml
    """
    import re
    import requests
    logger.info(f"{repo_name}からOpenAPI仕様書群を取得します")
    spec_pattern = CONFIG["spec_path"]  # 例: docs/*.yml, docs/path/*.yml
    if "/" in spec_pattern:
        dir_part, file_pattern = spec_pattern.rsplit("/", 1)
    else:
        dir_part, file_pattern = "", spec_pattern
    # パターンを正規表現に変換
    regex_pattern = re.escape(file_pattern).replace(r"\*", ".*") + "$"
    command = [
        "gh", "api",
        f"/repos/{CONFIG['organization']}/{repo_name}/contents/{dir_part}",
        "--jq", f".[] | select(.name | test(\"{regex_pattern}\")) | .name"
    ]
    try:
        output = run_gh_command(command)
        yml_files = [line.strip() for line in output.splitlines() if line.strip()]
        if not yml_files:
            logger.warning(f"{repo_name}/{dir_part}に{file_pattern}に一致するYAMLファイルが見つかりませんでした")
            return []
        static_site_dir = Path(CONFIG["static_site_dir"])
        saved_files = []
        for yml_file in yml_files:
            spec_file = static_site_dir / repo_name / dir_part / yml_file
            spec_file.parent.mkdir(exist_ok=True, parents=True)
            file_command = [
                "gh", "api",
                f"/repos/{CONFIG['organization']}/{repo_name}/contents/{dir_part}/{yml_file}",
                "--jq", ".content"
            ]
            print(f"[DEBUG] file_command: {file_command}")
            encoded_content = run_gh_command(file_command)
            if not encoded_content:
                logger.warning(f"{repo_name}/{dir_part}/{yml_file} の仕様書が見つかりませんでした")
                continue
            content = base64.b64decode(encoded_content.strip()).decode('utf-8')
            with open(spec_file, "w", encoding='utf-8') as f:
                f.write(content)
            logger.info(f"{repo_name}/{dir_part}/{yml_file} の仕様書を正常に取得しました: {spec_file}")
            saved_files.append(spec_file)
        return saved_files
    except Exception as e:
        logger.error(f"{repo_name}の仕様書群取得中にエラーが発生しました: {e}")
        return []
