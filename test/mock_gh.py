#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import base64
from pathlib import Path

class MockGitHub:
    """
    GitHubのAPIとghコマンドをシミュレートするモッククラス
    """
    def __init__(self, mock_data_dir="test/mock_data"):
        """
        初期化
        mock_data_dir: モックデータを格納するディレクトリ
        """
        self.mock_data_dir = Path(mock_data_dir)
        self.mock_data_dir.mkdir(exist_ok=True)
        
        # テスト用のリポジトリを作成
        self.create_mock_repositories()
    
    def create_mock_repositories(self):
        """
        テスト用のリポジトリ構造を作成
        """
        # テスト用のリポジトリ一覧
        repositories = [
            "xxx-api-1",
            "xxx-api-2",
            "xxx-api-3",
            "other-repo-1",
            "another-project"
        ]
        
        # 各リポジトリのディレクトリを作成
        for repo in repositories:
            repo_dir = self.mock_data_dir / repo
            repo_dir.mkdir(exist_ok=True)
            
            # xxx-apiパターンに一致するリポジトリにはOpenAPI仕様書を作成
            if "xxx-api" in repo:
                docs_dir = repo_dir / "docs"
                docs_dir.mkdir(exist_ok=True)
                
                # サンプルのOpenAPI仕様書を作成
                self.create_sample_openapi_spec(docs_dir / "openapi.yml", repo)
    
    def create_sample_openapi_spec(self, file_path, repo_name):
        """
        サンプルのOpenAPI仕様書を作成
        """
        openapi_content = f"""openapi: 3.0.0
info:
  title: {repo_name} API
  description: サンプルAPI仕様書
  version: 1.0.0
paths:
  /users:
    get:
      summary: ユーザー一覧を取得
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: integer
                    name:
                      type: string
  /users/{{id}}:
    get:
      summary: 特定のユーザーを取得
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
"""
        with open(file_path, 'w') as f:
            f.write(openapi_content)
    
    def list_repositories(self, org_name, limit=100):
        """
        リポジトリ一覧を取得するghコマンドのシミュレーション
        """
        repos = []
        for repo_dir in self.mock_data_dir.iterdir():
            if repo_dir.is_dir():
                repos.append({"name": repo_dir.name})
                if len(repos) >= limit:
                    break
        
        return json.dumps(repos)
    
    def get_file_content(self, org_name, repo_name, file_path):
        """
        ファイル内容を取得するghコマンドのシミュレーション
        """
        full_path = self.mock_data_dir / repo_name / file_path
        
        if not full_path.exists():
            return json.dumps({"message": "Not Found", "documentation_url": "https://docs.github.com/rest"})
        
        with open(full_path, 'r') as f:
            content = f.read()
        
        # Base64エンコードしてGitHub APIのレスポンスをシミュレート
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        return encoded

# モック版のghコマンド実行関数
def run_mock_gh_command(mock_gh, command):
    """
    ghコマンドをモックする関数
    """
    # リポジトリ一覧の取得
    if command[0:3] == ["gh", "repo", "list"]:
        org = command[3]
        limit = 100
        for i, arg in enumerate(command):
            if arg == "--limit" and i + 1 < len(command):
                limit = int(command[i + 1])
        
        return mock_gh.list_repositories(org, limit)
    
    # ファイル内容の取得
    elif command[0:3] == ["gh", "api", "/repos"]:
        path_parts = command[3].split('/')
        if len(path_parts) >= 5:  # /repos/{org}/{repo}/contents/{path}
            org = path_parts[2]
            repo = path_parts[3]
            file_path = '/'.join(path_parts[5:])
            
            return mock_gh.get_file_content(org, repo, file_path)
    
    return "{}"

# モックGitHubインスタンスの作成
def create_mock_environment():
    """
    テスト環境をセットアップする
    """
    return MockGitHub()

if __name__ == "__main__":
    # テスト用環境の作成
    mock_gh = create_mock_environment()
    print(f"モックリポジトリが {mock_gh.mock_data_dir} に作成されました。")