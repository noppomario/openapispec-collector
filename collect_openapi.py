#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import shutil
import logging
import sys
import base64
from pathlib import Path
import yaml
import requests
from jinja2 import Environment, FileSystemLoader
from config import CONFIG

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openapispec-collector')

# 静的アセットのパス
STATIC_ASSETS_DIR = Path(__file__).parent / "static_assets"
TEMPLATES_DIR = STATIC_ASSETS_DIR / "templates"
CSS_DIR = STATIC_ASSETS_DIR / "css"
JS_DIR = STATIC_ASSETS_DIR / "js"

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
    指定されたリポジトリからOpenAPI仕様書を取得
    """
    logger.info(f"{repo_name}からOpenAPI仕様書を取得します")
    
    # GitHubからファイル内容を取得
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
        
        # Base64デコード
        content = base64.b64decode(encoded_content).decode('utf-8')
        
        # 保存先ディレクトリを作成
        static_site_dir = Path(CONFIG["static_site_dir"])
        repo_dir = static_site_dir / repo_name
        repo_dir.mkdir(exist_ok=True, parents=True)
        
        # 仕様書を保存
        spec_file = repo_dir / "openapi.yml"
        with open(spec_file, "w", encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"{repo_name}の仕様書を正常に取得しました: {spec_file}")
        return spec_file
    
    except Exception as e:
        logger.error(f"{repo_name}の仕様書取得中にエラーが発生しました: {e}")
        return None

def generate_static_site():
    """
    収集したOpenAPI仕様書から静的サイトを生成
    """
    static_site_dir = Path(CONFIG["static_site_dir"])
    
    logger.info("静的サイトの生成を開始します")
    
    # 静的アセットのディレクトリを作成してCSSとJSファイルをコピー
    static_css_dir = static_site_dir / "static" / "css"
    static_css_dir.mkdir(exist_ok=True, parents=True)
    
    # CSSファイルをコピー
    try:
        shutil.copy2(CSS_DIR / "styles.css", static_css_dir / "styles.css")
        logger.info(f"CSSファイルをコピーしました: {static_css_dir / 'styles.css'}")
    except Exception as e:
        logger.error(f"CSSファイルのコピー中にエラーが発生しました: {e}")
    
    # index.htmlを生成
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("index.html")
    
    # 収集したすべての仕様書をリスト化
    specs = []
    api_specs = {}  # API仕様書データをJSONとして保持
    
    for repo_dir in static_site_dir.iterdir():
        if repo_dir.is_dir() and repo_dir.name != "static":  # staticディレクトリは除外
            yml_files = list(repo_dir.glob("*.yml"))
            yaml_files = list(repo_dir.glob("*.yaml"))
            spec_files = yml_files + yaml_files
            
            for spec_file in spec_files:
                repo_name = repo_dir.name
                spec_path = f"{repo_name}/{spec_file.name}"
                
                # APIのタイトルを抽出
                title = repo_name
                spec_data = None
                
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        spec_data = yaml.safe_load(content)
                        if spec_data and 'info' in spec_data and 'title' in spec_data['info']:
                            title = spec_data['info']['title']
                        
                        # API仕様データをJSONとして保持
                        api_specs[spec_path] = spec_data
                except Exception as e:
                    logger.warning(f"{spec_file}からタイトル情報を抽出できませんでした: {e}")
                
                # SwaggerUIとReDocへのリンクを作成
                swagger_link = f"swagger-ui.html?url={spec_path}"
                redoc_link = f"redoc.html?url={spec_path}"
                
                specs.append({
                    "title": title,
                    "repo": repo_name,
                    "path": spec_path,
                    "data": json.dumps(spec_data),  # APIの仕様データをJSON文字列として含める
                    "swagger_link": swagger_link,
                    "redoc_link": redoc_link
                })
    
    # ReDocテンプレートを読み込みBase64エンコード
    redoc_template_path = TEMPLATES_DIR / "redoc.html"
    redoc_template_base64 = ""
    try:
        with open(redoc_template_path, 'r', encoding='utf-8') as f:
            redoc_template = f.read()
            redoc_template_base64 = base64.b64encode(redoc_template.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"ReDocテンプレート読み込み中にエラーが発生: {e}")

    # Swagger UI CSSを読み込む
    swagger_ui_css = ""
    try:
        swagger_ui_css_url = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
        response = requests.get(swagger_ui_css_url)
        if response.status_code == 200:
            swagger_ui_css = response.text
    except Exception as e:
        logger.warning(f"Swagger UI CSSの読み込みに失敗しました: {e}")
    
    # カスタムCSSを読み込む
    custom_css = ""
    try:
        css_path = CSS_DIR / "styles.css"
        with open(css_path, 'r', encoding='utf-8') as f:
            custom_css = f.read()
    except Exception as e:
        logger.warning(f"カスタムCSSの読み込みに失敗しました: {e}")
    
    # JavaScriptファイルを読み込む
    js_content = {}
    js_files = {
        "js_search": JS_DIR / "search.js", 
        "js_viewer": JS_DIR / "viewer.js", 
        "js_main": JS_DIR / "main.js"
    }
    
    for name, file_path in js_files.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                js_content[name] = f.read()
                logger.info(f"JavaScriptファイルを読み込みました: {name} ({len(js_content[name])} バイト)")
        except Exception as e:
            logger.error(f"JavaScriptファイルの読み込み中にエラーが発生しました: {file_path}, エラー: {e}")
            js_content[name] = f"/* Error loading: {file_path}, {str(e)} */"
    
    # index.htmlを保存
    rendered_html = template.render(
        specs=specs,
        redoc_template_base64=redoc_template_base64,
        swagger_ui_css=swagger_ui_css,
        custom_css=custom_css,
        **js_content  # JavaScriptコンテンツを展開
    )
    
    with open(static_site_dir / "index.html", "w", encoding='utf-8') as f:
        f.write(rendered_html)
    
    # Swagger UIページを作成
    shutil.copy2(TEMPLATES_DIR / "swagger-ui.html", static_site_dir / "swagger-ui.html")
    
    # ReDocページを作成
    shutil.copy2(TEMPLATES_DIR / "redoc.html", static_site_dir / "redoc.html")
    
    logger.info(f"静的サイトが {static_site_dir} に生成されました")
    return len(specs)

def generate_integrated_viewer():
    """
    すべてのリソースを1つのHTMLファイルにバンドルした統合ビューアを生成
    """
    logger.info(f"統合ビューアの生成を開始します [出力先: {CONFIG['static_site_dir']}]")
    
    static_site_dir = Path(CONFIG["static_site_dir"])
    if not static_site_dir.exists():
        logger.warning(f"静的サイトディレクトリが存在しません: {static_site_dir}")
        static_site_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"静的サイトディレクトリを作成しました: {static_site_dir}")
    
    # API仕様書を読み込む
    api_specs = {}
    total_size = 0
    spec_count = 0
    
    for repo_dir in static_site_dir.iterdir():
        if repo_dir.is_dir():
            yml_files = list(repo_dir.glob("*.yml"))
            yaml_files = list(repo_dir.glob("*.yaml"))
            spec_files = yml_files + yaml_files
            
            for spec_file in spec_files:
                repo_name = repo_dir.name
                spec_path = f"{repo_name}/{spec_file.name}"
                
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        size = len(content)
                        logger.info(f"仕様書を読み込みました: {spec_file.name} ({size} バイト)")
                        total_size += size
                        spec_count += 1
                        
                        # YAML形式の仕様書をJSONに変換
                        spec_data = yaml.safe_load(content)
                        api_specs[spec_path] = spec_data
                        
                except Exception as e:
                    logger.error(f"仕様書の読み込み中にエラーが発生: {spec_file} - {e}")
    
    logger.info(f"合計 {spec_count} 件の仕様書を読み込みました (合計サイズ: {total_size} バイト)")
    
    try:
        # テンプレートエンジンをセットアップ
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        
        # ReDocテンプレートをBase64エンコード
        redoc_template_path = TEMPLATES_DIR / "redoc.html"
        with open(redoc_template_path, 'r', encoding='utf-8') as f:
            redoc_template = f.read()
            redoc_template_base64 = base64.b64encode(redoc_template.encode('utf-8')).decode('utf-8')
        
        # すべてのCSS/JSコンテンツを読み込む
        # 1. 外部リソース（CDN）から取得
        external_resources = {
            "swagger_ui_css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            "swagger_ui_js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            "redoc_js": "https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"
        }
        
        resource_contents = {}
        for name, url in external_resources.items():
            try:
                logger.info(f"外部リソースを取得中: {url}")
                response = requests.get(url)
                if response.status_code == 200:
                    resource_contents[name] = response.text
                    logger.info(f"外部リソースを取得しました: {name} ({len(response.text)} バイト)")
                else:
                    logger.warning(f"リソースの取得に失敗しました: {url}, ステータスコード: {response.status_code}")
                    resource_contents[name] = f"/* Failed to load: {url} */"
            except Exception as e:
                logger.error(f"リソース取得中にエラーが発生しました: {url}, エラー: {e}")
                resource_contents[name] = f"/* Error loading: {url}, {str(e)} */"
        
        # 2. ローカルのJavaScriptファイルを読み込む
        js_files = {
            "js_search": JS_DIR / "search.js", 
            "js_viewer": JS_DIR / "viewer.js", 
            "js_main": JS_DIR / "main.js"
        }
        
        for name, file_path in js_files.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    resource_contents[name] = f.read()
                    logger.info(f"JavaScriptファイルを読み込みました: {name} ({len(resource_contents[name])} バイト)")
            except Exception as e:
                logger.error(f"JavaScriptファイルの読み込み中にエラーが発生しました: {file_path}, エラー: {e}")
                resource_contents[name] = f"/* Error loading: {file_path}, {str(e)} */"
        
        # 3. ローカルのCSSファイルを読み込む
        try:
            css_path = CSS_DIR / "styles.css"
            with open(css_path, 'r', encoding='utf-8') as f:
                resource_contents["custom_css"] = f.read()
                logger.info(f"CSSファイルを読み込みました: custom_css ({len(resource_contents['custom_css'])} バイト)")
        except Exception as e:
            logger.error(f"CSSファイルの読み込み中にエラーが発生しました: {css_path}, エラー: {e}")
            resource_contents["custom_css"] = f"/* Error loading: {css_path}, {str(e)} */"
        
        # テンプレートをレンダリング
        template = env.get_template("api-spec-viewer.html")
        
        # すべてのリソースをテンプレートに渡す
        context = {
            "api_specs_json": json.dumps(api_specs),
            "redoc_template_base64": redoc_template_base64,
            **resource_contents  # すべてのCSSとJSコンテンツを展開
        }
        
        rendered_html = template.render(**context)
        
        # 出力先パスを設定
        viewer_file = static_site_dir / "api-spec-viewer.html"
        logger.info(f"統合ビューアを保存します: {viewer_file}")
        
        # HTMLファイルに書き込む前にディレクトリの存在を確認
        if not viewer_file.parent.exists():
            logger.warning(f"親ディレクトリが存在しません: {viewer_file.parent}")
            viewer_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"親ディレクトリを作成しました: {viewer_file.parent}")
        
        # ファイルに保存
        with open(viewer_file, "w", encoding='utf-8') as f:
            f.write(rendered_html)
        
        # ファイルサイズの確認
        file_size = os.path.getsize(viewer_file)
        logger.info(f"統合ビューアを保存しました: {viewer_file} (サイズ: {file_size} バイト)")
        
        return viewer_file
        
    except MemoryError as e:
        logger.error(f"メモリ不足エラー: {e}")
        logger.error("API仕様データが大きすぎる可能性があります。データサイズを減らして再試行してください。")
        return None
        
    except Exception as e:
        import traceback
        logger.error(f"統合ビューア生成中にエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        return None

def clean_directories():
    """
    出力ディレクトリと静的サイトディレクトリをクリーンアップする共通機能
    """
    static_site_dir = Path(CONFIG["static_site_dir"])
    
    if static_site_dir.exists():
        logger.info(f"静的サイトディレクトリを削除: {static_site_dir}")
        shutil.rmtree(static_site_dir)
    
    return static_site_dir

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
        elif command == "viewer":
            generate_integrated_viewer()
            return
    
    logger.info("OpenAPI仕様書収集を開始します")
    
    # 静的サイトディレクトリを作成
    static_site_dir = clean_directories()
    static_site_dir.mkdir(exist_ok=True)
    
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

        # 統合ビューアを生成
        generate_integrated_viewer()
    else:
        logger.warning("有効な仕様書が1つも取得できなかったため、静的サイトは生成されませんでした")
    
    logger.info("処理が完了しました")

if __name__ == "__main__":
    main()