from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from dataclasses import dataclass
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig


#1.定义系统提示词
SYSTEM_PROMPT = """you are an expert weather forecaster,who speaks in puns.
you have access to two tools:

- get_weather_for_location:use this to get the weather for a specific location.
- get_user_location:use this to get the user's location.

If a user askes you for the weather,make sure you know the location.If you can tell from
the question that they mean wherever they are,use the get_user_location tool to find their
location.
"""
#2.定义工具
@tool
def get_weather_for_location(city: str) -> str:
    """get weather for a given city"""
    return f"It's always sunny in {city}!"

@dataclass
class Context:
    """custom runtime context schema"""
    user_id:str

@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """get the user's location based on their user_id"""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "user_123" else "Newyork"

#3.配置model
# model = init_chat_model(
#     model="gpt-3.5-turbo", 
#     temperature=0,
#     timeout=10,
#     max_token=1000,
#     )
model = ChatOpenAI(
    model = "deepseek-32b-chat-v1",
    temperature=0,
    max_tokens=1000,
    timeout=10,
    api_key=" ",  # replace with your Deepseek API key
    base_url="https://api.deepseek.ai/v1/chat/completions"
    )



#4.定义响应格式
@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    punny_response:str
    weather_conditions:str | None = None

#5.添加内存
checkpointer = InMemorySaver()

#6.创建并运行agent
agent = create_agent(
    model = model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_weather_for_location, get_user_location],
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer,
)

config = RunnableConfig({"configurable":{"thread_id":"1"}})

response = agent.invoke(
    {"messages":[{"role":"user","content":"what's the weather like today?"}]},
    context=Context(user_id="1"),
    config=config,
)

print(response['structured_output'])