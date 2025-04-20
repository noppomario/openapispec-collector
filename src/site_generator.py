import os
import json
import shutil
import base64
import logging
from pathlib import Path
import yaml
import requests
from jinja2 import Environment, FileSystemLoader
from src.config import CONFIG

logger = logging.getLogger('openapispec-collector')

# 静的アセットのパス
STATIC_ASSETS_DIR = Path(__file__).parent.parent / "static_assets"
TEMPLATES_DIR = STATIC_ASSETS_DIR / "templates"
CSS_DIR = STATIC_ASSETS_DIR / "css"
JS_DIR = STATIC_ASSETS_DIR / "js"

def generate_static_site():
    static_site_dir = Path(CONFIG["static_site_dir"])
    logger.info("静的サイトの生成を開始します")
    static_css_dir = static_site_dir / "static" / "css"
    static_css_dir.mkdir(exist_ok=True, parents=True)
    try:
        shutil.copy2(CSS_DIR / "styles.css", static_css_dir / "styles.css")
        logger.info(f"CSSファイルをコピーしました: {static_css_dir / 'styles.css'}")
    except Exception as e:
        logger.error(f"CSSファイルのコピー中にエラーが発生しました: {e}")
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("index.html")
    specs = []
    api_specs = {}
    for repo_dir in static_site_dir.iterdir():
        if repo_dir.is_dir() and repo_dir.name != "static":
            spec_pattern = CONFIG["spec_path"]
            if "/" in spec_pattern:
                dir_part, file_pattern = spec_pattern.rsplit("/", 1)
            else:
                dir_part, file_pattern = "", spec_pattern
            search_dir = repo_dir / dir_part if dir_part else repo_dir
            if search_dir.exists() and search_dir.is_dir():
                yml_files = list(search_dir.rglob(file_pattern))
                for spec_file in yml_files:
                    repo_name = repo_dir.name
                    rel_path = spec_file.relative_to(static_site_dir)
                    spec_path = str(rel_path)
                    # サブパス部分を安全に抽出
                    subpath = str(rel_path.parent)[len(repo_name):].lstrip("/")
                    title = repo_name + ("/" + subpath if subpath else "") + "/" + spec_file.stem
                    spec_data = None
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            spec_data = yaml.safe_load(content)
                            if spec_data and 'info' in spec_data and 'title' in spec_data['info']:
                                title = spec_data['info']['title']
                            api_specs[spec_path] = spec_data
                    except Exception as e:
                        logger.warning(f"{spec_file}からタイトル情報を抽出できませんでした: {e}")
                    swagger_link = f"swagger-ui.html?url={spec_path}"
                    redoc_link = f"redoc.html?url={spec_path}"
                    specs.append({
                        "title": title,
                        "repo": repo_name,
                        "path": spec_path,
                        "data": json.dumps(spec_data),
                        "swagger_link": swagger_link,
                        "redoc_link": redoc_link
                    })
            else:
                # 従来通りrepo直下のymlもサポート
                yml_files = list(repo_dir.glob("*.yml")) + list(repo_dir.glob("*.yaml"))
                for spec_file in yml_files:
                    repo_name = repo_dir.name
                    rel_path = spec_file.relative_to(static_site_dir)
                    spec_path = str(rel_path)
                    title = repo_name
                    spec_data = None
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            spec_data = yaml.safe_load(content)
                            if spec_data and 'info' in spec_data and 'title' in spec_data['info']:
                                title = spec_data['info']['title']
                            api_specs[spec_path] = spec_data
                    except Exception as e:
                        logger.warning(f"{spec_file}からタイトル情報を抽出できませんでした: {e}")
                    swagger_link = f"swagger-ui.html?url={spec_path}"
                    redoc_link = f"redoc.html?url={spec_path}"
                    specs.append({
                        "title": title,
                        "repo": repo_name,
                        "path": spec_path,
                        "data": json.dumps(spec_data),
                        "swagger_link": swagger_link,
                        "redoc_link": redoc_link
                    })
    redoc_template_path = TEMPLATES_DIR / "redoc.html"
    redoc_template_base64 = ""
    try:
        with open(redoc_template_path, 'r', encoding='utf-8') as f:
            redoc_template = f.read()
            redoc_template_base64 = base64.b64encode(redoc_template.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"ReDocテンプレート読み込み中にエラーが発生: {e}")
    swagger_ui_css = ""
    try:
        swagger_ui_css_url = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
        response = requests.get(swagger_ui_css_url)
        if response.status_code == 200:
            swagger_ui_css = response.text
    except Exception as e:
        logger.warning(f"Swagger UI CSSの読み込みに失敗しました: {e}")
    custom_css = ""
    try:
        css_path = CSS_DIR / "styles.css"
        with open(css_path, 'r', encoding='utf-8') as f:
            custom_css = f.read()
    except Exception as e:
        logger.warning(f"カスタムCSSの読み込みに失敗しました: {e}")
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
    rendered_html = template.render(
        specs=specs,
        redoc_template_base64=redoc_template_base64,
        swagger_ui_css=swagger_ui_css,
        custom_css=custom_css,
        **js_content
    )
    with open(static_site_dir / "index.html", "w", encoding='utf-8') as f:
        f.write(rendered_html)
    shutil.copy2(TEMPLATES_DIR / "swagger-ui.html", static_site_dir / "swagger-ui.html")
    shutil.copy2(TEMPLATES_DIR / "redoc.html", static_site_dir / "redoc.html")
    logger.info(f"静的サイトが {static_site_dir} に生成されました")
    return len(specs)

def generate_integrated_viewer():
    logger.info(f"統合ビューアの生成を開始します [出力先: {CONFIG['static_site_dir']}]")
    static_site_dir = Path(CONFIG["static_site_dir"])
    if not static_site_dir.exists():
        logger.warning(f"静的サイトディレクトリが存在しません: {static_site_dir}")
        static_site_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"静的サイトディレクトリを作成しました: {static_site_dir}")
    api_specs = {}
    total_size = 0
    spec_count = 0
    for repo_dir in static_site_dir.iterdir():
        if repo_dir.is_dir() and repo_dir.name != "static":
            spec_pattern = CONFIG["spec_path"]
            if "/" in spec_pattern:
                dir_part, file_pattern = spec_pattern.rsplit("/", 1)
            else:
                dir_part, file_pattern = "", spec_pattern
            search_dir = repo_dir / dir_part if dir_part else repo_dir
            if search_dir.exists() and search_dir.is_dir():
                yml_files = list(search_dir.rglob(file_pattern))
                for spec_file in yml_files:
                    repo_name = repo_dir.name
                    rel_path = spec_file.relative_to(static_site_dir)
                    spec_path = str(rel_path)
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            size = len(content)
                            logger.info(f"仕様書を読み込みました: {spec_file.name} ({size} バイト)")
                            total_size += size
                            spec_count += 1
                            spec_data = yaml.safe_load(content)
                            api_specs[spec_path] = spec_data
                    except Exception as e:
                        logger.error(f"仕様書の読み込み中にエラーが発生: {spec_file} - {e}")
            else:
                # 従来通りrepo直下のymlもサポート
                yml_files = list(repo_dir.glob("*.yml")) + list(repo_dir.glob("*.yaml"))
                for spec_file in yml_files:
                    repo_name = repo_dir.name
                    rel_path = spec_file.relative_to(static_site_dir)
                    spec_path = str(rel_path)
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            size = len(content)
                            logger.info(f"仕様書を読み込みました: {spec_file.name} ({size} バイト)")
                            total_size += size
                            spec_count += 1
                            spec_data = yaml.safe_load(content)
                            api_specs[spec_path] = spec_data
                    except Exception as e:
                        logger.error(f"仕様書の読み込み中にエラーが発生: {spec_file} - {e}")
    logger.info(f"合計 {spec_count} 件の仕様書を読み込みました (合計サイズ: {total_size} バイト)")
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        redoc_template_path = TEMPLATES_DIR / "redoc.html"
        with open(redoc_template_path, 'r', encoding='utf-8') as f:
            redoc_template = f.read()
            redoc_template_base64 = base64.b64encode(redoc_template.encode('utf-8')).decode('utf-8')
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
        try:
            css_path = CSS_DIR / "styles.css"
            with open(css_path, 'r', encoding='utf-8') as f:
                resource_contents["custom_css"] = f.read()
                logger.info(f"CSSファイルを読み込みました: custom_css ({len(resource_contents['custom_css'])} バイト)")
        except Exception as e:
            logger.error(f"CSSファイルの読み込み中にエラーが発生しました: {css_path}, エラー: {e}")
            resource_contents["custom_css"] = f"/* Error loading: {css_path}, {str(e)} */"
        template = env.get_template("api-spec-viewer.html")
        context = {
            "api_specs_json": json.dumps(api_specs),
            "redoc_template_base64": redoc_template_base64,
            **resource_contents
        }
        rendered_html = template.render(**context)
        viewer_file = static_site_dir / "api-spec-viewer.html"
        logger.info(f"統合ビューアを保存します: {viewer_file}")
        if not viewer_file.parent.exists():
            logger.warning(f"親ディレクトリが存在しません: {viewer_file.parent}")
            viewer_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"親ディレクトリを作成しました: {viewer_file.parent}")
        with open(viewer_file, "w", encoding='utf-8') as f:
            f.write(rendered_html)
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
