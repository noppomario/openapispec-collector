/**
 * OpenAPI仕様書検索機能
 */

// 全API横断検索機能
function searchAllSpecs(query, apiSpecs) {
    if (!query || query.trim().length < 2) {
        return [];
    }
    
    const results = [];
    const searchQuery = query.toLowerCase().trim();
    
    // 検索クエリを単語に分割
    const queryWords = searchQuery.split(/\s+/).filter(word => word.length >= 2);
    
    // インジケータの表示
    showSearchIndicator();
    
    // すべてのAPI仕様書を検索
    for (const [specPath, specData] of Object.entries(apiSpecs)) {
        const repoName = specPath.split('/')[0];
        const title = specData?.info?.title || repoName;
        const description = specData?.info?.description || '';
        const version = specData?.info?.version || '';
        
        let score = 0;
        let matchItems = [];
        
        // タイトル、説明文、バージョンの一致をチェック
        const titleMatch = title.toLowerCase().includes(searchQuery);
        if (titleMatch) score += 100;
        
        if (description && description.toLowerCase().includes(searchQuery)) {
            score += 50;
            matchItems.push({
                path: 'info.description',
                value: description,
                snippet: highlightSnippet(getSnippet(description, searchQuery), searchQuery)
            });
        }
        
        if (version && version.toLowerCase().includes(searchQuery)) {
            score += 30;
            matchItems.push({
                path: 'info.version',
                value: version,
                snippet: `バージョン: ${version}`
            });
        }
        
        // エンドポイント(paths)の特別な検索処理
        if (specData.paths) {
            for (const [path, pathObj] of Object.entries(specData.paths)) {
                // パスが検索クエリを含む場合
                if (path.toLowerCase().includes(searchQuery)) {
                    score += 80;
                    let operations = [];
                    
                    // 利用可能なHTTPメソッドを収集
                    for (const [method, operation] of Object.entries(pathObj)) {
                        if (['get', 'post', 'put', 'delete', 'patch'].includes(method)) {
                            operations.push({
                                method: method.toUpperCase(),
                                summary: operation.summary || '',
                                operationId: operation.operationId || ''
                            });
                        }
                    }
                    
                    matchItems.push({
                        path: `paths.${path}`,
                        value: path,
                        snippet: `エンドポイント: ${path}`,
                        operations: operations
                    });
                }
                
                // 各HTTPメソッドの詳細情報を検索
                for (const [method, operation] of Object.entries(pathObj)) {
                    if (!['get', 'post', 'put', 'delete', 'patch'].includes(method)) continue;
                    
                    const methodUpper = method.toUpperCase();
                    let matched = false;
                    
                    // サマリーの検索
                    if (operation.summary && operation.summary.toLowerCase().includes(searchQuery)) {
                        score += 60;
                        matched = true;
                    }
                    
                    // operationIdの検索
                    if (operation.operationId && operation.operationId.toLowerCase().includes(searchQuery)) {
                        score += 70;
                        matched = true;
                    }
                    
                    // タグの検索
                    if (operation.tags && operation.tags.some(tag => tag.toLowerCase().includes(searchQuery))) {
                        score += 50;
                        matched = true;
                    }
                    
                    // 説明文の検索
                    if (operation.description && operation.description.toLowerCase().includes(searchQuery)) {
                        score += 40;
                        matched = true;
                    }
                    
                    if (matched) {
                        matchItems.push({
                            path: `paths.${path}.${method}`,
                            value: `${methodUpper} ${path}`,
                            snippet: highlightSnippet(operation.summary || operation.operationId || `${methodUpper} 操作`, searchQuery),
                            method: methodUpper
                        });
                    }
                }
            }
        }
        
        // スキーマ定義の検索処理
        if (specData.components && specData.components.schemas) {
            for (const [schemaName, schema] of Object.entries(specData.components.schemas)) {
                // スキーマ名の一致
                if (schemaName.toLowerCase().includes(searchQuery)) {
                    score += 60;
                    matchItems.push({
                        path: `components.schemas.${schemaName}`,
                        value: schemaName,
                        snippet: `スキーマ: ${schemaName}`,
                        schemaType: schema.type || 'object'
                    });
                }
                
                // スキーマ説明の一致
                if (schema.description && schema.description.toLowerCase().includes(searchQuery)) {
                    score += 40;
                    matchItems.push({
                        path: `components.schemas.${schemaName}.description`,
                        value: schema.description,
                        snippet: highlightSnippet(`${schemaName}: ${getSnippet(schema.description, searchQuery)}`, searchQuery)
                    });
                }
                
                // スキーマのプロパティ検索
                if (schema.properties) {
                    for (const [propName, propDef] of Object.entries(schema.properties)) {
                        // プロパティ名の一致
                        if (propName.toLowerCase().includes(searchQuery)) {
                            score += 50;
                            matchItems.push({
                                path: `components.schemas.${schemaName}.properties.${propName}`,
                                value: propName,
                                snippet: `${schemaName}.${propName}: ${propDef.type || 'any'}`
                            });
                        }
                        
                        // プロパティの説明一致
                        if (propDef.description && propDef.description.toLowerCase().includes(searchQuery)) {
                            score += 30;
                            matchItems.push({
                                path: `components.schemas.${schemaName}.properties.${propName}.description`,
                                value: propDef.description,
                                snippet: highlightSnippet(`${schemaName}.${propName}: ${getSnippet(propDef.description, searchQuery)}`, searchQuery)
                            });
                        }
                    }
                }
            }
        }
        
        // より一般的なテキスト検索のために仕様書をフラット化
        const flattenedMatches = flattenSpec(specData, searchQuery);
        matchItems = [...matchItems, ...flattenedMatches];
        
        // 複数単語の検索で単語ごとのスコアを加算
        if (queryWords.length > 1) {
            queryWords.forEach(word => {
                if (title.toLowerCase().includes(word)) score += 20;
                if (description && description.toLowerCase().includes(word)) score += 10;
                
                // パスやメソッドの一致も評価
                if (matchItems.some(item => 
                    item.path.includes('paths') && item.value.toLowerCase().includes(word))) {
                    score += 15;
                }
            });
        }
        
        // 重複を除去し上位のマッチを保持
        const uniqueMatches = [];
        const seenPaths = new Set();
        
        for (const match of matchItems) {
            if (!seenPaths.has(match.path)) {
                seenPaths.add(match.path);
                uniqueMatches.push(match);
            }
        }
        
        // 最低スコアまたはマッチがある場合に結果に追加
        if (score > 0 || uniqueMatches.length > 0) {
            results.push({
                specPath: specPath,
                title: title,
                repo: repoName,
                description: description?.substring(0, 150) + (description?.length > 150 ? '...' : ''),
                matches: uniqueMatches.slice(0, 15), // 上位15件に制限
                totalMatches: uniqueMatches.length,
                titleMatch: titleMatch,
                queryScore: score
            });
        }
    }
    
    // インジケータの非表示
    hideSearchIndicator();
    
    // スコア順にソート
    results.sort((a, b) => b.queryScore - a.queryScore);
    
    return results;
}

// 検索インジケータの表示
function showSearchIndicator() {
    let indicator = document.getElementById('search-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'search-indicator';
        indicator.className = 'search-indicator';
        indicator.innerHTML = `
            <div class="spinner-border spinner-border-sm text-primary" role="status">
                <span class="visually-hidden">検索中...</span>
            </div>
            <span class="ms-2">検索中...</span>
        `;
        document.querySelector('.search-container').appendChild(indicator);
    }
    indicator.style.display = 'flex';
}

// 検索インジケータの非表示
function hideSearchIndicator() {
    const indicator = document.getElementById('search-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

// オブジェクトをフラット化して検索するヘルパー関数
function flattenSpec(obj, query, path = '', maxDepth = 5, currentDepth = 0) {
    let items = [];
    
    if (typeof obj !== 'object' || obj === null || currentDepth >= maxDepth) {
        return items;
    }
    
    for (const [key, value] of Object.entries(obj)) {
        // 特定のノイズの多いプロパティをスキップ
        if (['example', 'examples', 'enum'].includes(key)) continue;
        
        const currentPath = path ? `${path}.${key}` : key;
        
        // 特定のコンテキストを優先
        const isHighPriorityContext = currentPath.includes('paths') || 
                                     currentPath.includes('components.schemas') ||
                                     currentPath.includes('info');
        
        if (typeof value === 'object' && value !== null) {
            // 再帰的にオブジェクトを探索
            items = [...items, ...flattenSpec(value, query, currentPath, maxDepth, currentDepth + 1)];
        } else if (typeof value === 'string') {
            const stringValue = value.toLowerCase();
            if (stringValue.includes(query.toLowerCase())) {
                items.push({
                    path: currentPath,
                    value: value,
                    snippet: highlightSnippet(getSnippet(value, query), query),
                    priority: isHighPriorityContext ? 2 : 1
                });
            }
        } else if (typeof value === 'number' || typeof value === 'boolean') {
            const stringValue = String(value).toLowerCase();
            if (stringValue === query.toLowerCase()) {
                items.push({
                    path: currentPath,
                    value: String(value),
                    snippet: String(value),
                    priority: isHighPriorityContext ? 2 : 1
                });
            }
        }
    }
    
    // 優先度でソート
    items.sort((a, b) => b.priority - a.priority);
    
    return items;
}

// スニペットのハイライト処理を改善
function highlightSnippet(text, query) {
    if (!text || !query) return text;
    
    const words = query.toLowerCase().split(/\s+/).filter(w => w.length > 0);
    let result = text;
    
    words.forEach(word => {
        const regex = new RegExp(`(${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        result = result.replace(regex, '<mark>$1</mark>');
    });
    
    return result;
}

// スニペット生成処理を改善
function getSnippet(text, query) {
    if (!text) return '';
    
    const maxLength = 150;
    const words = query.toLowerCase().split(/\s+/).filter(w => w.length > 0);
    let bestSnippet = '';
    let bestScore = -1;
    
    // 各検索語に対してベストなスニペットを探す
    words.forEach(word => {
        const regex = new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
        const matchIndex = text.toLowerCase().search(regex);
        
        if (matchIndex >= 0) {
            const start = Math.max(0, matchIndex - 40);
            const end = Math.min(text.length, matchIndex + word.length + 40);
            const snippet = text.substring(start, end);
            const score = words.filter(w => snippet.toLowerCase().includes(w)).length;
            
            if (score > bestScore) {
                bestScore = score;
                bestSnippet = snippet;
            }
        }
    });
    
    if (bestSnippet) {
        // スニペットの前後に省略記号を追加
        const needsPrefix = bestSnippet !== text.substring(0, bestSnippet.length);
        const needsSuffix = bestSnippet !== text.substring(text.length - bestSnippet.length);
        
        return (needsPrefix ? '...' : '') + bestSnippet + (needsSuffix ? '...' : '');
    }
    
    // マッチしない場合は先頭部分を表示
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}
