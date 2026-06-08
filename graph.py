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
from agents.planner import run_planner

# Define AgentState with conversation history, routing key, temporary payload, and system rules context
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_agent: str
    task_payload: Dict[str, Any]
    system_rules: str

from tools.logger import log_node_start, log_node_end

# Define individual node wrappers
def supervisor_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("supervisor", state)
    result = run_supervisor(state["messages"], state.get("system_rules", ""))
    output = {
        "next_agent": result["next_agent"]
    }
    log_node_end("supervisor", output)
    return output

def executor_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("executor", state)
    output = run_executor(state)
    log_node_end("executor", output)
    return output

def retriever_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("retriever", state)
    output = run_retriever(state)
    log_node_end("retriever", output)
    return output

def critic_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("critic", state)
    output = run_critic(state)
    log_node_end("critic", output)
    return output

def responder_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("responder", state)
    output = run_responder(state)
    log_node_end("responder", output)
    return output

def planner_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("planner", state)
    output = run_planner(state)
    log_node_end("planner", output)
    return output

from agents.rule_manager import run_rule_manager
def rule_manager_node(state: AgentState) -> Dict[str, Any]:
    log_node_start("rule_manager", state)
    output = run_rule_manager(state)
    log_node_end("rule_manager", output)
    return output

# Define routing logic functions
def supervisor_router(state: AgentState) -> str:
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "executor":
        return "executor"
    elif next_agent == "planner":
        return "planner"
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
workflow.add_node("planner", planner_node)

# Set Entry Edge
workflow.add_edge(START, "supervisor")

# Configure Supervisor Routing
workflow.add_conditional_edges(
    "supervisor",
    supervisor_router,
    {
        "executor": "executor",
        "planner": "planner",
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
workflow.add_edge("planner", "critic")
workflow.add_edge("critic", "executor")
workflow.add_edge("retriever", "supervisor")
workflow.add_edge("responder", "supervisor")
workflow.add_edge("rule_manager", "supervisor")

# Compile graph
app = workflow.compile()
