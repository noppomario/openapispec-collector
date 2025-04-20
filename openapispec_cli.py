import sys
import logging
from src.gh_utils import get_api_repositories, fetch_openapi_specs
from src.site_generator import generate_static_site, generate_integrated_viewer
from src.cleaner import clean, clean_directories

logger = logging.getLogger('openapispec-collector')

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def print_usage():
    print("""
Usage: python openapispec_cli.py <command>

Commands:
  collect   API仕様書の収集のみ
  build     収集済み仕様書から静的サイト生成のみ
  all       収集＋静的サイト生成＋統合ビューア生成
  viewer    統合ビューアのみ生成
  clean     クリーンアップのみ
""")

def collect_specs():
    """
    API仕様書を収集し、収集件数とファイルリストを返す共通関数
    """
    static_site_dir = clean_directories()
    static_site_dir.mkdir(exist_ok=True)
    api_repos = get_api_repositories()
    if not api_repos:
        logger.warning("対象のリポジトリが見つかりませんでした")
        return 0, []
    successful_specs = 0
    all_files = []
    for repo in api_repos:
        try:
            output_files = fetch_openapi_specs(repo)
            if output_files:
                successful_specs += len(output_files)
                all_files.extend(output_files)
                logger.info(f"{repo}の仕様書を正常に取得しました: {output_files}")
        except Exception as e:
            logger.error(f"{repo}の処理中にエラーが発生しました: {e}")
    return successful_specs, all_files

def collect_only():
    logger.info("OpenAPI仕様書収集のみを実行します")
    successful_specs, _ = collect_specs()
    logger.info(f"{successful_specs}件の仕様書を収集しました")

def build_only():
    logger.info("静的サイト生成のみを実行します")
    specs_count = generate_static_site()
    logger.info(f"合計 {specs_count} 件の仕様書を使用して静的サイトを生成しました")

def all_process():
    logger.info("API仕様書収集＋静的サイト生成＋統合ビューア生成を実行します")
    successful_specs, _ = collect_specs()
    if successful_specs > 0:
        specs_count = generate_static_site()
        logger.info(f"合計 {specs_count} 件の仕様書を使用して静的サイトを生成しました")
        generate_integrated_viewer()
    else:
        logger.warning("有効な仕様書が1つも取得できなかったため、静的サイトは生成されませんでした")
    logger.info("処理が完了しました")

def main():
    if len(sys.argv) <= 1:
        print_usage()
        return
    command = sys.argv[1]
    if command == "collect":
        collect_only()
    elif command == "build":
        build_only()
    elif command == "all":
        all_process()
    elif command == "viewer":
        generate_integrated_viewer()
    elif command == "clean":
        clean()
    else:
        print_usage()

if __name__ == "__main__":
    main()
