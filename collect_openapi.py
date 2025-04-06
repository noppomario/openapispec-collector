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

def generate_standalone_spa():
    """
    すべてのリソースを1つのHTMLファイルにバンドルしたオフラインSPAを生成
    """
    output_dir = Path(CONFIG["output_dir"])
    static_site_dir = Path(CONFIG["static_site_dir"])
    
    # 静的サイトディレクトリが確実に存在するようにする
    static_site_dir.mkdir(exist_ok=True, parents=True)
    
    logger.info(f"オフラインSPAの生成を開始します [出力先: {static_site_dir}]")
    
    # OpenAPI仕様書をJSON形式に変換して1つのJavaScriptオブジェクトに集約
    api_specs = {}
    total_spec_size = 0  # 仕様書の合計サイズを追跡
    
    try:
        # 出力ディレクトリが存在するか確認
        if not output_dir.exists():
            logger.warning(f"出力ディレクトリが存在しません: {output_dir}")
            output_dir.mkdir(exist_ok=True, parents=True)
            logger.info(f"出力ディレクトリを作成しました: {output_dir}")
        
        for repo_dir in output_dir.iterdir():
            if repo_dir.is_dir():
                yml_files = list(repo_dir.glob("*.yml"))
                yaml_files = list(repo_dir.glob("*.yaml"))
                spec_files = yml_files + yaml_files
                
                for spec_file in spec_files:
                    repo_name = repo_dir.name
                    try:
                        with open(spec_file, 'r', encoding='utf-8') as f:
                            spec_data = yaml.safe_load(f)
                            # 仕様書データをJSONに変換して保存
                            api_specs[f"{repo_name}/{spec_file.name}"] = spec_data
                            
                            # 仕様書のサイズを追跡
                            spec_size = os.path.getsize(spec_file)
                            total_spec_size += spec_size
                            logger.info(f"仕様書を読み込みました: {spec_file.name} ({spec_size} バイト)")
                    except Exception as e:
                        logger.error(f"{spec_file}の読み込み中にエラーが発生しました: {e}")
        
        # 読み込んだ仕様書の数とサイズを記録
        logger.info(f"合計 {len(api_specs)} 件の仕様書を読み込みました (合計サイズ: {total_spec_size} バイト)")
        
        if not api_specs:
            logger.warning("有効な仕様書が1つも読み込めませんでした")
            return None
        
        # 外部リソースのURLとそのコンテンツを取得
        external_resources = {
            "swagger_ui_css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            "swagger_ui_js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
            "redoc_js": "https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"
        }
        
        resource_contents = {}
        import requests
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
        
        # ReDocとSwaggerUIの分離テンプレートを作成
        redoc_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ReDoc - OpenAPI Viewer</title>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }
        #redoc-container {
            height: 100%;
        }
    </style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
    <script>
        // 親ウィンドウからのメッセージを受信
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'RENDER_SPEC') {
                try {
                    // すでにRedocが初期化されている場合は破棄
                    const container = document.getElementById('redoc-container');
                    while (container.firstChild) {
                        container.removeChild(container.firstChild);
                    }
                    
                    // 新しいRedocインスタンスを初期化
                    Redoc.init(
                        event.data.spec,
                        {
                            scrollYOffset: 0,
                            hideDownloadButton: true,
                            nativeScrollbars: true,
                            hideLoading: false,
                            suppressWarnings: true
                        },
                        container
                    );
                    // 親フレームにレンダリング完了を通知
                    window.parent.postMessage({ type: 'RENDER_COMPLETE' }, '*');
                } catch (error) {
                    console.error('ReDoc初期化エラー:', error);
                    document.getElementById('redoc-container').innerHTML = `
                        <div style="padding: 20px; color: red;">
                            <h3>エラーが発生しました</h3>
                            <p>${error.message || '不明なエラー'}</p>
                        </div>
                    `;
                    // 親フレームにエラーを通知
                    window.parent.postMessage({ type: 'RENDER_ERROR', error: error.message }, '*');
                }
            }
        });
        
        // 初期化完了を親に通知
        window.parent.postMessage({ type: 'FRAME_READY' }, '*');
    </script>
</body>
</html>
"""
        
        # オフラインSPA用のHTML生成
        spa_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OpenAPI Specification Collection - Offline SPA</title>
    <style>
        /* Bootstrap CSS (インライン) */
        """ + (resource_contents.get("bootstrap_css", "/* Bootstrap CSS not available - using CDN */") or "") + """
    </style>
    <style>
        /* Swagger UI CSS (インライン) */
        """ + (resource_contents.get("swagger_ui_css", "/* Swagger UI CSS not available - using CDN */") or "") + """
    </style>
    <style>
        /* カスタムスタイル */
        body, html {
            height: 100%;
            margin: 0;
            font-family: Arial, sans-serif;
        }
        .app-container {
            display: flex;
            height: 100%;
        }
        .sidebar {
            width: 300px;
            background-color: #f8f9fa;
            padding: 15px;
            overflow-y: auto;
            border-right: 1px solid #dee2e6;
            max-height: 100vh;
        }
        .content {
            flex-grow: 1;
            padding: 0;
            overflow-y: auto;
            position: relative;
            display: flex;
            flex-direction: column;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
            flex-grow: 1;
        }
        .hidden {
            display: none !important;
        }
        #viewer-container {
            height: 100%;
            width: 100%;
            display: flex;
            flex-direction: column;
        }
        #swagger-ui {
            height: 100%;
            overflow-y: auto;
        }
        .loading-indicator {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            z-index: 100;
        }
        .viewer-header {
            padding: 10px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .back-button {
            padding: 5px 10px;
            background-color: #6c757d;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .spec-title {
            margin: 0 10px;
            font-size: 1.2em;
            flex-grow: 1;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <h2>OpenAPI仕様書</h2>
            <div class="list-group mt-4" id="api-list">
                <!-- APIリストはJavaScriptで動的に生成 -->
            </div>
        </div>
        <div class="content">
            <div id="welcome-screen">
                <div class="container mt-5 text-center">
                    <h1>OpenAPI仕様書コレクション</h1>
                    <p>左側のリストから表示したい仕様書を選択してください</p>
                </div>
            </div>
            <div id="viewer-container" class="hidden">
                <div class="viewer-header">
                    <button class="back-button" id="back-to-list">戻る</button>
                    <div class="spec-title" id="current-spec-title">仕様書タイトル</div>
                    <div class="viewer-type" id="current-viewer-type">Viewer: -</div>
                </div>
                <!-- SwaggerUIコンテナ -->
                <div id="swagger-ui" class="hidden"></div>
                <!-- ReDocはiframeで表示 -->
                <iframe id="redoc-frame" class="hidden" title="ReDoc Viewer" sandbox="allow-scripts allow-same-origin">
                </iframe>
            </div>
        </div>
    </div>
    
    <!-- Base64エンコードされたReDocテンプレート -->
    <script>
        const redocTemplateBase64 = 'REDOC_TEMPLATE_BASE64_PLACEHOLDER';
    </script>

    <!-- API仕様データ (インライン) -->
    <script>
        // APIデータをJavaScriptオブジェクトとして埋め込み
        const apiSpecs = JSON_API_SPECS_PLACEHOLDER;
    </script>

    <!-- Swagger UI Bundle (インライン) -->
    <script>
        """ + (resource_contents.get("swagger_ui_js", "/* Swagger UI JS not available - using CDN */") or "") + """
    </script>

    <!-- アプリケーションロジック -->
    <script>
        // CDNが利用できない場合のフォールバックリンク
        const CDN_LINKS = {
            "swagger_ui_js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            "swagger_ui_css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        };
        
        // アプリケーションの状態管理
        const appState = {
            currentSpecPath: null,
            currentViewType: null,
            currentSpecTitle: null
        };
        
        // Base64文字列をデコードする関数
        function decodeBase64(base64) {
            try {
                return atob(base64);
            } catch (e) {
                console.error('Base64デコードエラー:', e);
                return '';
            }
        }
        
        // 不足しているリソースを動的に読み込む
        function loadExternalResourceIfNeeded(type, id, url) {
            const resourceExists = type === 'script' 
                ? (typeof SwaggerUIBundle !== 'undefined')
                : document.querySelector(`style[data-id="${id}"]`);
                
            if (!resourceExists) {
                console.log(`Loading external ${type}: ${url}`);
                if (type === 'script') {
                    const script = document.createElement('script');
                    script.src = url;
                    script.id = id;
                    document.body.appendChild(script);
                } else if (type === 'style') {
                    const link = document.createElement('link');
                    link.rel = 'stylesheet';
                    link.href = url;
                    link.setAttribute('data-id', id);
                    document.head.appendChild(link);
                }
            }
        }
        
        // ロード中表示を作成
        function createLoadingIndicator(message) {
            const indicator = document.createElement('div');
            indicator.className = 'loading-indicator';
            indicator.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">${message || 'Loading...'}</p>
            `;
            return indicator;
        }
        
        // アプリケーション初期化
        document.addEventListener('DOMContentLoaded', function() {
            // 必要に応じて外部リソースを読み込み
            if (!window.SwaggerUIBundle) {
                loadExternalResourceIfNeeded('script', 'swagger-ui-js', CDN_LINKS.swagger_ui_js);
            }
            
            // イベントハンドラを設定
            document.getElementById('back-to-list').addEventListener('click', function() {
                showWelcomeScreen();
            });
            
            // APIリストを生成
            const apiList = document.getElementById('api-list');
            
            for (const [specPath, specData] of Object.entries(apiSpecs)) {
                const repoName = specPath.split('/')[0];
                const title = specData?.info?.title || repoName;
                
                const listItem = document.createElement('div');
                listItem.className = 'list-group-item';
                
                const heading = document.createElement('h5');
                heading.textContent = title;
                listItem.appendChild(heading);
                
                const repoInfo = document.createElement('p');
                repoInfo.textContent = `Repository: ${repoName}`;
                listItem.appendChild(repoInfo);
                
                const buttonGroup = document.createElement('div');
                
                const swaggerButton = document.createElement('button');
                swaggerButton.className = 'btn btn-primary btn-sm me-2';
                swaggerButton.textContent = 'Swagger UI';
                swaggerButton.addEventListener('click', () => showSpec(specPath, 'swagger', title));
                buttonGroup.appendChild(swaggerButton);
                
                const redocButton = document.createElement('button');
                redocButton.className = 'btn btn-success btn-sm';
                redocButton.textContent = 'ReDoc';
                redocButton.addEventListener('click', () => showSpec(specPath, 'redoc', title));
                buttonGroup.appendChild(redocButton);
                
                listItem.appendChild(buttonGroup);
                apiList.appendChild(listItem);
            }
        });
        
        // ウェルカム画面の表示
        function showWelcomeScreen() {
            const welcomeScreen = document.getElementById('welcome-screen');
            const viewerContainer = document.getElementById('viewer-container');
            const swaggerUI = document.getElementById('swagger-ui');
            const redocFrame = document.getElementById('redoc-frame');
            
            welcomeScreen.classList.remove('hidden');
            viewerContainer.classList.add('hidden');
            swaggerUI.classList.add('hidden');
            redocFrame.classList.add('hidden');
            
            // 状態をリセット
            appState.currentSpecPath = null;
            appState.currentViewType = null;
        }
        
        // 仕様書表示
        function showSpec(specPath, viewerType, title) {
            // 状態を更新
            appState.currentSpecPath = specPath;
            appState.currentViewType = viewerType;
            appState.currentSpecTitle = title;
            
            // UI要素の参照を取得
            const welcomeScreen = document.getElementById('welcome-screen');
            const viewerContainer = document.getElementById('viewer-container');
            const swaggerUI = document.getElementById('swagger-ui');
            const redocFrame = document.getElementById('redoc-frame');
            const currentSpecTitle = document.getElementById('current-spec-title');
            const currentViewerType = document.getElementById('current-viewer-type');
            
            // タイトルと表示タイプを更新
            currentSpecTitle.textContent = title || 'OpenAPI仕様書';
            currentViewerType.textContent = `Viewer: ${viewerType === 'swagger' ? 'Swagger UI' : 'ReDoc'}`;
            
            // 基本的なUI表示制御
            welcomeScreen.classList.add('hidden');
            viewerContainer.classList.remove('hidden');
            
            // 仕様書データを取得
            const spec = apiSpecs[specPath];
            
            if (viewerType === 'swagger') {
                // SwaggerUIを表示、ReDocを非表示
                swaggerUI.classList.remove('hidden');
                redocFrame.classList.add('hidden');
                
                // ローディングインジケータを表示
                const loadingIndicator = createLoadingIndicator('Swagger UIを読み込み中...');
                swaggerUI.innerHTML = '';
                swaggerUI.appendChild(loadingIndicator);
                
                // SwaggerUIが読み込まれるまで待機
                const checkSwaggerUI = setInterval(() => {
                    if (window.SwaggerUIBundle) {
                        clearInterval(checkSwaggerUI);
                        
                        try {
                            // SwaggerUIを初期化
                            while (swaggerUI.firstChild) {
                                swaggerUI.removeChild(swaggerUI.firstChild);
                            }
                            
                            SwaggerUIBundle({
                                spec: spec,
                                dom_id: '#swagger-ui',
                                deepLinking: true,
                                presets: [SwaggerUIBundle.presets.apis],
                                layout: "BaseLayout",
                                docExpansion: 'list',
                                filter: true
                            });
                        } catch (error) {
                            console.error('Swagger UI初期化エラー:', error);
                            swaggerUI.innerHTML = `<div class="alert alert-danger m-3">
                                <h4>Swagger UIの初期化中にエラーが発生しました</h4>
                                <p>${error.message || '不明なエラー'}</p>
                            </div>`;
                        }
                    } else {
                        // 最大5秒待機
                        window.swaggerRetryCount = (window.swaggerRetryCount || 0) + 1;
                        
                        if (window.swaggerRetryCount > 50) {
                            clearInterval(checkSwaggerUI);
                            console.error('Swagger UI JS読み込み失敗');
                            swaggerUI.innerHTML = '<div class="alert alert-danger m-3">Swagger UI JavaScriptライブラリの読み込みに失敗しました。</div>';
                            loadExternalResourceIfNeeded('script', 'swagger-ui-js-retry', CDN_LINKS.swagger_ui_js);
                        }
                    }
                }, 100);
            } else if (viewerType === 'redoc') {
                // ReDocを表示、SwaggerUIを非表示
                swaggerUI.classList.add('hidden');
                redocFrame.classList.remove('hidden');
                
                // iframeのコンテンツをReDocテンプレートに設定
                const redocHtml = decodeBase64(redocTemplateBase64);
                const iframe = document.getElementById('redoc-frame');
                
                // iframeを準備
                iframe.onload = function() {
                    const message = {
                        type: 'RENDER_SPEC',
                        spec: spec
                    };
                    // iframeがロードされたらメッセージを送信
                    setTimeout(() => {
                        iframe.contentWindow.postMessage(message, '*');
                    }, 100);
                };
                
                // srcdocにReDocテンプレートを設定（Base64デコード）
                // この方法はiframeを再利用するため、DOMノード削除エラーを回避
                const blob = new Blob([redocHtml], {type: 'text/html'});
                const url = URL.createObjectURL(blob);
                iframe.src = url;
                
                // メッセージリスナーの設定
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'RENDER_ERROR') {
                        console.error('ReDocレンダリングエラー:', event.data.error);
                    } else if (event.data && event.data.type === 'RENDER_COMPLETE') {
                        console.log('ReDocレンダリング完了');
                    }
                });
            }
        }
    </script>
</body>
</html>
"""
        
        # Base64エンコードしてReDocテンプレートをHTMLに埋め込み
        import base64
        try:
            redoc_template_base64 = base64.b64encode(redoc_template.encode('utf-8')).decode('utf-8')
            spa_html = spa_html.replace("REDOC_TEMPLATE_BASE64_PLACEHOLDER", redoc_template_base64)
        except Exception as e:
            logger.error(f"ReDocテンプレートのエンコード中にエラーが発生しました: {e}")
            redoc_template_base64 = ''
            spa_html = spa_html.replace("REDOC_TEMPLATE_BASE64_PLACEHOLDER", redoc_template_base64)
        
        # API仕様データをJSON形式でHTMLに埋め込み
        import json
        try:
            # JSON変換
            logger.info("API仕様データをJSONに変換しています...")
            json_data = json.dumps(api_specs)
            logger.info(f"JSON変換完了 (サイズ: {len(json_data)} バイト)")
            
            # HTMLへの埋め込み
            spa_html = spa_html.replace("JSON_API_SPECS_PLACEHOLDER", json_data)
            logger.info(f"HTML生成完了 (サイズ: {len(spa_html)} バイト)")
            
            # 出力先パスの確認
            spa_file = static_site_dir / "offline-spa.html"
            logger.info(f"SPAファイルを保存します: {spa_file}")
            
            # HTMLファイルに書き込む前にディレクトリの存在を確認
            if not spa_file.parent.exists():
                logger.warning(f"親ディレクトリが存在しません: {spa_file.parent}")
                spa_file.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"親ディレクトリを作成しました: {spa_file.parent}")
            
            # ファイルに保存
            with open(spa_file, "w", encoding='utf-8') as f:
                f.write(spa_html)
            
            # ファイルサイズの確認
            file_size = os.path.getsize(spa_file)
            logger.info(f"SPAファイルを保存しました: {spa_file} (サイズ: {file_size} バイト)")
            
            return spa_file
            
        except MemoryError as e:
            logger.error(f"メモリ不足エラー: {e}")
            logger.error("API仕様データが大きすぎる可能性があります。データサイズを減らして再試行してください。")
            return None
            
        except Exception as e:
            import traceback
            logger.error(f"SPAファイル生成中にエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            return None
            
    except Exception as e:
        import traceback
        logger.error(f"オフラインSPAの生成中にエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        return None

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
        elif command == "spa":
            generate_standalone_spa()
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

        # 1ファイルにまとめる
        generate_standalone_spa()
    else:
        logger.warning("有効な仕様書が1つも取得できなかったため、静的サイトは生成されませんでした")
    
    logger.info("処理が完了しました")

if __name__ == "__main__":
    main()