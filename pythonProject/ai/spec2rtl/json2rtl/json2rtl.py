from pathlib import Path
from collections import deque

from langchain.chains.question_answering.map_rerank_prompt import output_parser
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from transformers import AutoTokenizer
from langchain_chroma import Chroma
from langchain.schema import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.tools import tool
import networkx as nx
from ai.spec2rtl.json2rtl.spec_embedding import SpecEmbeddings
from ai.spec2rtl.json2rtl.json2graph import gen_spec_graph
from ai.spec2rtl.json2rtl.json_proc import SpecInfo
from ai.spec2rtl.json2rtl.constants import SpecNodeType


API_BASE_URL = "http://t-llmserver.ai.cdtp.com/v1/"
API_KEY = SecretStr("DeepSeek_R1_Still_Qwen_32B_RTAwMTk1Nj"
                    "YmRGVlcFNlZWtfUjFfU3RpbGxfUXdlbl8zMkImMjAyNS80LzI5")
MODEL_NAME = "DeepSeek-R1-Still-Qwen-32B"

EMBEDDING_MODEL_NAME = "test-bge-m3"
EMBEDDING_API_KEY = "test_bge_m3_RTAwMTk1NjYmdGVzdF9iZ2VfbTMmMjAyNS81LzIz"
EMBEDDING_URL = "http://t-llmserver.ai.cdtp.com/v1/embeddings"


def load_chroma_index(embeddings: SpecEmbeddings, db_dir: Path | str):
    if isinstance(db_dir, Path):
        return Chroma(
            persist_directory=db_dir.__str__(),
            embedding_function=embeddings,
            collection_name="spec_collection"
        )
    else:
        return Chroma(
            persist_directory=db_dir,
            embedding_function=embeddings,
            collection_name="spec_collection"
        )


def filter_node_type(graph: nx.DiGraph, type_n: str):
    rtn_l = []
    for node, attr in graph.nodes(data=True):
        if attr.get("type") == type_n:
            rtn_l.append(node)

    return rtn_l


def search_ancestor_nodes(ref_graph: nx.DiGraph,
                          src_node,
                          depth: int | None = None) -> list:
    ancestor = [src_node]
    queue_n = deque([src_node])
    if depth is None:
        while queue_n:
            node = queue_n.popleft()
            for pred in ref_graph.predecessors(node):
                if pred not in ancestor:
                    ancestor.append(pred)
                    queue_n.append(pred)
    else:
        cnt = 0
        while queue_n:
            node = queue_n.popleft()
            for pred in ref_graph.predecessors(node):
                if pred not in ancestor:
                    ancestor.append(pred)
                    queue_n.append(pred)
            cnt += 1
            if cnt == depth:
                break
    return ancestor


def classify_nodes_by_type(ref_graph: nx.DiGraph, nodes_list: list) -> dict:
    rtn_dict = {}
    for node in nodes_list:
        fnd_tp = ref_graph.nodes[node].get('type')
        if fnd_tp in rtn_dict:
            rtn_dict[fnd_tp].append(node)
        else:
            rtn_dict[fnd_tp] = [node]

    return rtn_dict


def create_hybrid_retriever(vector_store, txts: str, srch_k: int = 3):
    bm25_retriever = BM25Retriever.from_texts(txts)
    bm25_retriever.k = srch_k

    # create the vector retriever
    vector_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": srch_k}
    )

    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.4, 0.6]
    )
    return hybrid_retriever


def gen_embeddings():
    # configure the tokenizer file
    tknzr_file = ("/home/barwellg/python_repo/ai/spec2rtl/"
                  "extra_file/tokenizer_ivv")
    tknzr = AutoTokenizer.from_pretrained(tknzr_file)

    embeddings = SpecEmbeddings(
        tokenizer=tknzr,
        base_url=EMBEDDING_URL,
        model_name=EMBEDDING_MODEL_NAME,
        api_key=EMBEDDING_API_KEY,
        max_length=512
    )
    return embeddings


def pass_local_query_db(db: Chroma):
    @tool
    def query_vec_db(query_info: str):
        """
        when the prompt contains professional terms, abbreviations, or concepts
        that you may not understand, call this tool to search for their definitions
        in the local knowledge base.
        for example: if encountering "after tRRDL, there will issue a new coomand",
        you may not understand the 'tRRDL', you should exact specific term such as
        'tRRDL' and call this tool as a 'query_info' parameter

        This tool will return the explanation of the query_info
        """
        retriever = create_hybrid_retriever(db, query_info, 1)


    return query_vec_db


def main():
    work_dir = Path.cwd()
    chrma_dir = work_dir / "chroma_db"
    chrma_dir.mkdir(parents=True, exist_ok=True)
    spec_json_path = ("/home/barwellg/python_repo/ai/spec2rtl/"
                      "json2rtl/ref_file/spec_fmt.json")
    spec_json_p = Path(spec_json_path)
    spec_json_str = spec_json_p.read_text()

    llm = ChatOpenAI(
        api_key=API_KEY,
        base_url=API_BASE_URL,
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=32768
    )

    embeddings = gen_embeddings()

    vec_store = Chroma(
        persist_directory=chrma_dir.__str__(),
        embedding_function=embeddings
    )

    spec_info = SpecInfo.from_json(spec_json_path)
    attr_d = {
        "state": spec_info.fsm_info,
        "encoding": spec_info.op_code,
        "port": spec_info.port_info,
        "glossary": spec_info.glossary
    }

    dsps_txts = []
    for cd, text in spec_info.op_code.cmd_on_port_text_map.items():
        dsps_txts.append(text)
    for p_n, p_txt in spec_info.port_info.port_text.items():
        dsps_txts.append(p_txt)
    for glsy, g_txt in spec_info.glossary.text.items():
        dsps_txts.append(g_txt)
    for stat, s_txt in spec_info.fsm_info.states_text.items():
        dsps_txts.append(s_txt)

    # add the individual definition to the Vec store
    vec_store.add_texts(texts=dsps_txts)

    gph = gen_spec_graph(attr_d)
    state_nodes = filter_node_type(gph, SpecNodeType.STATE.value)
    state_txts = []
    for state_n in state_nodes:
        rlt_nodes = search_ancestor_nodes(gph, state_n, depth=1)
        rlt_nodes_mp = classify_nodes_by_type(gph, rlt_nodes)
        t_embd_st_str = ""
        for tp, n_l in rlt_nodes_mp.items():
            if tp == SpecNodeType.STATE.value:
                st_l = []
                for node in n_l:
                    st_l.append(spec_info.fsm_info.states_text[node])
                state_str = "; ".join(st_l)
                t_embd_st_str += state_str
            elif tp == SpecNodeType.PORT.value:
                prt_l = []
                for node in n_l:
                    prt_l.append(spec_info.port_info.port_text[node])
                port_str = "; ".join(prt_l)
                t_embd_st_str += port_str
            elif tp == SpecNodeType.OP_CODE.value:
                code_l = []
                for node in n_l:
                    code_l.append(spec_info.op_code.cmd_on_port_text_map[node])
                code_str = "; ".join(code_l)
                t_embd_st_str += code_str
            elif tp == SpecNodeType.GLSRY.value:
                glsry_l = []
                for node in n_l:
                    glsry_l.append(spec_info.glossary.text[node])
                glsry_str = "; ".join(glsry_l)
                t_embd_st_str += glsry_str
            else:
                raise ValueError(f"Unknown node type: {tp}")

        state_txts.append(t_embd_st_str)

    # vec_store.add_texts(
    #     texts=state_txts
    # )
    # all_txts.extend(state_txts)
    # print("The text has already be vectorized")

    chr_db = load_chroma_index(embeddings, chrma_dir)
    retriever = create_hybrid_retriever(chr_db, dsps_txts)
    query = "what the value can be on the port Cr0"
    print(f"looking for Cr0 function")

    results = retriever.get_relevant_documents(query)
    print(results)

# spec_json_p = Path("/home/barwellg/python_repo/ai/spec2rtl/"
#                    "json2rtl/ref_file/spec_fmt.json")
# loader = JSONLoader(file_path=spec_json_p,
#                     jq_schema=".design_overview")
#
# json_ref = loader.load()

# def gen_response(client: ChatOpenAI, message: list,
#                  lgr:logging.Logger, temp="normal") -> str:
#     low_llm_client = ChatOpenAI(
#         model=MODEL_NAME,
#         api_key=API_KEY,
#         base_url=API_BASE_URL,
#         temperature=0.0
#     )
#
#     normal_llm_client = ChatOpenAI(
#         model=MODEL_NAME,
#         api_key=API_KEY,
#         base_url=API_BASE_URL
#     )
#
#     if temp == "normal":
#         rsps = normal_llm_client(messages=message)
#     elif temp == "low":
#         rsps = low_llm_client(messages=message)
#     else:
#         raise ValueError("temp must be 'normal' or 'low'")
#
#     ctnt = rsps.content
#     # prmpt_tokens = rsps.usage.get("input_tokens")
#     # cmplt_tokens = rsps.usage.get("output_tokens")
#     # ttl_tokens = rsps.usage.get("total_tokens")
#     # lgr.info("The complete message is:\n%s", ctnt)
#     # lgr.info("---------------------------------------------------------------")
#     # lgr.info("***  The Prompt Token number is: %d  ***", prmpt_tokens)
#     # lgr.info("***  The Completion Token number is: %d  ***", cmplt_tokens)
#     # lgr.info("***  The Total Token number used is: %d  ***", ttl_tokens)
#
#     return ctnt

# low_llm_client = ChatOpenAI(
#     model=MODEL_NAME,
#     api_key=API_KEY,
#     base_url=API_BASE_URL,
#     temperature=0.0
# )
#
# normal_llm_client = ChatOpenAI(
#     model=MODEL_NAME,
#     api_key=API_KEY,
#     base_url=API_BASE_URL
# )

# def main():
#     start_time = datetime.datetime.now()
#     # logger = general_func.init_logging("json2rtl_v2.log")
#
#     memory = ConversationBufferMemory(memory_key="chat_history")
#
#
#
#
#     end_time = datetime.datetime.now()
#     general_func.script_runtime_prt(start_time, end_time)
if __name__ == "__main__":
    main()

