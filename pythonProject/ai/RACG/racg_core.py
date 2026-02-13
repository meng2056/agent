from pathlib import Path
from typing import Optional
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from ai.RACG.chunking.config.setting import *
from ai.agent.ai_config.config import *
from langchain_chroma import Chroma
from langchain_core.documents import Document
from ai.RACG.chunking.main import racg_enrich_and_chunk
from langchain_community.retrievers import BM25Retriever

class RACG:
    def __init__(
            self,
            repo_path: str | Path,
            vectordb_path: str | Path = settings.VECTOR_DB_PATH,
            collection_name: str = settings.VECTOR_DB_COLLECTION_NAME,
            embed_max_tokens: int = settings.EMBED_MAX_TOKENS,
            search_k: int = 5,
            persist: bool = True,
    ):
        self.repo_path = repo_path
        self.vectordb_path = vectordb_path
        self.collection_name = collection_name
        self.embed_max_tokens = embed_max_tokens
        self.search_k = search_k
        self.persist = persist

        self.vectordb: Optional[Chroma] = None

    def chunk_and_enrich(self) -> list[Document]:
        docs = racg_enrich_and_chunk(
             path=self.repo_path,
             save_enriched=self.persist)
        return docs

    def doc2chromadb(self, docs: list[Document]):
        embed_method = gen_custom_embeddings(max_len=self.embed_max_tokens)
        self.vectordb = Chroma.from_documents(
            documents=docs,
            persist_directory=settings.VECTOR_DB_PATH,
            embedding=embed_method,
            collection_name=settings.VECTOR_DB_COLLECTION_NAME
            )

    @staticmethod
    def gen_retriever(
            vec_store,
            srch_k: int = 5):
        vector_retriever = vec_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": srch_k, "fetch_k": 10}
        )

        result = vec_store.get()
        documents = result["documents"]
        metadatas = result["metadatas"]

        bm25_docs = [Document(page_content=doc, metadata=meta)
                     for doc, meta in zip(documents, metadatas)]

        bm25_retriever = (
            BM25Retriever.from_documents(documents=bm25_docs, k=srch_k))

        # scored_retriever = ScoredEnsembleRetriever(
        #     retrievers=[bm25_retriever, vector_retriever],
        #     weights=[0.4, 0.6],
        #     # id_key="doc_id"
        # )
        # return scored_retriever
        ensemble_retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.5, 0.5]
        )

        custom_reranker =

        reranker_compressor = CrossEncoderReranker(model=custom_reranker,
                                                   top_n=3)

        final_retriever = ContextualCompressionRetriever(
            base_retriever=ensemble_retriever,
            base_compressor=reranker_compressor,
        )
        return final_retriever

    def code_retriever(self, doc2chromadb):
        code_retriever = self.gen_retriever(
            vec_store=doc2chromadb.vectordb,
        )
        return code_retriever

def main():
    racg = RACG(repo_path=r"D:\CODE\pythonProject\ai\agent\agent_core\graph_core.py")
    docs = racg.chunk_and_enrich()
    racg.doc2chromadb(docs)
    retriever = racg.code_retriever(racg)
    docs = retriever.invoke("what is the graph_core of the function?")
    print(docs)

if __name__ == "__main__":
    main()

