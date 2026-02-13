import orjson
from pydantic import BaseModel, Field
from typing import TypedDict, Any, Annotated, Literal, Sequence, Callable
from ai.agent.ai_config.config import *
from ai.cad_agent_release.tools.auto_reg import auto_reg_tools
from ai.cad_agent_release.agent_core.prompt import *
from ai.cad_agent_release.agent_core.rag import *
from ai.cad_agent_release.agent_core.callbacks import *
from langchain_core.prompts.chat import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt


class AgentState(TypedDict):
    agent_input: str | None
    chat_history: Annotated[list, add_messages]
    agent_type: Literal['cad_run', 'cad_rag', 'general_chat'] | None
    clsfy_result: Literal[
                      'success',
                      'partial_success',
                      'failed',
                      'more_info'
                  ] | None
    need_clarify: bool | None
    user_confirm: bool | None
    display_output: str | None
    rag_info: str | None
    tool_call_list: list | None
    tool_run_history: Annotated[list, add_messages]


class UserIntent(BaseModel):
    decision: Literal["confirm", "deny", "clarify"] = Field(
        description="User's primary decision: 'confirm' to proceed, 'deny' "
                    "to cancel, or 'clarify' to ask for more information."
    )
    clarification_needed: bool = Field(
        description="True if the user is asking for clarification, False"
                    "otherwise"
    )
    clarification_query: str | None = Field(
        description="The specific question or topic the user wants clarified, "
                    "if clarification_needed is True. Otherwise, null."
    )


class PlanClassify(BaseModel):
    flow_results: Literal[
        'success',
        'partial_success',
        'failed',
        'more_info'] = Field(
        description="""
        Indicates the result of whether a complex flow can be constructed based 
        on the tools integrated with the LLM. "success" and "partial_success" 
        indicate that an execution plan has been formed and tools can be 
        executed afterwards. "failed" indicates that the existing tools are 
        insufficient to constitute the workflow the user wishes to implement. 
        "more_info" means that the currently available information is 
        insufficient to determine whether a workflow can be constructed, 
        and the user needs to provide additional information.
        """
    )
    flow_plan: str | None = Field(
        description="""
        Final information displayed to the user, when flow_results is success 
        or partial_success, this field will include an execution plan, if the
        flow_results is failed, it will tell user can not build workflow based 
        on existing tools, if the flow results is more-info, it means the llm 
        need more information! This string must have markdown format.
        """
    )


class ReceptionIntent(BaseModel):
    routing_result: Literal['cad_run', 'cad_rag', 'general_chat'] = Field(
        description="""
        The classification result. STRICTLY follow these core rules:
        - `cad_run`: For requests to *EXECUTE/OPERATE* CAD tools, scripts, 
          workflows, or os-level operations, Includes requests to find, create 
          or implement a solution to fix their problem.(Highest Priority)
        - `cad_rag`: For request to *EXPLAIN/LEARN* about CAD tools, concepts,
          errors, or methodologies. Pure knowledge questions.
        - `general_chat`: For greetings, casual talk, or any topic outside IC 
          CAD (including mechanical CAD).
        """
    )


def begin_input_node(state: AgentState) -> dict[str, Any]:
    user_input = interrupt("begin_input")
    rag_choose = user_input["assert_rag"]
    flow_choose = user_input["assert_flow"]
    query_str = user_input["query_str"]
    branch = "general_chat"
    if flow_choose:
        branch = "cad_run"
    if rag_choose and not flow_choose:
        branch = "cad_rag"
    if not flow_choose and not rag_choose:
        branch = "general_chat"
    return {
        "agent_input": query_str,
        "chat_history": [HumanMessage(content=query_str)],
        "agent_type": branch
    }


def post_plan_input(state: AgentState) -> dict[str, Any]:
    user_input = interrupt("post_plan_input")
    rag_choose = user_input["assert_rag"]
    flow_choose = user_input["assert_flow"]
    query_str = user_input["query_str"]
    branch = "general_chat"
    if flow_choose:
        branch = "cad_run"
    if rag_choose and not flow_choose:
        branch = "cad_rag"
    if not flow_choose and not rag_choose:
        branch = "general_chat"
    return {
        "agent_input": query_str,
        "chat_history": [HumanMessage(content=query_str)],
        "agent_type": branch
    }


def gen_chat_node(
        chat_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:

    general_chat_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", gnrl_chat_sys_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{agent_input}")
        ]
    )

    def general_chat_node(state: AgentState) -> dict[str, Any]:
        qt_tool_status.emit("generating answer...")
        gnrl_chain = general_chat_prompt_template | chat_llm
        response = gnrl_chain.invoke(
            {
                "agent_input": state['agent_input'],
                "chat_history": state['chat_history'][:-1]
            }
        )
        return {
            "chat_history": [response]
        }

    return general_chat_node


def gen_cad_run_plan(
        run_tools: Sequence[BaseTool],
        tool_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:

    def cad_run_plan(state: AgentState) -> dict[str, Any]:
        qt_tool_status.emit("generating execution plan...")
        tools_desc = []
        for tool in run_tools:
            desc = tool.description or "No Definition."
            tools_desc.append(f"- `{tool.name}`: {desc}")
        tool_desc_str = "\n".join(tools_desc)
        cad_run_plan_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", cad_plan_sys_prompt_2),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{agent_input}")
            ]
        ).partial(tools_description=tool_desc_str)

        tool_plan_chain = cad_run_plan_prompt_template | tool_llm.bind(
            response_format={"type": "json_object"}) | JsonOutputParser(
            pydantic_object=PlanClassify
            )
        result = tool_plan_chain.invoke(
            {
                "agent_input": state['agent_input'],
                "chat_history": state['chat_history'][:-1]
            }
        )
        return {
            "display_output": result["flow_plan"],
            "chat_history": [result["flow_plan"]],
            "clsfy_result": result["flow_results"]
        }
    return cad_run_plan


def gen_retrieve_node(
        retrvr,
        tools_name: list[str],
        retrieve_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:

    search_sop_tool = gen_retrieve_rag_info(retrvr, tools_name)

    def retrieve_node(state: AgentState) -> dict[str, Any]:
        qt_tool_status.emit("retrieving information...")
        retrieve_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", retrieve_sys_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{agent_input}"),
            ]
        )

        tool_llm = retrieve_llm.bind_tools([search_sop_tool])
        tool_call_chain = retrieve_prompt_template | tool_llm
        tool_call_msg = tool_call_chain.invoke({
            "agent_input": state['agent_input'],
            "chat_history": state['chat_history'][:-1],
        })

        rtrv_msg_l = []
        if not tool_call_msg.tool_calls:
            rtrv_msg = (
                f"Sorry, I couldn't find any relevant information in my "
                f"Knowledge base that directly addresses your query,"
                f"It's possible that the topic is not covered or the "
                f"keywords used did not yield a match."
                f"Please try rephrasing your question with different "
                f"keywords, or provide more specific details about what "
                f"you're looking for. This might help me find a more "
                f"accurate answer for you.")
            rtrv_msg_l.append(rtrv_msg)
        else:
            for tool_call in tool_call_msg.tool_calls:
                rtrv_msg = search_sop_tool.invoke(
                    tool_call["args"]
                )
                rtrv_msg_l.append(rtrv_msg)

        return {
            "rag_info": "\n".join(rtrv_msg_l)
        }
    return retrieve_node


def gen_rag_node(
        rag_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:
    def rag_node(state: AgentState) -> dict[str: Any]:
        qt_tool_status.emit("augmented generating answer...")
        rag_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", rag_answer_sys_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{agent_input}"),
            ]
        ).partial(rag_info=state['rag_info'])
        rag_chain = rag_prompt_template | rag_llm
        result = rag_chain.invoke(
            {
                "agent_input": state['agent_input'],
                "chat_history": state['chat_history'][:-1],
            }
        )
        return {
            "chat_history": [result],
            "rag_info": None
        }
    return rag_node


def gen_reception_node(reception_llm) -> Callable:
    reception_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", cad_reception_sys_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{agent_input}")
        ]
    )

    def reception_node(state: AgentState) -> dict[str, Any]:
        reception_chain = reception_prompt_template | reception_llm.bind(
            response_format={"type": "json_object"}) | JsonOutputParser(
            pydantic_object=ReceptionIntent
        )
        result = reception_chain.invoke(
            {
                "agent_input": state['agent_input'],
                "chat_history": state['chat_history'][:-1],
            }
        )
        agent_type = result.get("routing_result", "general_chat")
        return {
            "agent_type": agent_type
        }

    return reception_node


def process_user_confirmation(
        judge_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:
    judge_prompt_template = ChatPromptTemplate.from_messages([
        ("system", judge_prompt),
        ("human", "{agent_input}")
    ])

    judge_chain = judge_prompt_template | judge_llm.bind(
        response_format={"type": "json_object"}) | JsonOutputParser(
        pydantic_object=UserIntent
    )

    def interpret_user_confimation(state: AgentState) -> dict[str, Any]:
        qt_tool_status.emit("Identifying the user's intention ...")
        user_response = state['agent_input']
        try:
            judge_result = judge_chain.invoke({
                "agent_input": user_response,
                "agent_plan": state['display_output']
            })
            if judge_result["decision"] == "confirm":
                # TODO complete the return value
                return {
                    "user_confirm": True,
                    "need_clarify": False
                }
            elif judge_result["decision"] == "deny":
                return {
                    "user_confirm": False,
                    "need_clarify": False,
                }

            elif judge_result["decision"] == "clarify":

                return {
                    "user_confirm": False,
                    "need_clarify": True,
                    "agent_input": judge_result["clarification_query"]
                }
            else:
                return {
                    "user_confirm": False,
                    "need_clarify": False,
                }
        except Exception as e:
            print(f"Error when parsing the user confimation of running script:"
                  f"{e}")
            return {
                "user_confirm": False,
                "need_clarify": False,
            }

    return interpret_user_confimation


def gen_toolcall_plan_node(
        run_tools: Sequence[BaseTool],
        exec_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:
    tool_llm = exec_llm.bind_tools(run_tools)

    def toolcall_plan_node(state: AgentState) -> dict[str: Any]:
        qt_tool_status.emit("Preparing to execute plan ...")
        plan_run_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", tool_call_sys_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{agent_input}")
            ]
        )

        tool_call_chain = plan_run_prompt_template | tool_llm
        tool_call_msg = tool_call_chain.invoke({
            "agent_input": state['display_output'],
            "chat_history": state['chat_history'][:-1],
        })
        tool_call_plan = tool_call_msg.tool_calls
        return {
            "tool_call_list": tool_call_plan,
            "chat_history": [tool_call_msg]
        }

    return toolcall_plan_node


def gen_tool_call_node(
        run_tools: Sequence[BaseTool],
        qt_slot_sig: pyqtSignal(dict)
) -> Callable:
    tools_map = {one_tool.name: one_tool for one_tool in run_tools}

    def tool_call_node(state: AgentState) -> dict[str: Any]:
        tool_call_l = state["tool_call_list"]
        if not tool_call_l or len(tool_call_l) == 0:
            return {
                "tool_call_list": None,
                "tool_run_history": []
            }
        else:
            # Tool Info accquire
            tool_dict = tool_call_l[0]
            tool_name = tool_dict['name']
            tool_args = tool_dict['args']
            tool_id = tool_dict['id']

            # GUI Info pass
            tool_start_str = f"Invoking tool: `{tool_name}`\n"
            qt_slot_sig.emit({
                "tool_name": tool_name,
                "status": "start",
                "message": tool_start_str
            })

            # Tool Run procedure
            tool_on_call = tools_map.get(tool_name)
            tool_run_result = tool_on_call.invoke(tool_args)
            tool_run_content = (f"The result after running tool `{tool_name}` "
                                f"is {tool_run_result}")

            # Tool Result Info Pass
            tool_run_rslt_list = tool_run_result.split()
            rslt_show_gui = " ".join(tool_run_rslt_list[:30])
            rslt_show_gui = f"{rslt_show_gui} ... ...\n"

            qt_slot_sig.emit({
                "tool_name": tool_name,
                "status": "result",
                "message": rslt_show_gui
            })

            # handle the stateGraph data pass
            tool_run_msg = ToolMessage(
                content=tool_run_content,
                tool_call_id=tool_id,
                name=tool_name
            )

            # Tool End Info Pass
            tool_end_content = f"Done Tool: `{tool_name}`\n"
            qt_slot_sig.emit({
                "tool_name": tool_name,
                "status": "end",
                "message": tool_end_content
            })

            if tool_call_l[1:]:
                return {
                    "tool_call_list": tool_call_l[1:],
                    "tool_run_history": [tool_run_msg]
                }
            else:
                return {
                    "tool_call_list": [],
                    "tool_run_history": [tool_run_msg]
                }

    return tool_call_node


def gen_plan_update_node(
        run_tools: Sequence[BaseTool],
        exec_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:
    tool_llm = exec_llm.bind_tools(run_tools)

    def plan_update_node(state: AgentState) -> dict[str: Any]:
        qt_tool_status.emit("Updating the dependencies ...")
        initial_plan = state["display_output"]
        remaining_tool = orjson.dumps(state['tool_call_list'][0])
        next_tool_name = state['tool_call_list'][0]['name']
        # input_prompt = (f"Initial workflow execution plan presented to the "
        #                 f"user is {initial_plan}, The remaining tool_calls "
        #                 f"please refer {remaining_tool}, please help me check"
        #                 f"whether there are something to be updated.")

        input_prompt = (f"Initial workflow execution plan presented to user is"
                        f"{initial_plan}, The next tool to run is "
                        f"{next_tool_name}, please check if there are any "
                        f"placeholder parameters should be replaced and "
                        f"help me run next tool.")

        plan_update_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", plan_update_sys_prompt2),
                MessagesPlaceholder(variable_name="chat_history"),
                MessagesPlaceholder(variable_name="tool_run_history"),
                ("human", "{agent_input}")
            ]
        )
        plan_update_chain = plan_update_prompt_template | tool_llm
        new_tool_msg = plan_update_chain.invoke({
            "agent_input": input_prompt,
            "chat_history": state['chat_history'][:-1],
            "tool_run_history": state['tool_run_history']
        })
        new_tool_call_list = new_tool_msg.tool_calls
        if not new_tool_call_list:
            return
        elif len(new_tool_call_list) == 1:
            latest_tool_name = new_tool_call_list[0]['name']
            origin_tool_name = state["tool_call_list"][0]['name']
            if latest_tool_name == origin_tool_name:
                final_tool_call_list = new_tool_call_list + state[
                    "tool_call_list"
                ][1:]
                return {
                    "tool_call_list": final_tool_call_list,
                    "chat_history": [new_tool_msg]
                }
        elif len(new_tool_call_list) > 1:
            return {
                "tool_call_list": new_tool_call_list,
                "chat_history": [new_tool_msg]
            }
        else:
            return {
                "tool_call_list": []
            }
    return plan_update_node


def gen_tool_summary_node(
        smry_llm: ChatOpenAI,
        qt_tool_status: pyqtSignal
) -> Callable:
    def tool_summary_node(state: AgentState) -> dict[str: Any]:
        qt_tool_status.emit("Generating summary ...")
        initial_plan = state["display_output"] + "/no_think"
        tool_summary_prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", tool_summary_sys_prompt),
                MessagesPlaceholder(variable_name="tool_run_history"),
                ("human", "{agent_input}")
            ]
        )
        tool_summary_chain = tool_summary_prompt_template | smry_llm
        tool_summary_msg = tool_summary_chain.invoke({
            "agent_input": initial_plan,
            "tool_run_history": state['tool_run_history']
        })
        return {
            "chat_history": [tool_summary_msg],
            "tool_run_history": []
        }
    return tool_summary_node


def check_user_cfrm(state: AgentState) -> str:
    if state["user_confirm"]:
        return "confirm_plan"
    elif state["need_clarify"]:
        return "clarify_plan"
    else:
        return "reject_plan"


def check_run_end(state: AgentState) -> str:
    if state["tool_call_list"]:
        return "running"
    else:
        return "run_done"


def graph_core(
        new_text: pyqtSignal,
        tool_info: pyqtSignal,
        node_status: pyqtSignal
) -> StateGraph:

    router_llm = gen_llm_qwq_235b(temp=0.1)
    chat_llm = gen_llm_qwq_235b(
        temp=0.7,
        streaming=True,
        callbacks=[GUICallbackHandler(new_text)]
    )
    rtrvr_llm = gen_llm_qwq_235b(
        temp=0.1,
        streaming=False
    )
    rag_llm = gen_llm_qwq_235b(
        temp=0.5,
        streaming=True,
        callbacks=[GUICallbackHandler(new_text)]
    )
    tool_call_llm = gen_llm_qwq_235b(
        temp=0.1,
        streaming=False
    )

    smry_llm = gen_llm_qwq_235b(
        temp=0.7,
        streaming=True,
        callbacks=[GUICallbackHandler(new_text)],
        thk_en=False
    )

    script_tools, tools_name = auto_reg_tools()

    custom_retriever = gen_retriever(srch_k=5)

    # ------------ grpah node generate --------------------
    # six nodes with LLM
    plan_node = gen_cad_run_plan(
        run_tools=script_tools,
        tool_llm=tool_call_llm,
        qt_tool_status=node_status
    )

    toolcall_plan_node = gen_toolcall_plan_node(
        run_tools=script_tools,
        exec_llm=tool_call_llm,
        qt_tool_status=node_status
    )

    tool_call_node = gen_tool_call_node(
        run_tools=script_tools,
        qt_slot_sig=tool_info
    )

    plan_update_node = gen_plan_update_node(
        run_tools=script_tools,
        exec_llm=tool_call_llm,
        qt_tool_status=node_status
    )

    rtrv_node = gen_retrieve_node(
        retrvr=custom_retriever,
        tools_name=tools_name,
        retrieve_llm=rtrvr_llm,
        qt_tool_status=node_status
    )
    rag_node = gen_rag_node(rag_llm, qt_tool_status=node_status)
    chat_node = gen_chat_node(chat_llm, qt_tool_status=node_status)
    reception_node = gen_reception_node(router_llm)
    proc_confim_node = process_user_confirmation(
        router_llm,
        qt_tool_status=node_status
    )

    tool_summary_node = gen_tool_summary_node(
        smry_llm,
        node_status
    )

    # Add the node to the graph
    cad_agent = StateGraph(AgentState)
    cad_agent.add_node("begin_input", begin_input_node)
    cad_agent.add_node("post_plan_input", post_plan_input)
    # cad_agent.add_node("reception", reception_node)
    cad_agent.add_node("plan_run", plan_node)
    cad_agent.add_node("toolcall_plan", toolcall_plan_node)
    cad_agent.add_node("tool_call", tool_call_node)
    cad_agent.add_node("plan_update", plan_update_node)
    cad_agent.add_node("rtrv", rtrv_node)
    cad_agent.add_node("rag", rag_node)
    cad_agent.add_node("proc_confirm", proc_confim_node)
    cad_agent.add_node("chat", chat_node)
    cad_agent.add_node("tool_summary", tool_summary_node)

    # build the relationship between nodes
    cad_agent.add_edge(START, "begin_input")
    # cad_agent.add_edge("begin_input", "reception")
    cad_agent.add_conditional_edges(
        "begin_input",
        lambda state: state["agent_type"],
        {
            "cad_run": "plan_run",
            "cad_rag": "rtrv",
            "general_chat": "chat"
        }
    )
    cad_agent.add_edge("plan_run", "post_plan_input")
    cad_agent.add_conditional_edges(
        "post_plan_input",
        lambda state: state["clsfy_result"],
        {
            "success": "proc_confirm",
            "partial_success": "proc_confirm",
            "failed": "plan_run",
            "more_info": "plan_run"
        }
    )
    cad_agent.add_conditional_edges(
        "proc_confirm",
        check_user_cfrm,
        {
            "confirm_plan": "toolcall_plan",
            "clarify_plan": "rag",
            "reject_plan": "plan_run"
        }
    )
    cad_agent.add_edge("toolcall_plan", "tool_call")
    cad_agent.add_conditional_edges(
        "tool_call",
        check_run_end,
        {
            "run_done": "tool_summary",
            "running": "plan_update"
        }
    )
    cad_agent.add_edge("tool_summary", "begin_input")
    cad_agent.add_edge("plan_update", "tool_call")
    cad_agent.add_edge("rtrv", "rag")
    cad_agent.add_edge("rag", "begin_input")
    cad_agent.add_edge("chat", "begin_input")

    check_pnt = InMemorySaver()
    graph_app = cad_agent.compile(
        checkpointer=check_pnt
    )
    return graph_app
