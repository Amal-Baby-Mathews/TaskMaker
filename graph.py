from typing import TypedDict, Annotated, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# Import agent logics
from agents.supervisor import run_supervisor
from agents.execution import run_executor
from agents.retrieval import run_retriever
from agents.critic import run_critic
from agents.responder import run_responder

# Define AgentState with conversation history, routing key, temporary payload, and system rules context
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_agent: str
    task_payload: Dict[str, Any]
    system_rules: str

# Define individual node wrappers
def supervisor_node(state: AgentState) -> Dict[str, Any]:
    result = run_supervisor(state["messages"], state.get("system_rules", ""))
    return {
        "next_agent": result["next_agent"]
    }

def executor_node(state: AgentState) -> Dict[str, Any]:
    return run_executor(state)

def retriever_node(state: AgentState) -> Dict[str, Any]:
    return run_retriever(state)

def critic_node(state: AgentState) -> Dict[str, Any]:
    return run_critic(state)

def responder_node(state: AgentState) -> Dict[str, Any]:
    return run_responder(state)

from agents.rule_manager import run_rule_manager
def rule_manager_node(state: AgentState) -> Dict[str, Any]:
    return run_rule_manager(state)

# Define routing logic functions
def supervisor_router(state: AgentState) -> str:
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "executor":
        return "executor"
    elif next_agent == "retriever":
        return "retriever"
    elif next_agent == "responder":
        return "responder"
    elif next_agent == "rule_manager":
        return "rule_manager"
    else:
        return "END"

def executor_router(state: AgentState) -> str:
    next_agent = state.get("next_agent")
    if next_agent == "critic":
        return "critic"
    else:
        return "supervisor"

# Setup StateGraph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("executor", executor_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("critic", critic_node)
workflow.add_node("responder", responder_node)
workflow.add_node("rule_manager", rule_manager_node)

# Set Entry Edge
workflow.add_edge(START, "supervisor")

# Configure Supervisor Routing
workflow.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "executor": "executor",
        "retriever": "retriever",
        "responder": "responder",
        "rule_manager": "rule_manager",
        "END": END
    }
)

# Configure Executor Routing (routes to critic for validation, or back to supervisor upon action completion)
workflow.add_conditional_edges(
    "executor",
    executor_router,
    {
        "critic": "critic",
        "supervisor": "supervisor"
    }
)

# Unconditional Edges
workflow.add_edge("critic", "executor")
workflow.add_edge("retriever", "supervisor")
workflow.add_edge("responder", "supervisor")
workflow.add_edge("rule_manager", "supervisor")

# Compile graph
app = workflow.compile()
