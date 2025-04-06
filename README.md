# OpenAPI仕様書収集ツール

GitHub上の複数リポジトリに分散したOpenAPI仕様書を収集し、一元的に閲覧できる静的サイトを生成するツール

## 使用方法

```bash
# スクリプトを実行
python collect_openapi.py
```

実行すると以下の処理が行われます：

1. 指定された組織/ユーザーから対象のリポジトリを検索
2. 各リポジトリからOpenAPI仕様書を取得し、`static_site/`ディレクトリに静的サイトを生成
3. オフライン対応のSPAも同時に生成 (`static_site/offline-spa.html`)

生成された静的サイトは、`static_site/index.html`を開くことで閲覧できます。
また、`static_site/offline-spa.html`を開くことで、オフラインでも利用可能なシングルページアプリケーション版を利用できます。

## 閲覧方法

生成された静的サイトでは、以下の2つのビューアーを利用できます：

- Swagger UI: OpenAPI仕様書の対話的なドキュメントを表示
- ReDoc: 読みやすく整形されたドキュメントを表示

オフラインSPA版では以下の機能も利用できます：

- 全API横断検索
- レスポンシブデザイン
- オフライン対応（すべてのリソースを1ファイルに統合）

## 設定

`config.py`で以下の設定を変更できます：

```python
CONFIG = {
    # GitHubの組織名または所有者名
    "organization": "xxx-project",
    
    # 対象リポジトリのパターン
    "repo_pattern": "xxx-api",
    
    # 取得するリポジトリの上限
    "repo_limit": 100,
    
    # OpenAPI仕様書の相対パス
    "spec_path": "docs/openapi.yml",
    
    # 静的サイトの出力先ディレクトリ
    "static_site_dir": "static_site",
}
```

## コマンドライン引数

以下のコマンドライン引数が利用可能です：

- `clean`: 出力ディレクトリをクリーンアップ
- `spa`: オフラインSPAのみを生成

## ライセンス

MIT

## 貢献

プルリクエストは歓迎します。大きな変更を行う場合は、まず問題を報告してください。
