# OpenAPI仕様書収集・静的サイト生成ツール

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)


GitHub上の複数リポジトリに分散したOpenAPI仕様書を収集し、一元的に閲覧できる静的サイトを生成するツールです。

## 主な特徴
- spec_path（例: docs/*.yml, docs/paths/*.yml など）で任意のパターンのOpenAPI仕様書を収集可能
- 収集した仕様書を静的サイト（Swagger UI, ReDoc, 統合ビューア）として自動生成

## 使い方

```bash
# 仕様書の収集のみ
python openapispec_cli.py collect

# 収集済み仕様書から静的サイト生成のみ
python openapispec_cli.py build

# 収集＋静的サイト生成＋統合ビューア生成
python openapispec_cli.py all

# 統合ビューアのみ生成
python openapispec_cli.py viewer

# クリーンアップ
python openapispec_cli.py clean
```

## 設定例

`src/config.py` で以下のように設定します:

```python
CONFIG = {
    "organization": "xxx-project",
    "repo_pattern": "xxx-api",
    "repo_limit": 100,
    "spec_path": "docs/paths/*.yml",  # 任意のパターンに変更可能
    "static_site_dir": "static_site",
}
```

## 静的サイトの閲覧

- 生成された `static_site/index.html` をブラウザで開くと、全API仕様書を横断的に閲覧できます。
- `static_site/api-spec-viewer.html` はオフラインでも利用可能なスタンドアローンビューアです。

## ライセンス

This software is released under the [MIT License](LICENSE).
