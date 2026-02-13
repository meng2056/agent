#模型的技能
#1. text generation
#2.Tool calling
#3.Structured output
#4. Multimodality
#5. Reasoning

#基本使用方法：
#1.与agent一起使用
#2. 单独使用

#initialize model
import os
from langchain.chat_models import init_chat_model

os.environ["OPENAI_API_KEY"] = "your_api_key"

model = init_chat_model("gpt-3.5-turbo")

result = model.invoke("What is the capital of France?")

# Invocation 调用
#1. invoke
response = model.invoke("why do parrots have colorful feathers?")
print(response)

#2.Stream 
for chunk in model.stream("why do parrots have colorful feathers?"):
    print(chunk.text, end = "|", flush = True)

for chunk in model.stream("what color is the sky?"):
    for block in chunk.content_blocks:
        if block["type"] == "reasoning" and (reasoning := block.get("reasoning")):
            print(f"{reasoning}")
        elif block["type"] == "tool_call_chunk":
            print(f"Tool call chunk:{block}")
        elif block["type"] == "text":
            print(block["text"])
        else:
            ...

#3. batch
responses = model.batch([
    "what is the capital of France?",
    "what is the capital of Germany?",
    "what is the capital of China?"
])
for responses in responses:
    print(responses)

#4. Tool calling(function calling)
#schma:包含tool的name,description,and/or argument definitions.(经常是JSON Schema)
# function or 执行的corotuine
#要使定义的tool可供model使用，必须使用bind_tools将他们绑定 
#与agent中tool calling不同的是：model的tool需要手动去执行，然后将tool_result返回给model，
#而agent可以自动对执行tool并返回结果

from langchain.tools import tool

@tool
def get_weather(city:str) -> str:
    """get weather for a city"""
    return f"the weather in{city} is sunny ! "

model_with_tools = model.bind_tools([get_weather])

response = model_with_tools.invoke("what is the weather in shanghai?")
for tool_call in response.tool_calls:
    print(f"Tool:{tool_call['name']}")
    print(f"Arguments:{tool_call['args']}")

##一些常见的工具调用方式
#1. tool execution loop
#2. 强制工具调用
model_with_tools = model.bind_tools([tool1],tool_choice="any")
model_with_tools = model.bind_tools([tool1],tool_choice="tool1")
#3.并行执行
model_with_tools = model.bind_tools([tool1])
response = model_with_tools.invoke("what is the weather in shanghai?",parallel=True)
print(response.tool_calls)
#4.流式调用tool call
for chunk in model_with_tools.stream("what is the weather in shanghai?"):
    for tool_chunk in chunk.tool_call_chunks:
        if name := tool_chunk.get("name"):
            print(f"Tool call chunk:{name}")
        elif args := tool_chunk.get("args"):
            print(f"Arguments:{args}")

#5. 结构化输出-（pydantic,TypedDict, JSON)
#Pydantic 提供最丰富的feature set,包括 validation,descriptions,nested structures.

from pydantic import BaseModel, Field

class Movie(BaseModel):
    """a movie with details."""
    title:str = Field(...,description="the title of the movie")
    year:int = Field(...,description="the year the movie was released")
    director:str = Field(...,description="the director of the movie")

model_with_structure = model.with_structured_output(Movie)
response = model_with_structure.invoke("provide details about the movie 'The Godfather'")
print(response)

#将原始AIMessage对象和解析后的表示一起返回，可以在调用with_structured_output是设include_raw=True
#schemas可以嵌套

#6.Reasoning
#stream reasoning output
for chunk in model.stream("what is the capital of France?"):
    reasoning_steps = [r for r in chunk.content_blocks if r["type"] == "reasoning"]
    print(reasoning_steps if reasoning_steps else chunk.text)
#Complete reasoning output
response = model.invoke("what is the capital of France?")
reasoning_steps = [b for b in response.content_blocks if b["type"] == "reasoning"]
print("".join(step["reasoning"] for step in reasoning_steps))

#7. base_url 和 代理
#base_url:许多model提供兼容OpenAI的API，可以通过指定相应的base_url来使用他们的init_chat_model
model = init_chat_model(
    model = "MOOD_NAME",
    model_provider="deepseek",
    base_url="https://api.deepseek.ai/v1",
    api_key="your_api_key"
)
#Proxy
model = ChatOpenAI(
    model = "gpt-3.5-turbo",
    model_provider="openai",
    proxy="http://your_proxy:port"
)
