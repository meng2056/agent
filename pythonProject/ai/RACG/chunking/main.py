from pathlib import Path
from ai.RACG.chunking.config.log_confg import logger
from ai.RACG.chunking.utils import RepoWalker
from ai.RACG.chunking.chunker import ParserFactory
from ai.RACG.chunking.chunker import LanguageDetector
from ai.RACG.chunking.comment import enrich_code_with_comments
from ai.RACG.chunking.chunker import TokenAwareChunker
from langchain_core.documents import Document
from ai.RACG.chunking.utils import get_repo_name
# from ai.agent.ai_config.config import *


def racg_enrich_and_chunk(
        path: str | Path,
        save_enriched: bool
) -> list[Document]:
    input_path = Path(path)
    repo_name = get_repo_name(input_path)

    final_documents: list[Document] = []

    chunker_cache: dict[str, TokenAwareChunker] = {}

    logger.info(f"Start processing the path: {input_path}")

    # 1. Traverse the files
    for file_path in RepoWalker.recursive_walk(input_path):
        try:
            language = LanguageDetector.detect(str(file_path))
            if language == 'unknown':
                logger.debug(f"Skip unknown language files: {file_path}")
                continue

            source_code = RepoWalker.read_file_content(file_path)
            if not source_code:
                continue

            # ============ B. first parse  ============
            parser = ParserFactory.get_parser(language)
            if not parser:
                logger.warning(f"No parser was found. "
                               f"[{language}]: {file_path}")
                continue

            logger.info(f"parse file: {file_path.name} ({language})")
            first_parse = parser.parse(source_code)

            # ============ C. add comment (Enrichment) ============

            enriched_source_code = enrich_code_with_comments(
                source_code, first_parse, language
            )

            if save_enriched:
                debug_path = file_path.with_suffix(
                    f".enriched{file_path.suffix}"
                )
                debug_path.write_text(enriched_source_code, encoding='utf-8')
                logger.debug(f"Saved copy: {debug_path}")

            # ============ D. Re-Parsing ============

            re_parse = parser.parse(enriched_source_code)

            # ============ E. Verification ============
            # Verify that the structure of the ASTs is the same
            if not parser.verify_ast_equality(first_parse, re_parse):
                logger.warning(
                    f"AST structure mismatch after enrichment: {file_path}")
                continue  # Skip this file if verification fails

            # ============ F. (Chunking) ============
            if language not in chunker_cache:
                chunker_cache[language] = TokenAwareChunker(language)
            chunker = chunker_cache[language]

            file_metadata = {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "language": language,
                "repo_name": repo_name,
            }

            top_level_nodes = [n for n in re_parse
                               if n.parent_name is None]
            chunks = chunker.chunk_enriched_code(
                enriched_source_code, top_level_nodes, file_metadata
            )

            final_documents.extend(chunks)
            logger.info(f"Complete processing {file_path.name}: "
                        f"gen {len(chunks)} 个 Documents")

        except Exception as e:
            logger.error(
                f"Failed to process the file {file_path}: {e}", exc_info=True
            )
            continue

    logger.info(f"missons completed! A total of {len(final_documents)} "
                f"code snippets have been generated.")
    return final_documents
