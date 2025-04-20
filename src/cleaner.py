import shutil
import logging
from pathlib import Path
from src.config import CONFIG

logger = logging.getLogger('openapispec-collector')

def clean_directories():
    """
    出力ディレクトリと静的サイトディレクトリをクリーンアップする共通機能
    """
    static_site_dir = Path(CONFIG["static_site_dir"])
    if static_site_dir.exists():
        logger.info(f"静的サイトディレクトリを削除: {static_site_dir}")
        shutil.rmtree(static_site_dir)
    return static_site_dir

def clean():
    """
    出力ディレクトリと静的サイトディレクトリをクリーンアップする
    """
    logger.info("クリーンアップを実行します")
    clean_directories()
    logger.info("クリーンアップが完了しました")
