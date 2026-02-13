from langchain_openai import ChatOpenAI
from openai import base_url
from pydantic import SecretStr
from pathlib import Path
# from ai.ai_config.custom_embedding import CustomEmbeddings
from transformers import AutoTokenizer
import asyncio
# from ai.ai_config.custom_reranker import CustomReranker
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
BASE_URL = "http://t-llmserver.ai.cdtp.com/v1/"

QWQ_235B_NAME = "test-Qwen3-235B-GPTQ-Int8"
QWQ_235B_KEY = SecretStr("test_Qwen3_235B_GPTQ_Int8_RTAwMTk1NjYmdGVzdF9Rd2Vu"
                         "M18yMzVCX0dQVFFfSW50OCYyMDI1LzcvMjQ=")
DS_QWQ_32B_NAME = "DeepSeek-R1-Still-Qwen-32B"
DS_QWQ_32B_KEY = SecretStr("DeepSeek_R1_Still_Qwen_32B_RTAwMTk1NjYmRGVlc"
                           "FNlZWtfUjFfU3RpbGxfUXdlbl8zMkImMjAyNS80LzI5")

QWQ_32B_NAME = "QWQ-32B"
QWQ_32B_KEY = SecretStr("QWQ_32B_RTAwMTk1NjYmUVdRXzMyQiYyMDI1LzQvMjc=")

EMBEDDING_URL = "http://t-llmserver.ai.cdtp.com/v1/embeddings"
EMBEDDING_API_KEY = "test_bge_m3_RTAwMTk1NjYmdGVzdF9iZ2VfbTMmMjAyNS81LzIz"
EMBEDDING_MODEL_NAME = "test-bge-m3"

RERANKER_API_URL = "http://t-llmserver.ai.cdtp.com/rerank"
RERANKER_API_KEY = SecretStr("test_bge_reranker_v2_m3_RTAwMTk1NjYmdGVzdF9iZ2V"
                             "fcmVyYW5rZXJfdjJfbTMmMjAyNS8xMC8xNQ==")
RERANKER_MODEL_NAME = "test-bge-reranker-v2-m3"

NORMAL_URL = "http://llmserver.ai.cxmt.com/v1/"
QWQ_CODER_NAME = "Qwen3-Coder-480B-fp8"
QWQ_CODER_KEY = SecretStr("Qwen3_Coder_480B_fp8_EDA_RTAwMTk1NjYmUXdlbj"
                          "NfQ29kZXJfNDgwQl9mcDgmMjAyNS8xMC8xNQ==")


def gen_llm_deepseek_32b(
        temp: float = 0.1,
        tokens: int = 32768,
        streaming: bool = False,
        thk_en: bool = True,
        callbacks: list = None
) -> ChatOpenAI:
    llm = ChatOpenAI(
        api_key=DS_QWQ_32B_KEY,
        base_url=BASE_URL,
        model=DS_QWQ_32B_NAME,
        streaming=streaming,
        temperature=temp,
        max_tokens=tokens,
        extra_body={
            "enable_thinking": thk_en
        },
        callbacks=callbacks
    )
    return llm


def gen_llm_qwq_32b(
        temp: float = 0.1,
        tokens: int = 32768,
        streaming: bool = False,
        thk_en: bool = True,
        callbacks: list = None
) -> ChatOpenAI:
    llm = ChatOpenAI(
        api_key=QWQ_32B_KEY,
        base_url=BASE_URL,
        model=QWQ_32B_NAME,
        streaming=streaming,
        temperature=temp,
        max_tokens=tokens,
        extra_body={
            "enable_thinking": thk_en
        },
        callbacks=callbacks
    )
    return llm


def gen_llm_qwq_235b(
        temp: float = 0.1,
        tokens: int = 32768,
        streaming: bool = False,
        thk_en: bool = True,
        callbacks: list = None
) -> ChatOpenAI:
    llm = ChatOpenAI(
        api_key=QWQ_235B_KEY,
        base_url=BASE_URL,
        model=QWQ_235B_NAME,
        streaming=streaming,
        temperature=temp,
        max_tokens=tokens,
        extra_body={
            "enable_thinking": thk_en
        },
        callbacks=callbacks
    )
    return llm


def gen_qwq_coder_480b(
        temp: float = 0.7,
        tokens: int = 65536,
        streaming: bool = False,
        callbacks: list = None
) -> ChatOpenAI:
    """
    The annotations on ModelScope for Qwen3-Coder-480B-fp8 show that:
    (1) This model only supports non-thinking mode and will not generate
    <think></think> blocks in the output. At the same time, there is no longer
    a need to specify enable_thinking=False.
    (2) Best practice: We recommend that most queries use an output length
    of 65,536 tokens, which is sufficient for the instruction model.
    temperature = 0.7
    """
    llm = ChatOpenAI(
        api_key=QWQ_CODER_KEY,
        base_url=NORMAL_URL,
        model=QWQ_CODER_NAME,
        streaming=streaming,
        temperature=temp,
        max_tokens=tokens,
        callbacks=callbacks
    )
    return llm


def gen_custom_embeddings(max_len: int):


    # 代码专用模型
    model_name = "microsoft/codebert-base"
    # 或者使用更轻量的模型
    # model_name = "sentence-transformers/all-distilroberta-v1"

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    return embeddings


def gen_custom_reranker():
    # 使用开源的交叉编码器模型
    model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker = CrossEncoder(model_name)
    return reranker

