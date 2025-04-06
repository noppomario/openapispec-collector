/**
 * OpenAPI仕様書ビューア機能
 */

// SwaggerUIまたはReDocで仕様書を表示
function showSpec(specPath, viewerType, title, apiSpecs) {
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

// 検索結果の表示を更新
function updateSearchResults(results, appState) {
    const container = document.getElementById('search-results');
    const apiListTab = document.getElementById('tab-apis');
    const searchTab = document.getElementById('tab-search');
    const apiListContainer = document.getElementById('api-list-container');
    const searchResultsContainer = document.getElementById('search-results-container');
    
    // 検索結果コンテナをクリア
    container.innerHTML = '';
    
    // 検索結果がない場合のメッセージ表示
    if (results.length === 0) {
        container.innerHTML = '<div class="alert alert-info mt-3">検索結果がありません。別のキーワードをお試しください。</div>';
        return;
    }
    
    // 検索タブをアクティブに
    apiListTab.classList.remove('active');
    searchTab.classList.add('active');
    apiListContainer.classList.remove('active');
    searchResultsContainer.classList.add('active');
    
    // 検索結果の概要を表示
    const resultSummary = document.createElement('div');
    resultSummary.className = 'alert alert-primary mt-2 mb-3';
    resultSummary.innerHTML = `「<strong>${appState.searchQuery}</strong>」の検索結果: <strong>${results.length}</strong> 件のAPI仕様書がマッチしました`;
    container.appendChild(resultSummary);
    
    // 検索結果を表示
    results.forEach((result, index) => {
        const resultItem = document.createElement('div');
        resultItem.className = 'search-result-item';
        resultItem.setAttribute('data-spec-path', result.specPath);
        
        // タイトルと説明
        let titleHtml = highlightKeyword(result.title, appState.searchQuery);
        let descriptionHtml = '';
        
        if (result.description) {
            descriptionHtml = `<div class="result-description">${highlightKeyword(result.description, appState.searchQuery)}</div>`;
        }
        
        // APIバッジ
        const apiBadge = `<span class="badge bg-info me-2">${result.repo}</span>`;
        
        // マッチ項目の表示
        let matchesHtml = '';
        if (result.matches.length > 0) {
            // REST APIエンドポイントを最初に表示
            const pathMatches = result.matches.filter(m => m.path.includes('paths'));
            const otherMatches = result.matches.filter(m => !m.path.includes('paths'));
            
            // パスマッチの表示（REST APIエンドポイント）
            if (pathMatches.length > 0) {
                matchesHtml += '<div class="path-matches mt-2">';
                matchesHtml += '<h6 class="result-section-title">エンドポイント:</h6>';
                
                pathMatches.forEach(match => {
                    const methodBadge = match.method ? 
                        `<span class="badge ${getMethodBadgeClass(match.method)}">${match.method}</span>` : '';
                    
                    matchesHtml += `
                        <div class="result-endpoint">
                            ${methodBadge}
                            <code>${highlightKeyword(match.value, appState.searchQuery)}</code>
                        </div>
                        <div class="result-snippet">
                            ${highlightKeyword(match.snippet, appState.searchQuery)}
                        </div>
                    `;
                    
                    // オペレーション情報があれば表示
                    if (match.operations && match.operations.length > 0) {
                        match.operations.forEach(op => {
                            const opSummary = op.summary || op.operationId || '';
                            if (opSummary) {
                                matchesHtml += `
                                    <div class="operation-item">
                                        <span class="badge ${getMethodBadgeClass(op.method)}">${op.method}</span>
                                        <small>${highlightKeyword(opSummary, appState.searchQuery)}</small>
                                    </div>
                                `;
                            }
                        });
                    }
                });
                matchesHtml += '</div>';
            }
            
            // その他のマッチ
            if (otherMatches.length > 0) {
                matchesHtml += '<div class="other-matches mt-2">';
                
                // スキーママッチ
                const schemaMatches = otherMatches.filter(m => m.path.includes('components.schemas'));
                if (schemaMatches.length > 0) {
                    matchesHtml += '<h6 class="result-section-title">スキーマ:</h6>';
                    schemaMatches.forEach(match => {
                        matchesHtml += `
                            <div class="result-schema">
                                <small class="result-path">${formatPath(match.path)}:</small>
                                <div class="result-snippet">${highlightKeyword(match.snippet, appState.searchQuery)}</div>
                            </div>
                        `;
                    });
                }
                
                // その他のコンテンツマッチ
                const contentMatches = otherMatches.filter(m => 
                    !m.path.includes('components.schemas') && 
                    m.path !== 'info.description' &&
                    m.path !== 'info.version');
                
                if (contentMatches.length > 0) {
                    matchesHtml += '<h6 class="result-section-title">その他のコンテンツ:</h6>';
                    contentMatches.slice(0, 5).forEach(match => {
                        matchesHtml += `
                            <div class="result-content">
                                <small class="result-path">${formatPath(match.path)}:</small>
                                <div class="result-snippet">${highlightKeyword(match.snippet, appState.searchQuery)}</div>
                            </div>
                        `;
                    });
                    
                    // 表示しきれないマッチがある場合
                    if (contentMatches.length > 5) {
                        matchesHtml += `<div class="more-matches">他 ${contentMatches.length - 5} 件のマッチ...</div>`;
                    }
                }
                
                matchesHtml += '</div>';
            }
        }
        
        // 結果アイテムのHTML構築
        resultItem.innerHTML = `
            <div class="result-header">
                <div class="result-title">
                    ${apiBadge} ${titleHtml}
                </div>
                ${descriptionHtml}
            </div>
            ${matchesHtml}
            <div class="result-meta mt-2">
                <span>合計 ${result.totalMatches} 箇所がマッチ</span>
                <div>
                    <button class="btn btn-sm btn-outline-primary view-swagger">Swagger UI</button>
                    <button class="btn btn-sm btn-outline-success view-redoc">ReDoc</button>
                </div>
            </div>
        `;
        
        // SwaggerUIボタンイベント
        resultItem.querySelector('.view-swagger').addEventListener('click', (e) => {
            e.stopPropagation();
            window.showSpec(result.specPath, 'swagger', result.title, window.apiSpecs);
        });
        
        // ReDocボタンイベント
        resultItem.querySelector('.view-redoc').addEventListener('click', (e) => {
            e.stopPropagation();
            window.showSpec(result.specPath, 'redoc', result.title, window.apiSpecs);
        });
        
        // 項目クリックでSwaggerUI表示
        resultItem.addEventListener('click', () => {
            window.showSpec(result.specPath, 'swagger', result.title, window.apiSpecs);
        });
        
        container.appendChild(resultItem);
    });
    
    // スタイルを追加
    addSearchResultStyles();
}

// HTTPメソッドに応じたバッジクラスを取得
function getMethodBadgeClass(method) {
    switch (method.toUpperCase()) {
        case 'GET': return 'bg-success';
        case 'POST': return 'bg-primary';
        case 'PUT': return 'bg-warning text-dark';
        case 'DELETE': return 'bg-danger';
        case 'PATCH': return 'bg-info text-dark';
        default: return 'bg-secondary';
    }
}

// パス表示を整形
function formatPath(path) {
    // 長すぎるパスは省略
    if (path.length > 40) {
        const parts = path.split('.');
        if (parts.length > 4) {
            // 先頭と末尾の部分を保持
            return parts.slice(0, 2).join('.') + '...' + parts.slice(-2).join('.');
        }
    }
    return path;
}

// テキスト内のキーワードをハイライト
function highlightKeyword(text, keyword) {
    if (!keyword || !text) return text;
    const regex = new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return text.replace(regex, match => `<span class="highlight">${match}</span>`);
}

// 検索結果のスタイルを動的に追加
function addSearchResultStyles() {
    // 既存のスタイルがあれば追加しない
    if (document.getElementById('search-result-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'search-result-styles';
    style.textContent = `
        .search-result-item {
            padding: 12px;
            margin-bottom: 15px;
            background-color: #fff;
            border: 1px solid #dee2e6;
            border-left: 4px solid #007bff;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .search-result-item:hover {
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            background-color: #f8f9fa;
        }
        .result-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
        }
        .result-description {
            color: #666;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .result-section-title {
            font-size: 12px;
            margin: 8px 0 5px 0;
            color: #495057;
            font-weight: bold;
        }
        .result-endpoint {
            margin-bottom: 2px;
            display: flex;
            align-items: center;
        }
        .result-endpoint code {
            margin-left: 5px;
            font-size: 13px;
            color: #333;
            word-break: break-all;
        }
        .result-snippet {
            font-size: 12px;
            color: #666;
            margin: 3px 0 8px 0;
            padding-left: 10px;
            border-left: 2px solid #eee;
            white-space: normal;
            word-break: break-word;
        }
        .result-path {
            color: #6c757d;
            font-size: 11px;
            display: block;
            margin-bottom: 2px;
        }
        .result-schema, .result-content {
            margin-bottom: 8px;
        }
        .operation-item {
            padding-left: 10px;
            margin-bottom: 5px;
            font-size: 12px;
            display: flex;
            align-items: center;
        }
        .operation-item .badge {
            margin-right: 5px;
            font-size: 10px;
            min-width: 45px;
            text-align: center;
        }
        .more-matches {
            font-size: 12px;
            color: #6c757d;
            font-style: italic;
            margin-top: 5px;
        }
    `;
    document.head.appendChild(style);
}
