from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3

# ------------ Chat Model ----------------#
load_dotenv()
llm = ChatOpenAI(model='gpt-4o-mini')

# ------------ Chat State ----------------# 
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ------------- Nodes method ---------------#
def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

# ------------- Checkpointer ---------------#
connection = sqlite3.connect('chatbot.db',check_same_thread=False)
checkpointer = SqliteSaver(conn=connection)

# ------------- Define graph ----------------#
graph = StateGraph(ChatState)

# -------------- Define nodes ---------------#
graph.add_node("chat_node", chat_node)

# -------------- Define edges ---------------#
graph.add_edge(START, "chat_node")
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
def get_all_threads():
    all_threads = set()
    for saver in checkpointer.list(None):
        all_threads.add(saver.config['configurable']['thread_id'])
    return list(all_threads)
