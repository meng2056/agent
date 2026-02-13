# Core components

## Model

### static method
"""静态模型在创建代理时配置一次，并在整个执行过程中保持不变。"""

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model = "deepseek-32b-chat-v1",
    temperature=0,
    timeout=10,
    max_tokens=1000,
    api_key="",
    base_url="https://api.deepseek.ai/v1/chat/completions"
    )

agent = create_agent(model,tools=tools)

### dynamic method
"""动态模型在runtime期间根据上下文或其他因素进行调整。使用@wrap_model_call装饰器创建中间件函数，
以便在每次调用模型之前修改其参数。"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse

basic_model = ChatOpenAI(model = "deepseek-32b-chat-v1", temperature=0)
advenced_model = ChatOpenAI(model = "deepseek-32b-chat-v1", temperature=0.7)

@wrap_model_call
def dynamic_model_selection(request:ModelRequest,handler) -> ModelResponse:
    """Choose model based on conversation complexity(number of messages)."""
    message_count = len(request.state["messages"])

    if message_count > 5:
        model = advenced_model
    else:
        model = basic_model

    return handler(request.override(model=model))

agent = create_agent(
    model =basic_model,
    tools = tools,
    middleware=[dynamic_model_selection]
)

## Tools
###defining tools
from langchain.tools import tool
from langchain.agents import create_agent

@tool
def search(query:str) -> str:
    """Search the web for a query."""
    return f"Results for : {query}"

@tool
def get_weather(city:str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

tools = [search,get_weather]

agent = create_agent(model,tools = tools)

### tool error handling
"""要自定义处理 tool error 的方式，使用@wrap_tool_call装饰器创建中间件"""

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage

@wrap_tool_call
def handle_tool_error(request,handler):
    """Handle tool execution errors with custom message."""
    try:
        return handler(request)
    except Exception as e:
        #return a custom error message to the model.
        return ToolMessage(
            content=f"Tool error:please check your input and try again.({str(e)})",
            tool_call_id=request.tool_call_id,
        )
    agent = create_agent(model,tools = tools,middleware=[handle_tool_error])

### Tool use in the React loop
"""agent 遵守 ReAct 模式，在简短的推理步骤和有针对性地工具调用之间交互进行"""

### Dynamic tools
"""在某些情况下，你需要在运行时修改agent可用的工具集，而不是预先定义所有工具，根据工具是否预先已知，
分俩种情况"""

#1. 筛选预注册工具
"""如果在创建agent时已知所有可能的工具，则可以预先注册他们，并根据状态，权限，上下文动态筛选
哪些工具可以公开给模型使用"""

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def filter_tools(
    request:ModelRequest,
    handler:Callable[[ModelRequest],ModelResponse],
) -> ModelResponse:
    """filter tools based on user permissions."""

    user_role = request.runtime.context.user_role

    if user_role == "admin":
        tools = request.tools
    else:
        tools = [t for t in request.tools if t.name.startswith("read_")]
    
    return handler(request.override(tools=tools))

agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[filter_tools],
)

#2. 运行时工具注册
"""在运行时发现或创建工具，你需要注册这些工具，并动态处理他们的执行。
    使用@wrap_model_call:将动态工具添加到请求中，
    使用@wrap_tool_call:处理动态添加的工具执行"""

from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain.agents.middleware.types import ToolCallRequest

# a tool that will be added dynamically at runtime
@tool
def calculate_tip(bill_amount:float, tip_percentage:float = 20.0) -> float:
    """Calculate tip based on bill amount and tip percentage."""
    return bill_amount * (tip_percentage / 100)

class DynamicToolMiddleware(AgentMiddleware):
    """Middleware that registers and handles dynamic tools."""

    def wrap_model_call(self, request:ModelRequest,handler):
        #add dynamic tool to the request.
        #this could be loaded from an MCP server,database, etc.
        updated = request.override(tools = [*request.tools,calculate_tip])
        return handler(updated)
    
    def wrap_tool_call(self,request:ToolCallRequest,handler):
        #handle execution of the dynamic tool.
        if request.tool_call["name"] == "calculate_tip":
            return handler(request.override(tool=calculate_tip))
        return handler(request)
    
agent = create_agent(
    model="gpt-4",
    tools=[get_weather],
    middleware=[DynamicToolMiddleware()],
)

result = agent.invoke({
    "messages":[{"role":"user","content":"What's the tip on a $50 bill?"}]
})

### System Prompt
"""System Prompt参数接收 str或SystemMessage类型，如果使用SystemMessage，可以使用Anthropic
的prompt caching功能。
"""

from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage

library_agent = create_agent(
    model="gpt-4",
    system_prompt=SystemMessage(
        content = [
            {
                "type":"text",
                "text": "you are a helpful assistant that can answer questions about a library."
            },
            {
                "type":"text",
                "text": "<the entire library of 'Pride and Prejudice'>",
                "cache_control": {"type":"ephemeral"}  #该字段告诉 Anthropic 缓存该消息，直到下一次调用。
            }
        ]
    )
)

result = library_agent.invoke(
    {"messages": [HumanMessage("analyze the major themes in 'pride and prejudice'.")]}
)

### dynamic system prompt
"""对于需要根据运行时上下文或代理状态修改系统提示词的高级用例，使用Mideeleware.
使用@dynamic_prompt装饰器创建中间件，该中间件根据模型请求生成系统提示。"""

from typing import TypedDict
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

class Context(TypedDict):
    user_role: str

@dynamic_prompt
def user_role_prompt(request:ModelRequest) -> str:
    """generate system prompt based on user role."""
    user_role = request.runtime.context.get("user_role","user")
    base_prompt = "You are a helpful assistant."

    if user_role == "expert":
        return f"{base_prompt} Provide detailed and technical explanations."
    elif user_role == "beginner":
        return f"{base_prompt} Explain concepts simply and avoid jargon."
    return base_prompt

agent = create_agent(
    model="gpt-4",
    tools=tools,
    middleware=[user_role_prompt],
    context_schema = Context,
)

result = agent.invoke(
    {"messages":[{"role":"user",
                  "content":"explain machine learning"}]},
    context={"user_role":"beginner"},
)

### invocation 调用
"""可以通过更新state来invoke agent，state包含一系列messages. 也可以使用一条messages去invoke agent。"""
result = agent.invoke(
     {"messages":[{"role":"user",
                   "content":"what's the weather like today?"}]}
)

###ProviderStrategy 
"""ProviderStrategy使用model procider的原生结构化输出生成功能。"""
from langchain.agents.structured_output import ProviderStrategy

agent = create_agent(
    model=model,
    response_format=ProviderStrategy(ContactInfo),
)

### ToolStrategy 工具策略
"""当ProviderStrategy无法满足需求时，使用ToolStrategy,来自定义结构化输出"""

from pydantic import BaseModel
from langchain.agents.structured_output import ToolStrategy

class ContactInfo(BaseModel):
    name:str
    email:str
    phone_number:str

agent = create_agent(
    model=model,
    tools=tools,
    response_format=ToolStrategy(ContactInfo),
)

result = agent.invoke(
    {"messages":[{"role":"user",
                  "content":"get me contact info for John Doe."}]}
)

result["structuredresponse"]

### Memory 
"""Agent通过message state来自动保存对话记录，也可以使用自定义方案来记住对话记录中的其他信息。
存储在state中的信息被视为“short-term memory”，而使用checkpointer保存的信息被视为“long-term memory”。
自定义state必须扩展AgentState作为TypedDict.
"""

#自定义state有俩种方法：1. 通过middleware（首选）。 2.通过create_agent上的state_schema。

#1. 通过middleware定义state

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware
from typing import Any

class CustomState(AgentState):
    user_preferences:dict

class CustomMiddleware(AgentMiddleware):
    state_schema = CustomAgentState
    tools = [tool1,tool2]

    def before_model(self,state:CustomState,runtime) -> dict[str,Any] | None:
        ...

agent = create_agent(
    model,
    tools=tools,
    middleware=[CustomMiddleware()],
)

result = agent.invoke({
    "messages":[{"role":"user",
                "content":"i prefer technical explanations."}]},
    "user_preferences":{"style":"technical","verbosity":"detailed"}
)

#2. 通过state_schema定义state

from langchain.agents import AgentState, create_agent

class CustomState(AgentState):
    user_preferences:dict

agent = create_agent(
    model,
    tools=[tool1,tool2],
    state_schema=CustomState,
)

result = agent.invoke(
    {
        "messages":[{
            "role":"user",
            "content":"i prefer technical explanations",
        }]
        "user_preferences":{"style":"technical","verbosity":"detailed"}
    }
)