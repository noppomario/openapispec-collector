# -*- coding: utf-8 -*-

# 設定
CONFIG = {
    # GitHubの組織名または所有者名
    "organization": "xxx-project",
    
    # 対象リポジトリのパターン
    "repo_pattern": "xxx-api",
    
    # 取得するリポジトリの上限
    "repo_limit": 100,
    
    # OpenAPI仕様書の相対パス
    "spec_path": "docs/paths/*.yml",
    
    # 静的サイトの出力先ディレクトリ
    "static_site_dir": "static_site",
}