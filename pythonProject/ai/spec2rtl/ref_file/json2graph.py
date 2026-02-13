from pathlib import Path
# from py_lib.general_func import general_func
import networkx as nx
from whoosh.fields import Schema, TEXT, ID, KEYWORD, NUMERIC
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh import scoring
import matplotlib.pyplot as plt
import numpy as np
from itertools import product
from ai.spec2rtl.json2rtl.constants import SpecNodeType


def gen_graph_pic(g: nx.DiGraph, type_odr: list,
                  scale: int = 1.0,
                  gap: int = 1.0):
    node_colors = [g.nodes[node].get('color', 'black') for node in g.nodes()]
    node_type_d = {}
    for node, data in g.nodes(data=True):
        node_type = data.get('type')
        if node_type not in type_odr:
            node_type = None

        if node_type not in node_type_d.keys():
            node_type_d.update({node_type: []})

        node_type_d[node_type].append(node)

    radius_map = {}
    for i, node_type in enumerate(type_odr):
        radius_map[node_type] = (i + 1) * gap

    if None in node_type_d.keys():
        radius_map[None] = (len(type_odr) + 1) * gap

    # create circular layout for each node
    pos = {}
    for node_type, nodes in node_type_d.items():
        radius = radius_map[node_type] * scale
        n = len(nodes)

        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        for i, node in enumerate(nodes):
            x = radius * np.cos(theta[i])
            y = radius * np.sin(theta[i])
            pos[node] = (x, y)

    plt.figure(figsize=(12, 12))
    nx.draw(g, pos, with_labels=True, node_color=node_colors,
            node_size=250, arrowsize=15, font_size=10, edge_color='gray')
    plt.savefig("fsm_graph.png")


def gen_spec_graph(obj_map: dict) -> nx.DiGraph:
    """
    :param obj_map:
    :return:
    """
    port_obj = obj_map[SpecNodeType.PORT.value]
    # TODO need consider the mult state mch situation
    fsm_obj = obj_map[SpecNodeType.STATE.value]
    glsry_obj = obj_map[SpecNodeType.GLSRY.value]
    op_code_obj = obj_map[SpecNodeType.OP_CODE.value]

    # type_order is a hard-coding
    type_order = [
        SpecNodeType.STATE.value,
        SpecNodeType.PORT.value,
        SpecNodeType.OP_CODE.value,
        SpecNodeType.GLSRY.value
    ]

    cur_dir = Path.cwd()
    index_dir = cur_dir / "search_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    schema = Schema(
        id=ID(unique=True, stored=True),
        title=TEXT(stored=True),
        content=TEXT
    )
    ix = index.create_in(index_dir, schema)
    writer = ix.writer()

    r_graph = nx.DiGraph()
    for state in fsm_obj.states:
        r_graph.add_node(state, color="green",
                         label=state, type=SpecNodeType.STATE.value)
        st_text = fsm_obj.states_text.get(state)
        writer.add_document(
            id=f"{state}_text",
            title=f"{state}_behaviour",
            content=st_text
        )

    for port_n in port_obj.ports:
        r_graph.add_node(port_n, color="blue",
                         label=port_n, type=SpecNodeType.PORT.value)
        port_text = port_obj.port_text.get(port_n)
        writer.add_document(
            id=f"{port_n}_text",
            title=f"{port_n}_description",
            content=port_text
        )

    port_cmd_d = {}
    for port_n in op_code_obj.port_cmd_text_map.keys():
        for cmd_n in op_code_obj.port_cmd_text_map[port_n].keys():
            node_n = f"{cmd_n}-on-{port_n}"
            p_c_txt = op_code_obj.port_cmd_text_map[port_n][cmd_n]
            port_cmd_d.update({node_n: p_c_txt})
            r_graph.add_node(node_n, color="yellow",
                             label=node_n, type=SpecNodeType.OP_CODE.value)

    for p_c_n, p_c_txt in port_cmd_d.items():
        writer.add_document(
            id=f"{p_c_n}_text",
            title=f"{p_c_n}_description",
            content=p_c_txt
        )
        sp_l = p_c_n.split("-on-")
        p_nm = sp_l[1]
        # build the code map between port and command
        r_graph.add_edge(p_c_n, p_nm)

    writer.commit()
    for glsy in glsry_obj.names:
        r_graph.add_node(glsy, color="pink",
                         label=glsy, type=SpecNodeType.GLSRY.value)

    qp = QueryParser(f"content", schema=ix.schema)
    for state in fsm_obj.states:
        # if the port used in state definitions.
        for port_n in port_obj.ports:
            query = qp.parse(f"{port_n} AND id:{state}_text")
            with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
                results = searcher.search(query, limit=10)
                if not results:
                    pass
                    # print(f"{port_n} is not in the {state} function")
                else:
                    print(f"{port_n} is in the {state} function")
                    r_graph.add_edge(port_n, state)

        # if the glossary used in state definition
        for glsy in glsry_obj.names:
            query = qp.parse(f"{glsy} AND id:{state}_text")
            with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
                results = searcher.search(query, limit=10)
                if not results:
                    pass
                else:
                    print(f"{glsy} is in the {state} function")
                    r_graph.add_edge(glsy, state)

        # if the command and it's pin in stade definition build edge
        for cmd_name in op_code_obj.cmd_names:
            query = qp.parse(f"{cmd_name} AND id:{state}_text")
            with (ix.searcher(weighting=scoring.TF_IDF()) as searcher):
                results = searcher.search(query, limit=10)
                if not results:
                    pass
                else:
                    rlt_ports = op_code_obj.cmd_port_map[cmd_name]
                    for p_n in rlt_ports:
                        query = qp.parse(f"{p_n} AND id:{state}_text")
                        with ix.searcher(weighting=scoring.TF_IDF()) as scr:
                            rslt = scr.search(query, limit=10)
                            if not rslt:
                                pass
                            else:
                                node_n = f"{cmd_name}-on-{p_n}"
                                r_graph.add_edge(node_n, state)

    # build the relationship between ports
    for port_n1, port_n2 in product(port_obj.ports, repeat=2):
        if port_n1 == port_n2:
            continue
        query = qp.parse(f"{port_n2} AND id: {port_n1}_text")
        with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
            results = searcher.search(query, limit=10)
            if not results:
                pass
            else:
                print(f"{port_n2} used in {port_n1} description")
                r_graph.add_edge(port_n2, port_n1)

    # buld the relationship between port and glossary
    for port_n in port_obj.ports:
        for glsy in glsry_obj.names:
            query = qp.parse(f"{glsy} AND id:{port_n}_text")
            with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
                results = searcher.search(query, limit=10)
                if not results:
                    pass
                else:
                    print(f"{glsy} used in {port_n} description")
                    r_graph.add_edge(glsy, port_n)

    # build the relationship between glossary and command-code
    for p_c_n, p_c_txt in port_cmd_d.items():
        for glsy in glsry_obj.names:
            query = qp.parse(f"{glsy} AND id:{p_c_n}_text")
            with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
                results = searcher.search(query, limit=10)
                if not results:
                    pass
                else:
                    print(f"{glsy} used in {p_c_n} description")
                    r_graph.add_edge(glsy, p_c_n)

    gen_graph_pic(r_graph, type_order)
    return r_graph


# def main(args):
#     spec_json_path = args.spec_json
#     cur_dir = Path.cwd()
#     index_dir = cur_dir / "search_index"
#     index_dir.mkdir(parents=True, exist_ok=True)
#
#     schema = Schema(
#         id=ID(unique=True, stored=True),
#         title=TEXT(stored=True),
#         content=TEXT
#     )
#
#     ix = index.create_in(index_dir, schema)
#     writer = ix.writer()
#     spec_json_p = Path(spec_json_path)
#     spec_json_str = spec_json_p.read_text()
#     spec_json_obj = orjson.loads(spec_json_str)
#
#     port_obj = PortInfo.from_json(spec_json_obj)
#     fsm_obj = StateMachineInfo.from_json(spec_json_obj)
#
#     glsry_obj = Glossary.from_json(spec_json_obj)
#     op_code_obj = OpCode.from_json(spec_json_obj)
#     type_order = ["state", "port", "encoding", "glossary"]
#     G = nx.DiGraph()
#     for state in fsm_obj.states:
#         G.add_node(state, color="green", label=state, type="state")
#         st_i = fsm_obj.states_inst[state]
#         st_text = st_i.behavior_text
#         writer.add_document(
#             id=f"{state}_text",
#             title=f"{state}_behaviour",
#             content=st_text
#         )
#
#     for port_n in port_obj.ports:
#         G.add_node(port_n, color="blue", label=port_n, type="port")
#         port_text = port_obj.port_text.get(port_n)
#         writer.add_document(
#             id=f"{port_n}_text",
#             title=f"{port_n}_description",
#             content=port_text
#         )
#
#     port_cmd_d = {}
#     for port_n in op_code_obj.port_cmd_text_map.keys():
#         for cmd_n in op_code_obj.port_cmd_text_map[port_n].keys():
#             node_n = f"{cmd_n}-on-{port_n}"
#             p_c_txt = op_code_obj.port_cmd_text_map[port_n][cmd_n]
#             port_cmd_d.update({node_n: p_c_txt})
#             G.add_node(node_n, color="yellow", label=node_n, type="encoding")
#
#     for p_c_n, p_c_txt in port_cmd_d.items():
#         writer.add_document(
#             id=f"{p_c_n}_text",
#             title=f"{p_c_n}_description",
#             content=p_c_txt
#         )
#         sp_l = p_c_n.split("-on-")
#         p_nm = sp_l[1]
#         # build the code map between port and command
#         G.add_edge(p_c_n, p_nm)
#
#     writer.commit()
#
#     for glsy in glsry_obj.names:
#         G.add_node(glsy, color="pink", label=glsy, type="glossary")
#
#     qp = QueryParser(f"content", schema=ix.schema)
#     for state in fsm_obj.states:
#         # if the port used in state definition
#         for port_n in port_obj.ports:
#             query = qp.parse(f"{port_n} AND id:{state}_text")
#             with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
#                 results = searcher.search(query, limit=10)
#                 if not results:
#                     pass
#                     # print(f"{port_n} is not in the {state} function")
#                 else:
#                     print(f"{port_n} is in the {state} function")
#                     G.add_edge(port_n, state)
#
#         # if the glossary used in state definition
#         for glsy in glsry_obj.names:
#             query = qp.parse(f"{glsy} AND id:{state}_text")
#             with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
#                 results = searcher.search(query, limit=10)
#                 if not results:
#                     pass
#                 else:
#                     print(f"{glsy} is in the {state} function")
#                     G.add_edge(glsy, state)
#
#         # if the command and it's pin in stade definition build edge
#         for cmd_name in op_code_obj.cmd_names:
#             query = qp.parse(f"{cmd_name} AND id:{state}_text")
#             with (ix.searcher(weighting=scoring.TF_IDF()) as searcher):
#                 results = searcher.search(query, limit=10)
#                 if not results:
#                     pass
#                 else:
#                     rlt_ports = op_code_obj.cmd_port_map[cmd_name]
#                     for p_n in rlt_ports:
#                         query = qp.parse(f"{p_n} AND id:{state}_text")
#                         with ix.searcher(weighting=scoring.TF_IDF()) as scr:
#                             rslt = scr.search(query, limit=10)
#                             if not rslt:
#                                 pass
#                             else:
#                                 node_n = f"{cmd_name}-on-{p_n}"
#                                 G.add_edge(node_n, state)
#
#     # build the relationship between ports
#     for port_n1, port_n2 in product(port_obj.ports, repeat=2):
#         if port_n1 == port_n2:
#             continue
#         query = qp.parse(f"{port_n2} AND id: {port_n1}_text")
#         with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
#             results = searcher.search(query, limit=10)
#             if not results:
#                 pass
#             else:
#                 print(f"{port_n2} used in {port_n1} description")
#                 G.add_edge(port_n2, port_n1)
#
#     # buld the relationship between port and glossary
#     for port_n in port_obj.ports:
#         for glsy in glsry_obj.names:
#             query = qp.parse(f"{glsy} AND id:{port_n}_text")
#             with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
#                 results = searcher.search(query, limit=10)
#                 if not results:
#                     pass
#                 else:
#                     print(f"{glsy} used in {port_n} description")
#                     G.add_edge(glsy, port_n)
#
#     # build the relationship between glossary and command-code
#     for p_c_n, p_c_txt in port_cmd_d.items():
#         for glsy in glsry_obj.names:
#             query = qp.parse(f"{glsy} AND id:{p_c_n}_text")
#             with ix.searcher(weighting=scoring.TF_IDF()) as searcher:
#                 results = searcher.search(query, limit=10)
#                 if not results:
#                     pass
#                 else:
#                     print(f"{glsy} used in {p_c_n} description")
#                     G.add_edge(glsy, p_c_n)
#
#     gen_graph_pic(G, type_order)
#     return G
#
#
# if __name__ == "__main__":
#     start_time = datetime.datetime.now()
#     parser = argparse.ArgumentParser()
#     parser.add_argument("-sj", "--spec_json",
#                         help="input path of json file that include "
#                              "specification informations")
#     args_ps = parser.parse_args()
#     main(args_ps)
#     end_time = datetime.datetime.now()
#     general_func.script_runtime_prt(start_time, end_time)
