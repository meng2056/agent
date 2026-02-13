from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from fastmcp import FastMCP

mcp = FastMCP("Math","weather")

@mcp.tool()
def add(a:int,b:int) -> int:
    "Add two numbers"
    return a+b

@mcp.tool()
def multiply(a:int,b:int) -> int:
    "Multiply two numbers"
    return a*b

@mcp.tool()
async def get_weather(location:str) -> str:
    "get weather for location"
    return "it's always sunny in new york"
# if __name__ == "__main__":
#     mcp.run(transport="stdio")



client = MultiServerMCPClient(
    {
        "math":{
            "transport":"stdio",
            "command":"python",
            "args":["/path/to/math_server.py"],
        },
        "weather":{
            "transport":"http",
            "url":"http://localhost:5000"
        }
    }
)
# tools = await client.get_tools()
tools = client.get_tools()
agent = create_agent(
    model = "DEEPSEEK",
    tools = tools,
)
math_response =  agent.ainvoke({
    "messages":[{
        "role":"user",
        "content":"What's the tip on a $50 bill?"
    }]
})