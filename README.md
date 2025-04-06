# OpenAPI仕様書収集ツール

GitHub上の複数リポジトリからOpenAPI仕様書を抽出し、静的サイトを生成するためのツールです。

## 概要

このツールは以下の機能を提供します：

1. GitHub上の指定された組織/ユーザーのリポジトリから特定のパターン（例：「xxx-api」）に一致するリポジトリを検索
2. 各リポジトリの特定パス（デフォルト：`docs/openapi.yml`）からOpenAPI仕様書を抽出
3. 抽出した仕様書を基に、SwaggerUIとReDocによる閲覧が可能な静的サイトを生成

## 必要要件

- Python 3.8以上
- GitHub CLI（`gh`コマンド）がインストールされ、認証済みであること

## インストール

```bash
# リポジトリのクローン
git clone https://github.com/noppomario/openapispec-collector.git
cd openapispec-collector

# 仮想環境の作成とアクティベーション
python -m venv .venv
source .venv/bin/activate  # Windowsの場合は .venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

## 設定

`config.py` ファイルを編集して、以下の設定を行います：

```python
CONFIG = {
    # GitHubの組織名または所有者名
    "organization": "your-organization",
    
    # 対象リポジトリのパターン
    "repo_pattern": "api",
    
    # OpenAPI仕様書の相対パス
    "spec_path": "docs/openapi.yml",
    
    # その他の設定...
}
```

## 使用方法

```bash
# スクリプトを実行
python collect_openapi.py
```

実行すると以下の処理が行われます：

1. 指定された組織/ユーザーから対象のリポジトリを検索
2. 各リポジトリからOpenAPI仕様書を取得し、`output/`ディレクトリに保存
3. 静的サイトを`static_site/`ディレクトリに生成

生成された静的サイトは、`static_site/index.html`を開くことで閲覧できます。

## テスト

このプロジェクトにはテスト環境が含まれています。テストを実行するには：

```bash
# テスト実行
python -m test.test_collect_openapi
```

テスト環境では、GitHubリポジトリへの実際のアクセスをシミュレートするモックが使用されます。テスト結果は`test/output/`と`test/static_site/`ディレクトリに出力されます。

## ライセンス

MIT

## 貢献

プルリクエストは歓迎します。大きな変更を行う場合は、まず問題を報告してください。
