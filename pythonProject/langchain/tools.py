#tool 高级模式定义
from pydantic import BaseModel, Field
from typing import Literal

class WeatherInput(BaseModel):
    """Input for weather queries."""
    location:str = Field(description="city name")
    units:Literal["metric", "imperial"] = Field(
        default="metric",
        description="metric or imperial")
    include_forecast:bool = Field(
        default = False,
        description="include forecast or not"
    )

@tool(args_schema=WeatherInput)
def get_weather(location:str, units:str = "metric", include_forecast: bool = False) -> str:
    """Get weather information for a given location."""
    pass

#accessing context:tool可以通过ToolRuntime参数访问运行时信息。
#State,Context,Store,Stream Writer, Config, Tool Call ID

#ToolRuntime--accessing state
from langchain.tools import tool, ToolRuntime

@tool
def summarize_conversation(
    runtime: ToolRuntime
) -> str:
    """summarize the conversation so far"""
    messages = runtime.state["messages"]

    human_msgs = sum(1 for m in messages if m.__class__.__name__=="HumanMessage")
    ai_msgs = sum(1 for m in messages if m.__class__.__name__=="AIMessage")
    return f"Conversation so far: {human_msgs} human messages, {ai_msgs} AI messages."
@tool
def get_user_preference(
    pref_name: str,
    runtime: ToolRuntime
) -> str:
    """Get user preference from the context"""
    preference = runtime.state.get("user_preferences",{})
    return preference.get(pref_name,"Not set")

##使用Command去更新agent的state或控制图的执行流程

from langgraph.types import Command
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain.tools import tool, ToolRuntime

#update the conversation history by removing all messages
@tool
def clean_conversation():
    """clean the conversation history"""
    return Command(
        update={
            "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]
        }
    )

#update the user_name in the agent state
@tool
def update_user_name(
    new_name:str,
    runtime: ToolRuntime
) -> Command:
    """update the user_name in the agent state"""
    return Command(
        update={
            "user_name": new_name
        }
    )


###Short-term memory
#启用short-term memory后，长时间的对话可能会超过LLM的上下文窗口，创建的方式有以下四种：
##1.Trim messages：统计消息历史
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from typing import Any

@before_model
def trim_messages(
    state: AgentState,
    runtime: Runtime
) ->dict[str,Any] | None:
    """Keep only the last few messages to fit context windown"""
    
    messages = state["messages"]

    if len(messages) <= 5:
        return None
    else:
        first_message = messages[0]
        recent_messages = messages[-3:] if len(messages)%2 == 0 else messages[-4:]
        new_messages = [first_message]+ recent_messages
        return{
            "messages":[
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *new_messages
            ]
        }
    
agent = create_agent(
    model="gpt-4",
    tools=[get_weather],
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)
config:RunnableConfig = {"configurable":{"thread_id":"1"}}
agent.invoke({"messages":[{"role":"user","content":"What's the tip on a $50 bill?"}]},config=config})

##2delete messages
from langchain.messages import RemoveMessage
#删除前2条message
def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 23:
        return {"messages": [RemoveMessage(id = m.id) for m in messages[:2]]}
    
#删除全部message
def deleate_messages(state):
    return {"messages": [RemoveMessage(id = REMOVE_ALL_MESSAGES)]}

##streaming流式输出
#stream_mode = "updates"
from langchain.agents import create_agent
@tool
def get_weather(location:str, units:str = "metric", include_forecast: bool = False) -> str:
    """Get weather information for a given location."""
    pass

agent = create_agent(
    model="gpt-4",
    tools=[get_weather],
    )

for chunk in agent.stream(
    {"messages":[{
        "role":"user",
        "content":"What's the weather like in San Francisco?"
    }]},
    stream_mode="updates",
):
    for step, data in chunk.items():
        print(f"step:{step}")
        print(f"content:{data['messages'][-1].content_blocks}")

##stream_model="messages"



##structuured output
#provider stratedy
from pydantic import BaseModel, Field
from langchain.agents import create_agent

class ContactInfo(BaseModel):
    """Contact information for the user"""
    name:str = Field(description="The name of the user")
    email:str = Field(description = "The email address of the user")
    phone:str = Field(description="The phone number of the user")

agent = create_agent(
    model="gpt-3.5-turbo," \
    "response_format"=ContactInfo,
)
result = agent.invoke({
    "messages":[{
        "role":"user",
        "content":"Please provide me with my contact information"
    }]
    })
print(result['structured_responsed'])

#Toolstrategy
from pydantic import BaseModel,Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

class ProductReview(BaseModel):
    """Analysis of a product review"""
    rating:int | None = Field(description="The rating of the product")
    sentiment:Literal["positive","negative"] = Field(description="The sentiment of the product review")
    review:list[str] = Field(description="The actual review text")

agent = create_agent(
    model="gpt",
    tools=tool,
    response_format=ToolStrategy(ProductReview),
)
result = agent.invoke({
    "messages":[{
        "role":"user",
        "content":"please analyze the sentiment of the following product review:"
    }]
})
print(result["structured_response"])

##guardrails(护栏)
#build_in guardrails
#PII detection
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
agent = create_agent(
    model="gpt",
    tools = tool,
    middleware = [
        PIIMiddleware(
            "email",
            strategy = "redact",
            apply_to_input = True,
        ),
        PIIMiddleware(
            "phone number",
            strategy = "mask",
            apply_to_input = True,
        ),
        PIIMiddleware(
            "api_key",
            strategy = "block",
            detector=r"sk-[a-zA-Z0-9]{32}",
            apply_to_input=Ture,
        )
    ]
)
result = agent.invoke({
    "messages":[{
        "role":"user",
        "content": "What is my name?"
    }]
})

##human-in-the-loop
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

agent = create_agent(
    model="gpt",
    tools = tools,
    middleware = [
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email":True,
                "delete_database":True,
                "search":False,
            }
        )
    ],
    checkpointer=InMemorySaver(),
)

config = {"configurable":{"thread_id":"1"}}
result = agent.invoke({
    "messages":[{
        "role":"user",
        "content":"Please send an email to my friend",
    }],
    #
})

#context engineering
##dynamic prompt
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dynamic_prompt
def dynamic_prompt(request:ModelRequest) -> str:
    """Generate dynamic prompt based on conversation history."""
    message_count = len(request.messages)
    base = "you are a helpful assistant"
    if message_count > 5:
        base += "\nThis is a long conversation."
    return base
agent = create_agent(
    model = "gpt",
    tools = tool,
    middleware = [dynamic_prompt]
)

from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dataclass 
class Context:
    user_id: str

@dynamic_prompt
def store_aware_prompt(request:ModelRequest) -> str:
    user_id = request.runtime.context.user_id
    store = request.runtime.store
    user_prefs = store.get(("preferences",) user_id")
    base = "you are a helpful assistant"
    if user_prefs:
        style = user_prefs.value.get("communcation_style","balanced")
        base += f"\n User prefers {style} responses."
    return base 

agent = create_agent(
    model = "gpt",
    tools = tool,
    middleware = [store_aware_prompt],
    context_schema = Context,
    store = InMemoryStore(),
)