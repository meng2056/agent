import os
import nltk
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.tools import tool
from ai.agent.ai_config.config import gen_custom_embeddings
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from ai.agent.ai_config.config import gen_custom_reranker
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_core.documents import Document

os.environ["UNSTRUCTURED_DO_NOT_TRACK"] = "true"
ai_root = Path(__file__).parent.parent.parent
local_nltk_data_path = ai_root / "ai_config/resources/nltk_data"
nltk_data_path = str(local_nltk_data_path.resolve())
if nltk_data_path not in nltk.data.path:
    nltk.data.path.append(nltk_data_path)
os.environ["NLTK_DATA"] = nltk_data_path
VEC_DB_PATH = "/cadgit/git/agent_db/chroma_db"


def contain_chinese(jdg_str: str) -> bool:
    for char in jdg_str:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False


def gen_retrieve_rag_info(retriever, tools_name: list[str] = None):
    """
    Generate a tool for RAG retrieval custom SOP manual
    :param retriever: An instance of a retriever used to retrieve documents
    :param tools_name: An optional list, that may include all tools name
    """
    formatted_tool_names = ", ".join(tools_name) if tools_name else ""

    @tool
    def retrieve_rag_info(query_str: str) -> str:
        """
        Used to retrieve detailed information about the priciples, usage,
        configuration, troubleshooting and other aspects of a specific custom
        script or tool.

        **Function description:**
          This tools is specifically designed to query manuals or documents
          for custom scripts and tools stored in the SOP knowledge base. When
          users need to know related information of any specific tool
          developed by CAD team such as {all_tools}, LLM should use this tool
          to retrieve information from vector storage.

        **Application Scenarios**
        - Users inquire about the 'principle' and 'how does it work?' of a
          certain tool.
        - The user ask about the script: 'How to use it?',
          'Give me an example of how to use it?', "What the step of it"
        - The user asks 'How to configure' and 'what are the prameters' of a
          certain tool
        - Users encounter problems and ask, "This tool is reporting an error,
          how can I solve it?", "What are the common problems of the tool?"
        - Users need to obtain detailed technical documentation for a custom
          tool.

        :param query_str: This parameter need be a refinement of user
                   information, for example: The user asks: 'I heard there is a
                   tool called dff_x_check, can you introduce me the usage of
                   this tool? I want learn how to run this tool from terminal.'
                   the LLM should extract valid information and ensure the
                   retriever search the correct information, so the query_str
                   should be 'usage of dff_x_check'.
        :return: Retrieve relevant manual content from the SOP knowledge base.
           If no matching information is found, return 'No result found'
        """

        if contain_chinese(query_str):
            results = retriever.invoke(query_str)
            if not results:
                return "没有相关的中文搜索结果"
            response = "检索到以下中文信息:\n"
            for doc in results:
                response += doc.page_content
            return response

        else:
            results = retriever.invoke(query_str)
            if not results:
                return "No result found"

            response = ("retrieve following English information from the"
                        " SOP knowledge library:\n")

            for doc in results:
                response += doc.page_content
            return response
    retrieve_rag_info.__doc__ = retrieve_rag_info.__doc__.format(
        all_tools=formatted_tool_names
    )
    return retrieve_rag_info


def gen_retriever(srch_k: int, ):
    embed_method = gen_custom_embeddings(max_len=6144)
    vec_store = Chroma(
        persist_directory=VEC_DB_PATH,
        embedding_function=embed_method,
        collection_name="deg_sop"
    )

    vector_retriever = vec_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": srch_k, "fetch_k" : 10}
    )

    result = vec_store.get()
    documents = result["documents"]
    metadatas = result["metadatas"]

    bm25_docs = [Document(page_content=doc, metadata=meta)
                 for doc, meta in zip(documents, metadatas)]

    bm25_retriever = (BM25Retriever.from_documents(documents=bm25_docs, k=srch_k))

    ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.5, 0.5]
        )

    custom_reranker = gen_custom_reranker()

    reranker_compressor = CrossEncoderReranker(model=custom_reranker, top_n=3)

    final_retriever = ContextualCompressionRetriever(
        base_retriever=ensemble_retriever,
        base_compressor=reranker_compressor,
    )
    return final_retriever