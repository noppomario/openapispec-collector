/**
 * OpenAPI仕様書ビューア メインアプリケーション
 */

// グローバル変数の定義
window.apiSpecs = typeof apiSpecs !== 'undefined' ? apiSpecs : {}; // テンプレートから渡されたデータを使用
window.redocTemplateBase64 = typeof redocTemplateBase64 !== 'undefined' ? redocTemplateBase64 : ''; // テンプレートから渡されたデータを使用

// CDNが利用できない場合のフォールバックリンク
const CDN_LINKS = {
    "swagger_ui_js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    "swagger_ui_css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    "bootstrap_css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
    "redoc_js": "https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"
};

// アプリケーションの状態管理
const appState = {
    currentSpecPath: null,
    currentViewType: null,
    currentSpecTitle: null,
    searchResults: [],
    searchQuery: ''
};

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', function() {
    // データの存在確認とロギング
    console.log('API仕様データ:', window.apiSpecs);
    console.log('API数:', Object.keys(window.apiSpecs).length);
    
    // 必要に応じて外部リソースを読み込み
    if (!window.SwaggerUIBundle) {
        loadExternalResourceIfNeeded('script', 'swagger-ui-js', CDN_LINKS.swagger_ui_js);
    }
    
    // イベントハンドラを設定
    document.getElementById('back-to-list').addEventListener('click', function() {
        showWelcomeScreen();
    });
    
    // 検索入力欄のイベントリスナー
    const searchInput = document.getElementById('global-search');
    let debounceTimeout;
    
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        // デバウンス処理（入力が一定時間停止するまで検索を実行しない）
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            if (query.length >= 2) {
                appState.searchQuery = query;
                appState.searchResults = searchAllSpecs(query, window.apiSpecs);
                updateSearchResults(appState.searchResults, appState);
                // 検索結果タブに切り替え
                document.getElementById('tab-search').click();
            } else if (query.length === 0) {
                // 検索クエリが空の場合はAPI一覧に戻る
                document.getElementById('tab-apis').click();
            }
        }, 300);
    });
    
    // タブ切り替え
    document.getElementById('tab-apis').addEventListener('click', function() {
        document.getElementById('tab-apis').classList.add('active');
        document.getElementById('tab-search').classList.remove('active');
        document.getElementById('api-list-container').classList.add('active');
        document.getElementById('search-results-container').classList.remove('active');
    });
    
    document.getElementById('tab-search').addEventListener('click', function() {
        document.getElementById('tab-search').classList.add('active');
        document.getElementById('tab-apis').classList.remove('active');
        document.getElementById('search-results-container').classList.add('active');
        document.getElementById('api-list-container').classList.remove('active');
        
        // 検索結果がなければ再検索
        if (appState.searchResults.length === 0 && appState.searchQuery) {
            appState.searchResults = searchAllSpecs(appState.searchQuery, window.apiSpecs);
            updateSearchResults(appState.searchResults, appState);
        }
    });
    
    // API一覧の初期表示を確実に行う
    document.getElementById('api-list-container').classList.add('active');
    document.getElementById('search-results-container').classList.remove('active');
    
    // API一覧を初期化
    initializeApiList();

    // 表示方法ドロップダウンのイベントを追加
    const viewerModeSelect = document.getElementById('viewer-mode-select');
    if (viewerModeSelect) {
        // 初期値
        appState.currentViewType = viewerModeSelect.value;
        viewerModeSelect.addEventListener('change', function(e) {
            appState.currentViewType = viewerModeSelect.value;
            // すでにAPIが表示されていれば切り替え
            if (appState.currentSpecPath) {
                showSpec(appState.currentSpecPath, appState.currentViewType, appState.currentSpecTitle, window.apiSpecs);
            }
        });
    }

    // トグルボタンのイベント設定
    const toggleSwagger = document.getElementById('toggle-swagger');
    const toggleRedoc = document.getElementById('toggle-redoc');
    function updateViewerToggleUI() {
        if (appState.currentViewType === 'redoc') {
            toggleSwagger.classList.remove('active');
            toggleRedoc.classList.add('active');
        } else {
            toggleSwagger.classList.add('active');
            toggleRedoc.classList.remove('active');
        }
    }
    if (toggleSwagger && toggleRedoc) {
        // 初期状態
        appState.currentViewType = 'swagger';
        updateViewerToggleUI();
        toggleSwagger.addEventListener('click', function() {
            if (appState.currentViewType !== 'swagger') {
                appState.currentViewType = 'swagger';
                updateViewerToggleUI();
                if (appState.currentSpecPath) {
                    showSpec(appState.currentSpecPath, 'swagger', appState.currentSpecTitle, window.apiSpecs);
                }
            }
        });
        toggleRedoc.addEventListener('click', function() {
            if (appState.currentViewType !== 'redoc') {
                appState.currentViewType = 'redoc';
                updateViewerToggleUI();
                if (appState.currentSpecPath) {
                    showSpec(appState.currentSpecPath, 'redoc', appState.currentSpecTitle, window.apiSpecs);
                }
            }
        });
    }
});

// APIリストを初期化
function initializeApiList() {
    const apiList = document.getElementById('api-list');
    apiList.innerHTML = '';

    // 1. リポジトリごとにAPI仕様書をグループ化
    const repoMap = {};
    for (const [specPath, specData] of Object.entries(window.apiSpecs)) {
        const repoName = specPath.split('/')[0];
        if (!repoMap[repoName]) repoMap[repoName] = [];
        repoMap[repoName].push({ specPath, specData });
    }

    // 2. 各リポジトリごとに親要素＋子リストを作成
    Object.keys(repoMap).sort().forEach(repoName => {
        // リポジトリ見出し
        const repoSection = document.createElement('div');
        repoSection.className = 'repo-section';

        // 見出し＋トグル
        const header = document.createElement('div');
        header.className = 'repo-header';
        header.style.cursor = 'pointer';
        header.innerHTML = `<span class="repo-toggle">▼</span> <span class="repo-title">${repoName}</span>`;
        repoSection.appendChild(header);

        // 子リスト
        const childList = document.createElement('div');
        childList.className = 'repo-api-list';

        repoMap[repoName].forEach(({ specPath, specData }) => {
            const title = specData?.info?.title || specPath;
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item api-list-item';
            listItem.style.cursor = 'pointer';

            const heading = document.createElement('h5');
            heading.className = 'mb-2';
            heading.textContent = title;
            listItem.appendChild(heading);

            // 説明文
            if (specData?.info?.description) {
                const description = document.createElement('p');
                description.className = 'api-description mb-2';
                description.textContent = specData.info.description.substring(0, 150) +
                    (specData.info.description.length > 150 ? '...' : '');
                listItem.appendChild(description);
            }

            // API名クリックで現在の表示方法で開く
            listItem.addEventListener('click', () => {
                const viewerMode = appState.currentViewType || 'swagger';
                showSpec(specPath, viewerMode, title, window.apiSpecs);
            });

            childList.appendChild(listItem);
        });

        repoSection.appendChild(childList);
        apiList.appendChild(repoSection);

        // トグル動作
        header.addEventListener('click', () => {
            const isOpen = childList.style.display !== 'none';
            childList.style.display = isOpen ? 'none' : '';
            header.querySelector('.repo-toggle').textContent = isOpen ? '▶' : '▼';
        });
    });
}

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

// 関数をグローバルに公開
window.showSpec = showSpec;
window.showWelcomeScreen = showWelcomeScreen;
window.searchAllSpecs = searchAllSpecs;
window.appState = appState;
