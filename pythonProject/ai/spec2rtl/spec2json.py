import re
import copy
import os
import sys
import logging
import datetime
from pathlib import Path
from py_lib.general_func import general_func


def main():
    start_time = datetime.datetime.now()
    pass
    end_time = datetime.datetime.now()
    general_func.script_runtime_prt(start_time, end_time)


if __name__ == "__main__":
    main()
\end{verbatim}
\section{try-func.py}
\begin{verbatim}
from pydantic import SecretStr
from openai import OpenAI
import json

BASE_URL = "http://t-llmserver.ai.cdtp.com/v1/"
API_KEY = SecretStr("DeepSeek_R1_Still_Qwen_32B_RTAwMTk1Nj"
                    "YmRGVlcFNlZWtfUjFfU3RpbGxfUXdlbl8zMkImMjAyNS80LzI5")
MODEL_NAME = "DeepSeek-R1-Still-Qwen-32B"

QWQ_235B_KEY = ("test_Qwen3_235B_GPTQ_Int8_RTAwMTk1NjYmdGVzdF9Rd2VuM18yMz"
                "VCX0dQVFFfSW50OCYyMDI1LzcvMjQ=")
QWQ_235B_NAME = "test-Qwen3-235B-GPTQ-Int8"

QWQ_32B_KEY = "QWQ_32B_RTAwMTk1NjYmUVdRXzMyQiYyMDI1LzQvMjc="
QWQ_32B_NAME = "QWQ-32B"


def magic_add(a: int, b: int) -> int:
    return a + b + 2


client = OpenAI(
    api_key=QWQ_235B_KEY,
    base_url=BASE_URL
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "magic_add",
            "description": "This is a magic_add method, the user should provide"
                           " two int number, and this function will return a value",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "int",
                        "description": "augend, for example 3, 2, 5"
                    },
                    "b": {
                        "type": "int",
                        "description": "addend, for example 4, 6, 7"
                    }
                },
                "required": ["a", "b"]
            }
        }
    }
]


def run_conversation(user_query):
    msg = [{"role": "user", "content": user_query}]

    response = client.chat.completions.create(
        model=QWQ_235B_NAME,
        messages=msg,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    msg.append(response_message)

    if response_message.tool_calls:
        available_functions = {
            "magic_add": magic_add
        }
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)

            function_response = function_to_call(**function_args)

            msg.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response)
                }
            )

        second_response = client.chat.completions.create(
            model=QWQ_235B_NAME,
            messages=msg
        )
        return second_response.choices[0].message.content
    else:
        return response_message.content


query = "what is the result of 4 and 5 to do magic_add"
run_conversation(query)