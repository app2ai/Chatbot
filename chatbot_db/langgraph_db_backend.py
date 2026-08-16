from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph_tools import ChatTools as ct
from langchain_core.tools import BaseTool
import aiosqlite
import asyncio
import threading
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

load_dotenv()

# ----- Dedicated async loop for backend tasks ------#
_ASYNC_LOOP = asyncio.new_event_loop()
_ASYNC_THREAD = threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True)
_ASYNC_THREAD.start()

def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


def run_async(coro):
    return _submit_async(coro).result()


def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)

# ------------ Chat Model ----------------#
llm = ChatOpenAI(model='gpt-4')

# ----------- MCP ----------------------#
client = MultiServerMCPClient({
        "math-mcp-server": {
        "transport": "stdio",
        "command": "D:\\mcp servers\\math-mcp-server\\venv\\Scripts\\python.exe",
        "args": ["D:\\mcp servers\\math-mcp-server\\main.py"]
    },
    "remote-expense-mcp": {
        "transport": "streamable_http",
        "url": "https://uncertain-jade-crab.fastmcp.app/mcp"
    }
})

def load_mcp_tools() -> list[BaseTool]:
    try:
        return run_async(client.get_tools())
    except Exception:
        return []

mcp_tools = load_mcp_tools()

# ----------- Tools ---------------------#
tools = [ct.search_tool, ct.currency_exchange]

llm_with_tools = llm.bind_tools(tools=tools) if tools else llm

# ------------ Chat State ----------------# 
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ------------- Nodes method ---------------#
async def chat_node(state: ChatState):
    messages = state['messages']
    response = await llm_with_tools.invoke(messages)
    return {"messages": [response]}

tools_node = ToolNode(tools) if tools else None

# ------------- Checkpointer ---------------#
async def _init_checkpointer():
    connection = await aiosqlite.connect(database="chatbot.db")
    return AsyncSqliteSaver(connection)

checkpointer = run_async(_init_checkpointer())

# ------------- Define graph ----------------#
graph = StateGraph(ChatState)

# -------------- Define nodes ---------------#
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")

if tools_node:
    graph.add_node("tools", tools_node)
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
else:
    graph.add_edge("chat_node", END)

# --------------- Compile graph -------------#
chatbot_db = graph.compile(checkpointer=checkpointer)

# --------------- Invoke message ------------#
# res = chatbot_db.invoke(
#     input= {'messages': [HumanMessage(content="What is Worm whole, in 1 sentence?")]},
#     config= {'configurable': {'thread_id':'11'}}
# )

# print(res)


# ------------ Get all threads from DB -------#
async def _alist_threads():
    all_threads = set()
    async for checkpoint in checkpointer.alist(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def retrieve_all_threads():
    return run_async(_alist_threads())
