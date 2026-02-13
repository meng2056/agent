import os
from pathlib import Path
from typing import Generator, Union
from ai.RACG.chunking.config.setting import settings
from ai.RACG.chunking.config.log_confg import logger


class RepoWalker:
    @staticmethod
    def recursive_walk(path: Union[str, Path]) -> Generator[Path, None, None]:

        base_path = Path(path)

        if base_path.is_file():
            if base_path.suffix in settings.ALLOWED_EXTENSIONS:
                yield base_path
            else:
                logger.warning(f"The file type is not on the whitelist, "
                               f"so it has been skipped.: {base_path}")
            return

        if not base_path.exists():
            logger.error(f"The path does not exist.: {base_path}")
            return

        for root, _, files in os.walk(base_path):
            for file in files:
                file_path = Path(root) / file

                if file_path.suffix in settings.ALLOWED_EXTENSIONS:
                    yield file_path

    @staticmethod
    def read_file_content(file_path: Path) -> str:
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"read file content error: {file_path}: {str(e)}")
            return ""


def get_repo_name(path: Path) -> str:
    try:
        if path.is_file():
            return path.parent.name
        return path.name
    except Exception as e:
        logger.warning(f"Failed to get repository name for path {path}: {e}")
        return "unknown"
