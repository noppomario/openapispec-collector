#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import shutil
import logging
import sys
from pathlib import Path
import yaml
from config import CONFIG

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    
    # ghコマンドでリポジトリ一覧をJSON形式で取得
    command = [
        "gh", "repo", "list", 
        CONFIG["organization"],
        "--json", "name", 
        "--limit", str(CONFIG["repo_limit"])
    ]
    
    output = run_gh_command(command)
    repos = json.loads(output)
    
    # xxx-api パターンに一致するリポジトリをフィルタリング
    api_repos = [repo["name"] for repo in repos if CONFIG["repo_pattern"] in repo["name"]]
    
    logger.info(f"{len(api_repos)}個のAPIリポジトリが見つかりました")
    return api_repos

def fetch_openapi_spec(repo_name):
    """
    リポジトリからOpenAPI仕様書を取得する
    """
    output_dir = Path(CONFIG["output_dir"])
    output_dir.mkdir(exist_ok=True)
    repo_output_dir = output_dir / repo_name
    repo_output_dir.mkdir(exist_ok=True)
    
    logger.info(f"{repo_name}からOpenAPI仕様書を取得します")
    
    # リポジトリ内の特定ファイルを取得
    spec_path = CONFIG["spec_path"]  # 例: "docs/openapi.yml"
    
    try:
        # ghコマンドでファイルの内容を取得
        command = [
            "gh", "api", 
            f"/repos/{CONFIG['organization']}/{repo_name}/contents/{spec_path}",
            "--jq", ".content"
        ]
        
        content_response = run_gh_command(command).strip()
        
        # Base64デコード処理
        import base64
        content = ""
        
        try:
            # Base64デコードを試みる
            # 引用符が含まれている場合は除去
            if content_response.startswith('"') and content_response.endswith('"'):
                content_response = content_response[1:-1]
            
            # エスケープされた文字を処理
            cleaned_content = content_response.replace('\\n', '').replace('\\', '')
            
            # Base64デコード
            content = base64.b64decode(cleaned_content).decode('utf-8')
            logger.debug(f"Base64デコードに成功しました: {len(content)} バイト")
        except Exception as e:
            logger.warning(f"Base64デコードに失敗しました: {e}. そのまま処理を続行します")
            content = content_response
        
        # 内容が空でないか確認
        if not content.strip():
            logger.warning(f"取得したコンテンツが空です: {repo_name}")
        
        # ファイルに保存
        output_file = repo_output_dir / Path(spec_path).name
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file
    
    except Exception as e:
        logger.error(f"{repo_name}の仕様書取得中にエラーが発生しました: {e}")
        return None

def generate_static_site():
    """
    収集したOpenAPI仕様書から静的サイトを生成
    """
    output_dir = Path(CONFIG["output_dir"])
    static_site_dir = Path(CONFIG["static_site_dir"])
    static_site_dir.mkdir(exist_ok=True)
    
    logger.info("静的サイトの生成を開始します")
    
    # index.htmlを生成
    index_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OpenAPI Specification Collection</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body>
    <div class="container mt-5">
        <h1>OpenAPI Specification Collection</h1>
        <ul class="list-group mt-4">
"""
    
    # 収集したすべての仕様書をリスト化
    specs = []
    for repo_dir in output_dir.iterdir():
        if repo_dir.is_dir():
            # メソッドチェーン修正：glob結果をリストとして処理
            yml_files = list(repo_dir.glob("*.yml"))
            yaml_files = list(repo_dir.glob("*.yaml"))
            spec_files = yml_files + yaml_files
            
            for spec_file in spec_files:
                repo_name = repo_dir.name
                spec_path = f"{repo_name}/{spec_file.name}"
                
                # 仕様書をコピー
                dest_dir = static_site_dir / repo_name
                dest_dir.mkdir(exist_ok=True)
                shutil.copy2(spec_file, dest_dir)
                
                # APIのタイトルを抽出（可能であれば）
                title = repo_name
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        spec_data = yaml.safe_load(f)
                        if spec_data and 'info' in spec_data and 'title' in spec_data['info']:
                            title = spec_data['info']['title']
                except Exception as e:
                    logger.warning(f"{spec_file}からタイトル情報を抽出できませんでした: {e}")
                
                # SwaggerUIとReDocへのリンクを作成
                swagger_link = f"swagger-ui.html?url={spec_path}"
                redoc_link = f"redoc.html?url={spec_path}"
                
                specs.append({
                    "title": title,
                    "repo": repo_name,
                    "path": spec_path,
                    "swagger_link": swagger_link,
                    "redoc_link": redoc_link
                })
    
    # indexページにリンクを追加
    for spec in specs:
        index_content += f"""        <li class="list-group-item">
            <h5>{spec['title']}</h5>
            <p>Repository: {spec['repo']}</p>
            <div>
                <a href="{spec['swagger_link']}" class="btn btn-primary btn-sm" target="_blank">Swagger UI</a>
                <a href="{spec['redoc_link']}" class="btn btn-success btn-sm" target="_blank">ReDoc</a>
            </div>
        </li>
"""
    
    index_content += """        </ul>
    </div>
</body>
</html>
"""
    
    # index.htmlを保存
    with open(static_site_dir / "index.html", "w", encoding='utf-8') as f:
        f.write(index_content)
    
    # Swagger UIページを作成
    swagger_ui_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: new URL(document.location).searchParams.get("url"),
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [SwaggerUIBundle.presets.apis],
                layout: "BaseLayout"
            });
        };
    </script>
</body>
</html>
"""
    
    with open(static_site_dir / "swagger-ui.html", "w", encoding='utf-8') as f:
        f.write(swagger_ui_html)
    
    # ReDocページを作成
    redoc_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ReDoc</title>
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
        #redoc-container { background-color: white; }
    </style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
    <script>
        const specUrl = new URL(document.location).searchParams.get("url");
        Redoc.init(specUrl, {
            scrollYOffset: 50
        }, document.getElementById('redoc-container'));
    </script>
</body>
</html>
"""
    
    with open(static_site_dir / "redoc.html", "w", encoding='utf-8') as f:
        f.write(redoc_html)
    
    logger.info(f"静的サイトが {static_site_dir} に生成されました")
    return len(specs)

def clean_directories():
    """
    出力ディレクトリと静的サイトディレクトリをクリーンアップする共通機能
    """
    output_dir = Path(CONFIG["output_dir"])
    static_site_dir = Path(CONFIG["static_site_dir"])
    
    if output_dir.exists():
        logger.info(f"出力ディレクトリを削除: {output_dir}")
        shutil.rmtree(output_dir)
    
    if static_site_dir.exists():
        logger.info(f"静的サイトディレクトリを削除: {static_site_dir}")
        shutil.rmtree(static_site_dir)
    
    return output_dir, static_site_dir

def clean():
    """
    出力ディレクトリと静的サイトディレクトリをクリーンアップする
    """
    logger.info("クリーンアップを実行します")
    clean_directories()
    logger.info("クリーンアップが完了しました")

def main():
    """
    メイン処理
    """
    # コマンドライン引数の処理
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "clean":
            clean()
            return
    
    logger.info("OpenAPI仕様書収集を開始します")
    
    # 出力ディレクトリを作成
    output_dir, _ = clean_directories()
    output_dir.mkdir(exist_ok=True)
    
    # API関連リポジトリの一覧を取得
    api_repos = get_api_repositories()
    
    if not api_repos:
        logger.warning("対象のリポジトリが見つかりませんでした")
        return
    
    # 各リポジトリからOpenAPI仕様書を取得
    successful_specs = 0
    for repo in api_repos:
        try:
            output_file = fetch_openapi_spec(repo)
            if output_file:
                successful_specs += 1
                logger.info(f"{repo}の仕様書を正常に取得しました: {output_file}")
        except Exception as e:
            logger.error(f"{repo}の処理中にエラーが発生しました: {e}")
    
    # 静的サイトの生成
    if successful_specs > 0:
        specs_count = generate_static_site()
        logger.info(f"合計 {specs_count} 件の仕様書を使用して静的サイトを生成しました")
    else:
        logger.warning("有効な仕様書が1つも取得できなかったため、静的サイトは生成されませんでした")
    
    logger.info("処理が完了しました")

if __name__ == "__main__":
    main()