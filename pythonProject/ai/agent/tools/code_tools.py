from langchain_core.tools import tool
from typing import Literal
from ai.agent.ai_config.config import gen_llm_qwq_235b
from langchain_core.prompts.chat import ChatPromptTemplate
from ai.cad_agent_release.agent_core.tool_prompt import *


@tool
def code_gen_opt(
        code_lang: Literal['python', 'tcl', 'verilog'],
        task: Literal['generate', 'optimize'],
        task_desc: str,
        existing_code: str | None = None,
):
    """
    A powerful tool designed to either generate new code or optimize existing
    code in specified programming languages.

    This tool can create new code or improve the quality and efficiency of
    provided code based on a detailed functional description or optimizatiom
    advice.

    Args:
        code_lang(str, literal, required): The programming language of the code
            to be generated or optimized. Must be one of `python`, `tcl`,
            `verilog`.
        task(str, literal, required): The primary action to perform.
            - `generate`: Create new code based on task_desk.
            - `optimize`: To improve the existing code based on task_desk
        task_desc(str, required): A comprehensive description of the code
            generation task or the specific improvements desired for code
            optimization. For 'generate', this should detail the functionality,
            requirements, and any constraints(e.g., "Create a python function
            that sorts a list of dictionaries by a specific key, handling
            missing keys gracefully."). For `optimize`, it should detail the
            problem areas or desired outcomes (e.g., "reduce runtime of the
            current algorithm", "improve readability of the database query
            logic.")
        existing_code(str, optional): The complete string of the code to be
            optimized, This parameter is **required** if `task` is `optimize`.
            It should **not** be provided if `task` is `generate`.
    Return(str):
        A string representing the **final generated or optimized code**.
        The tool will return the complete code as a string upon successful
        completion of generation or optimization task.
    """
    llm = gen_llm_qwq_235b()

    if task == 'generate':
        human_input = (f"I'd like to help me generate code that meets the "
                       f"following requirements: {task_desc}")
    elif task == 'optimize':
        human_input = (f"I'd like to help me optimize the following code: "
                       f"{existing_code}, and meets the following "
                       f"requirements: {task_desc}.")
    else:
        return (f"An ERROR occurred while determining the code generation plan "
                f"or the code optimization plan.")

    if code_lang == 'python':
        code_prompt = ChatPromptTemplate.from_messages([
            ("system", code_gen_py_sys_prompt),
            ("human", "{human_msg}")
        ])
    elif code_lang == 'tcl':
        code_prompt = ChatPromptTemplate.from_messages([
            ("system", code_gen_tcl_sys_prompt),
            # MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{human_msg}")
        ])
    elif code_lang == 'verilog':
        code_prompt = ChatPromptTemplate.from_messages([
            ("system", code_gen_verilog_sys_prompt),
            # MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{human_msg}")
        ])
    else:
        return (f"An ERROR occurred while detemining which programming "
                f"language"
                f"to generate or optimize")

    code_proc_chain = code_prompt | llm
    code_proc_msg = code_proc_chain.invoke(
        {
            "human_msg": human_input
        }
    )

    return code_proc_msg.content