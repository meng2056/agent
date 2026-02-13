#Message 包含Role,Content,Metadata

# Basic usage
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage,AIMessage,SystemMessage

# Initialize the chat model
chat_model = init_chat_model("gpt_3.5")

human_message = HumanMessage(content="Hello, how are you?")
system_message = SystemMessage(content="This is a system message.")
messages = [system_message, human_message]

# Generate a response
response = chat_model.generate(messages)
print(response)

## Text prompts
response = model.invoke("write a haiku about spring")
##Message prompts
from langchain.messages import HumanMessage, SystemMessage, AIMessage
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is the weather like?"),
    AIMessage(content="The weather is sunny.")
]
response = model.invoke(messages)
##Dictionary prompts
messages = [
    {"role":"system","content":"You are a helpful assistant."},
    {"role":"user","content":"What is the weather like?"},
    {"role":"assistant","content":"The weather is sunny."}
]
response = model.invoke(messages)