from langchain.tools import tool
from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage
from typing import Callable
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

class SkillMiddleware(AgentMiddleware):
    def process_request(self, request: ModelRequest) -> ModelRequest:
        # 在这里添加你的逻辑，根据请求的内容判断是否需要加载技能
        # 如果需要加载技能，则调用 load_skill 函数，并将结果添加到请求中
        # 如果不需要加载技能，则直接返回请求
        return request
@tool
def load_skill(skill_name: str) -> str:
    """load the full content of a skill into the agent's context.
    use this when you need detailed information about how to handle a specific
    type of request.This will provide you with comprehensive instructions,policies,
    and guidelines for the skill area.
    Args:
      skill_name(str, required): The name of the skill to load.
    """

    for skill in SKILLS:
        if skill["name"] == skill_name:
            return f"Loaded skill:{skill_name}\n\n{skill['content']}"
        
    available = ", ".join(s["name"] for s in SKILLS)
    return f"Skill '{skill_name}' not found.Available skills: {available}"

##构建 skill 中间件
class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the sysytem prompt."""
    tools = [load_skill]

    def __init__(self):
        """initialize and generate the skills prompt from SKILLS."""
        skill_list = []
        for skill in SKILLS:
            skill_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
            self.skills_prompt = "\n".join(skill_list)

    def wrap_model_call(
            self, 
            request: ModelRequest, 
            handler: Callable[[ModelRequest], ModelResponse]
        ) -> ModelResponse :
        """Sync: inject skill descriptions into system prompt."""

        skill_add = (
            f"\n\n##Avaliable Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information"
            "about handling a specific type of request."
        )

        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text":skill_add}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message = new_system_message)
        return handler(modified_request)
    
##create the agent with skill support
 agent = create_agent(
        model,
        system_prompt = (
            "you are a SQL query assistant that helps users write queries against business adtabases."
        ),
        middleware=[SkillMiddleware()],
        checkpointer=InMemorySaver(),
 )
