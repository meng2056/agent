from abc import ABC, abstractmethod
from typing import Optional
from tree_sitter import Language, Parser, Node
import tree_sitter_python
import tree_sitter_verilog
import os
from ai.RACG.chunking.config.setting import settings
from ai.RACG.chunking.config.log_confg import logger
from typing import Any
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from transformers import AutoTokenizer

tknzr_file = "/home/alanm/python_repo/ai/ai_config/resources/tokenizer_ivv"

class SemanticNode(BaseModel):
    name: str
    type: str
    start_line: int  # 0-based
    end_line: int
    start_byte: int
    end_byte: int
    source_code: str
    existing_comment: Optional[str] = None
    parent_name: Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.parent_name}.{self.name}"\
            if self.parent_name else self.name


# ============ Abstract  class ============
class AbstractParser(ABC):
    def __init__(self):
        self.language = self._load_language()
        self.parser = Parser(self.language)

    @abstractmethod
    def _load_language(self) -> Language:
        pass

    @abstractmethod
    def parse(self, source_code: str) -> list[SemanticNode]:
        pass

    def _get_node_name(self, node: Node, source_bytes: bytes) -> str:
        name_node = node.child_by_field_name("name")
        if name_node:
            return (source_bytes[name_node.start_byte: name_node.end_byte]
                    .decode("utf8"))
        return "unknown"

    @staticmethod
    def verify_ast_equality(
            first_parse: list[SemanticNode], re_parse: list[SemanticNode]
    ) -> bool:
        if len(first_parse) != len(re_parse):
            logger.debug(f"AST verification failed: Inconsistent number of "
                         f"nodes, {len(first_parse)} != {len(re_parse)}")
            return False

        for i, (first_node, re_node) in enumerate(zip(first_parse, re_parse)):
            if first_node.name != re_node.name:
                logger.debug(f"AST verification failed: "
                             f"The name of node {i} is inconsistent.,"
                             f"'{first_node.name}' != '{re_node.name}'")
                return False

            if first_node.type != re_node.type:
                logger.debug(f"AST verification failed: "
                             f"The type of node {i} is inconsistent., "
                             f"'{first_node.type}' != '{re_node.type}'")
                return False

            if first_node.parent_name != re_node.parent_name:
                logger.debug(f"AST verification failed:"
                             f" The parent_name of node {i} is inconsistent., "
                             f"'{first_node.parent_name}' != '{re_node.parent_name}'")
                return False

        logger.debug("AST verification successful")
        return True


# ============ Python Parser============
class PythonParser(AbstractParser):
    def _load_language(self) -> Language:
        return Language(tree_sitter_python.language())

    def parse(self, source_code: str) -> list[SemanticNode]:
        try:
            source_bytes = source_code.encode("utf8")
            tree = self.parser.parse(source_bytes)
            nodes = []

            def traverse(node: Node, parent_name: Optional[str] = None):
                current_name = None

                if node.type in settings.PYTHON_TARGET_NODES:
                    current_name = self._get_node_name(node, source_bytes)

                    doc_str = self._extract_docstring(node, source_bytes)

                    nodes.append(SemanticNode(
                        name=current_name,
                        type=node.type.replace("_definition", ""),
                        start_line=node.start_point.row,
                        end_line=node.end_point.row,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        source_code=source_bytes[node.start_byte:
                                                 node.end_byte].decode("utf8"),
                        existing_comment=doc_str,
                        parent_name=parent_name
                    ))

                for child in node.children:
                    traverse(child, current_name
                    if current_name else parent_name)

            traverse(tree.root_node)
            return nodes
        except Exception as e:
            logger.error(f"Python parse failed: {e}")
            return []
    def _extract_docstring(
            self, node: Node, source_bytes: bytes
    ) -> Optional[str]:
        body = node.child_by_field_name("body")
        if body and body.child_count > 0:
            first_child = body.children[0]
            if first_child.type == "expression_statement":
                if first_child.children[0].type == "string":
                    return source_bytes[first_child.start_byte:
                                        first_child.end_byte].decode("utf8")
        return None


# ============ Verilog Parser============

class VerilogParser(AbstractParser):
    def _load_language(self) -> Language:
        return Language(tree_sitter_verilog.language())

    def parse(self, source_code: str) -> list[SemanticNode]:
        try:
            source_bytes = source_code.encode("utf8")
            tree = self.parser.parse(source_bytes)
            nodes = []

            def traverse(node: Node, parent_name: Optional[str] = None):
                current_name = None

                if node.type in settings.VERILOG_TARGET_NODES:
                    current_name = self._get_node_name(node, source_bytes)

                    nodes.append(SemanticNode(
                        name=current_name,
                        type=node.type.replace("_declaration", ""),
                        start_line=node.start_point.row,
                        end_line=node.end_point.row,
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                        source_code=source_bytes[node.start_byte:
                                                 node.end_byte].decode("utf8"),
                        existing_comment=None,
                        parent_name=parent_name
                    ))

                for child in node.children:
                    traverse(child, current_name
                     if current_name else parent_name)

            traverse(tree.root_node)
            return nodes
        except Exception as e:
            logger.error(f"Verilog parse failed: {e}")
            return []


class LanguageDetector:

    @staticmethod
    def detect(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1]
        if ext == '.py':
            return 'python'
        elif ext in {'.v', '.sv'}:
            return 'verilog'
        return 'unknown'


class ParserFactory:
    _parsers = {
        'python': PythonParser,
        'verilog': VerilogParser
    }

    @classmethod
    def get_parser(cls, language: str) -> Optional[AbstractParser]:
        parser_cls = cls._parsers.get(language)
        if parser_cls:
            return parser_cls()
        return None


class CodeSegment(BaseModel):
    content: str
    type: str
    start_line: int
    end_line: int
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============ core chunker ============

class TokenAwareChunker:

    def __init__(self, language: str):
        self.language = language
        self.max_tokens = settings.CHUNK_MAX_TOKENS
        self.tokenizer = AutoTokenizer.from_pretrained('gpt2')

        self.target_node_types = (settings.PYTHON_TARGET_NODES
                                  | settings.VERILOG_TARGET_NODES)

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def chunk_enriched_code(self,
                            source_code: str,
                            nodes: list[SemanticNode],
                            file_metadata: dict[str, Any]) -> list[Document]:
        """
        Main process: Linearization -> Greedy merging -> Documentation
        """
        segments = self._linearize_source(source_code, nodes, file_metadata)

        chunks_data = self._greedy_merge(segments)

        documents = []
        for i, (chunk_text, chunk_meta) in enumerate(chunks_data):
            final_metadata = {**file_metadata, **chunk_meta}
            final_metadata['chunk_id'] = i
            documents.append(Document(
                page_content=chunk_text,
                metadata=final_metadata
            ))
        return documents

    def _linearize_source(
            self,
            source_code: str,
            nodes: list[SemanticNode],
            file_metadata: dict[str, Any],
    ) -> list[CodeSegment]:
        if not nodes:
            token_cnt = self._count_tokens(source_code)
            if token_cnt > 1000:
                logger.warning(
                    "No semantic nodes found, entire file treated as glue, "
                    "token_count=%d",
                    token_cnt
                )
            return [CodeSegment(
                content=source_code,
                type="glue",
                token_count=token_cnt,
                start_line=0,
                end_line=source_code.count("\n"),
                metadata={
                    "start_line": 0,
                    "end_lin": source_code.count("\n"),
                    "token_count": token_cnt}
            )]

        sorted_nodes = sorted(nodes, key=lambda n: n.start_byte)
        segments: list[CodeSegment] = []
        cursor_byte = 0
        current_line = 0
        source_bytes = source_code.encode("utf-8")
        source_lines = source_code.splitlines(keepends=True)

        pending_glue: str = ""
        glue_start_line: int = 0

        for i, node in enumerate(sorted_nodes):
            if node.start_byte > cursor_byte:
                gap_bytes = source_bytes[cursor_byte:node.start_byte]
                gap_text = gap_bytes.decode("utf-8", errors="replace")
                if gap_text:
                    # pending_glue += gap_text
                    # if not pending_glue:
                    #     glue_start_line = current_line
                    # current_line += gap_text.count("\n")
                    if not pending_glue:
                        glue_start_line = self._get_line_number(source_code,cursor_byte)
                        pending_glue += gap_text
                        current_line += gap_text.count("\n")

            node_bytes = source_bytes[node.start_byte:node.end_byte]
            node_text = node_bytes.decode("utf-8", errors="replace")
            language = file_metadata.get('language', '')
            if language:
                formatted_node_text = (f"```{language}\n"
                                       f"#node segment:\n"
                                       f"{node_text}\n")
            else:
                formatted_node_text = node_text

            node_token_cnt = self._count_tokens(node_text)

            glue_token_cnt = self._count_tokens(pending_glue)
            if glue_token_cnt > 1000:
                logger.warning(
                    "Large preceding glue (token_count=%d) bound to node '%s' "
                    "(type=%s, lines ~%d-%d)",
                    glue_token_cnt, node.full_name, node.type,
                    glue_start_line, node.start_line
                )

            combined_content = pending_glue + formatted_node_text
            combined_token_cnt = glue_token_cnt + node_token_cnt
            seg_start_line = glue_start_line if pending_glue else (node.
                                                                   start_line)

            segments.append(CodeSegment(
                content=combined_content,
                type="node",
                token_count=combined_token_cnt,
                start_line=seg_start_line,
                end_line=node.end_line,
                metadata={
                    "node_name": node.name,
                    "node_type": node.type,
                    "start_line": seg_start_line,
                    "end_line": node.end_line,
                    "parent_name": node.parent_name,
                    "token_count": combined_token_cnt,
                    # "has_preceding_glue": bool(pending_glue),
                    # "preceding_glue_lines": pending_glue.count("\n") + (
                    #     1 if pending_glue else 0),
                    # "preceding_glue_tokens": glue_token_cnt,
                }
            ))

            pending_glue = ""
            cursor_byte = node.end_byte
            current_line = node.end_line + 1

        if cursor_byte < len(source_bytes):
            tail_bytes = source_bytes[cursor_byte:]
            tail_text = tail_bytes.decode("utf-8", errors="replace")
            if tail_text:
                tail_token_cnt = self._count_tokens(tail_text)
                if tail_token_cnt > 1000:
                    logger.warning(
                        "Large trailing glue segment (unbound),"
                        "token_count=%d, starting from line %d",
                        tail_token_cnt, current_line
                    )
                segments.append(CodeSegment(
                    content=tail_text,
                    type="glue",
                    token_count=tail_token_cnt,
                    start_line=current_line,
                    end_line=current_line+tail_text.count("\n"),
                    metadata={
                        "start_line": current_line,
                        "end_line": current_line + tail_text.count("\n"),
                        "token_count": tail_token_cnt}
                ))
        return segments

    def _get_line_number(self, source_code: str,
                                   byte_offset: int) -> int:
        """根据字节偏移量计算行号 (0-based)"""
        # 获取到偏移量为止的所有文本
        text_up_to_offset = source_code.encode("utf-8")[:byte_offset].decode(
            "utf-8", errors="replace")
        # 返回行数 (0-based)
        return text_up_to_offset.count("\n")

    def _greedy_merge(self, segments: list[CodeSegment]) -> \
            list[tuple[str, dict[str, Any]]]:

        chunks = []
        current_batch = []
        current_tokens = 0

        for seg in segments:

            is_overflow = (current_tokens + seg.token_count) > self.max_tokens

            is_protected_node = (
                    seg.type == "node" and
                    seg.metadata.get("node_type") in self.target_node_types
            )

            if is_overflow:
                if current_batch:
                    chunks.append(self._commit_batch(current_batch))
                    current_batch = []
                    current_tokens = 0

                if is_protected_node:
                    logger.warning(
                        f"A very large semantic node has been detected. "
                        f"[{seg.metadata.get('node_name')}] "
                        f"({seg.token_count} tokens)，Trigger the protection "
                        f"mechanism and skip the segmentation.。")
                    chunks.append(self._commit_batch([seg]))

                elif seg.token_count > self.max_tokens:
                    logger.info(f"Force the segmentation of non-semantic nodes"
                                f" (Lines {seg.start_line}-{seg.end_line})")
                    sub_chunks = self._force_split(seg)
                    chunks.extend(sub_chunks)

                else:
                    current_batch.append(seg)
                    current_tokens += seg.token_count

            else:
                current_batch.append(seg)
                current_tokens += seg.token_count

        if current_batch:
            chunks.append(self._commit_batch(current_batch))

        return chunks

    def _commit_batch(self, batch: list[CodeSegment]) -> tuple[str, dict]:
        text = "".join([s.content for s in batch])

        total_tokens = sum([s.token_count for s in batch])
        start_line = batch[0].start_line
        end_line = batch[-1].end_line

        contained_nodes = []
        # contained_nodes = {}
        primary_node = None

        for s in batch:
            if s.type == "node":
                node_info = f"{s.metadata.get('node_type')}:{s.metadata.get('node_name')}"
                contained_nodes.append(node_info)
                if primary_node is None:
                    primary_node = s.metadata.get('node_name')
        contained_nodes_str = ", ".join(contained_nodes)

        # for s in batch:
        #     if s.type == "node":
        #         node_type = s.metadata.get("node_type")
        #         node_name = s.metadata.get("node_name")
        #         if node_type and node_name:
        #             contained_nodes[node_type] = node_name
        #         if primary_node is None:
        #             primary_node = node_name
        #
        # contained_nodes_str = ", ".join(
        #     [f"{node_type}:{node_name}" for node_type, node_name in contained_nodes.items()]
        # )

        meta = {
            "chunk_start_line": start_line,
            "chunk_end_line": end_line,
            "line_count": end_line - start_line,
            "token_count": total_tokens,
            "contained_nodes": contained_nodes_str,
            "primary_node_name": primary_node or "global_context",
            "is_oversized": total_tokens > self.max_tokens
        }

        return text, meta

    def _force_split(self, segment: CodeSegment) -> list[tuple[str, dict]]:

        input_ids = self.tokenizer.encode(segment.content,
                                          add_special_tokens=False)
        total_ids = len(input_ids)
        chunk_size = self.max_tokens
        overlap = 50

        sub_chunks = []
        for i in range(0, total_ids, chunk_size - overlap):
            chunk_ids = input_ids[i: i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_ids)

            meta = {
                "chunk_start_line": segment.start_line,
                "chunk_end_line": segment.end_line,
                "token_count": len(chunk_ids),
                "is_forced_split": True,
                "split_index": i
            }
            sub_chunks.append((chunk_text, meta))

        return sub_chunks