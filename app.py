import os
import re
import json
import time
import calendar
import asyncio
from datetime import datetime, date
import pandas as pd
import streamlit as st

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from graph import app as graph_app
from tools.db_tools import (
    get_all_plans, update_plan, delete_plan,
    get_all_rules, add_rule, delete_rule, query_rules,
    save_chat_history, load_chat_history, clear_chat_history
)
from tools.config_loader import load_config
from tools.logger import reset_log

reset_log()

# Set up page configurations
st.set_page_config(
    page_title="TaskMaker AI Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom premium CSS styling for dark mode UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        justify-content: center;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-size: 16px;
        font-weight: 600;
        color: #888888;
        font-family: 'Space Grotesk', sans-serif;
    }

    .stTabs [aria-selected="true"] {
        color: #9D4EDD !important;
        border-bottom: 3px solid #9D4EDD !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper to clean reasoning think tags
def clean_response(text: str) -> str:
    """
    Strips out <think>...</think> tags and their contents from the generated output.
    """
    if not text:
        return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    if "<think>" in text:
        text = text.split("<think>")[0]
    return text.strip()

# Helper to parse dates from task objects
def parse_plan_date(plan: dict) -> date:
    due = plan.get("due_time", "")
    if not due:
        return None
    try:
        date_str = due.split("T")[0]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

# Header title banner (Emoji-free)
st.markdown("<h1 style='text-align: center; color: #9D4EDD; margin-bottom: 0px;'>PROJECT TaskMaker AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-style: italic; color: #8a8a8a; margin-top: 0px;'>Multi-Agent AI Secretary for task management</p>", unsafe_allow_html=True)
st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px; border-color: #333333;'>", unsafe_allow_html=True)

# Initialize Session State for Chat History and Calendar
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()

now = datetime.now()
if "cal_year" not in st.session_state:
    st.session_state.cal_year = now.year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = now.month

# Callbacks for Calendar navigation
def prev_month():
    if st.session_state.cal_month == 1:
        st.session_state.cal_month = 12
        st.session_state.cal_year -= 1
    else:
        st.session_state.cal_month -= 1

def next_month():
    if st.session_state.cal_month == 12:
        st.session_state.cal_month = 1
        st.session_state.cal_year += 1
    else:
        st.session_state.cal_month += 1

def set_today():
    st.session_state.cal_month = now.month
    st.session_state.cal_year = now.year

# Async event runner to track agent topology execution in real-time
async def run_graph_async(state: dict, topology_slot):
    def render_topology(highlighted_node=None):
        nodes = ["Supervisor", "Executor", "Critic", "Retrieval", "Responder", "RuleManager"]
        node_map = {
            "supervisor": "Supervisor",
            "executor": "Executor",
            "critic": "Critic",
            "retriever": "Retrieval",
            "responder": "Responder",
            "rule_manager": "RuleManager"
        }
        hl = node_map.get(highlighted_node) if highlighted_node else None
        
        # Build HTML for visual representation of topology
        html = "<div style='background-color:#1e1e1e; padding:15px; border-radius:10px; border:1px solid #333; margin-bottom: 20px;'>"
        html += "<h4 style='text-align:center; margin-top:0; color:#9D4EDD;'>Interactive Agent Topology Map</h4>"
        html += "<div style='display:flex; flex-direction:column; gap:8px; align-items:center;'>"
        
        for n in nodes:
            is_active = (n == hl)
            bg = "#9D4EDD" if is_active else "#2b2b2b"
            color = "#ffffff" if is_active else "#a0a0a0"
            border = "2px solid #D800C4" if is_active else "1px solid #444"
            shadow = "box-shadow: 0 0 12px #D800C4;" if is_active else ""
            status_lbl = " [ACTIVE]" if is_active else ""
            
            html += f"<div style='background-color:{bg}; color:{color}; border:{border}; {shadow} width:85%; padding:8px; border-radius:5px; text-align:center; font-size:14px; font-weight:bold;'>{n}{status_lbl}</div>"
            if n != nodes[-1]:
                html += "<div style='color:#555; font-size:12px;'>↓↑</div>"
                
        html += "</div></div>"
        topology_slot.markdown(html, unsafe_allow_html=True)

    # Initial render
    render_topology(None)
    async for event in graph_app.astream_events(state, version="v2"):
        event_type = event.get("event")
        event_name = event.get("name")
        
        valid_nodes = ["supervisor", "executor", "critic", "retriever", "responder", "rule_manager"]
        
        if event_type == "on_chain_start" and event_name in valid_nodes:
            render_topology(event_name)
            await asyncio.sleep(0.5)  # 500ms delay for visualization pacing
            
        elif event_type == "on_chain_end" and (event_name in valid_nodes or event_name == "LangGraph"):
            node_output = event.get("data", {}).get("output")
            if node_output and isinstance(node_output, dict):
                if "messages" in node_output:
                    state["messages"] = node_output["messages"]
                if "task_payload" in node_output:
                    state["task_payload"] = node_output["task_payload"]
                    
    # Render idle state when completed
    render_topology(None)
    return state

# Helper function to run async routine safely in sync Streamlit context
def execute_graph_with_events(state, topology_slot):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return loop.run_until_complete(run_graph_async(state, topology_slot))
    else:
        return asyncio.run(run_graph_async(state, topology_slot))

# Define Tabs
tab1, tab2, tab3 = st.tabs(["Chat Assistant", "Tasks Dashboard", "Instructions"])

# ----------------- Tab 1: Chat Assistant -----------------
with tab1:
    chat_col, map_col = st.columns([2, 1])
    
    with chat_col:
        st.markdown("### Chat with TaskMaker AI")
        st.markdown("Ask the AI to schedule plans, create recurring tasks, query reminders, or manage operational rules.")

        if st.button("Delete Chat History", key="delete_chat_btn"):
            clear_chat_history()
            st.session_state.chat_history = []
            st.success("Chat history deleted.")
            st.rerun()

        # Render past chat messages
        for msg in st.session_state.chat_history:
            if msg.type == "human":
                with st.chat_message("user"):
                    st.markdown(msg.content)
            elif msg.type == "ai":
                cleaned_history_content = clean_response(msg.content)
                if cleaned_history_content and not cleaned_history_content.startswith("[System"):
                    with st.chat_message("assistant"):
                        st.markdown(cleaned_history_content)

        # Chat input field
        prompt = st.chat_input("Enter your request here...")

    with map_col:
        topology_slot = st.empty()
        
        # Render default idle topology map
        nodes_list = ["Supervisor", "Executor", "Critic", "Retrieval", "Responder", "RuleManager"]
        default_html = "<div style='background-color:#1e1e1e; padding:15px; border-radius:10px; border:1px solid #333; margin-bottom: 20px;'>"
        default_html += "<h4 style='text-align:center; margin-top:0; color:#9D4EDD;'>Interactive Agent Topology Map</h4>"
        default_html += "<div style='display:flex; flex-direction:column; gap:8px; align-items:center;'>"
        for n in nodes_list:
            default_html += f"<div style='background-color:#2b2b2b; color:#a0a0a0; border:1px solid #444; width:85%; padding:8px; border-radius:5px; text-align:center; font-size:14px; font-weight:bold;'>{n}</div>"
            if n != nodes_list[-1]:
                default_html += "<div style='color:#555; font-size:12px;'>↓↑</div>"
        default_html += "</div></div>"
        topology_slot.markdown(default_html, unsafe_allow_html=True)

    if prompt:
        with chat_col:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        st.session_state.chat_history.append(HumanMessage(content=prompt))

        # Retrieve relevant system rules semantically to inject into graph state
        relevant_rules = query_rules(prompt, limit=5)
        system_rules_str = ""
        if relevant_rules:
            system_rules_str = "\n".join([f"- {r['content']}" for r in relevant_rules])

        state = {
            "messages": st.session_state.chat_history,
            "task_payload": {},
            "next_agent": "supervisor",
            "system_rules": system_rules_str
        }

        # Run LangGraph with active real-time topology map updates
        final_state = execute_graph_with_events(state, topology_slot)
        st.session_state.chat_history = final_state["messages"]
        save_chat_history(st.session_state.chat_history)

        if st.session_state.chat_history and st.session_state.chat_history[-1].type == "ai":
            final_resp = st.session_state.chat_history[-1].content
        else:
            final_resp = "I have completed processing your request."

        cleaned_resp = clean_response(final_resp)
        
        with chat_col:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                displayed_text = ""
                for char in cleaned_resp:
                    displayed_text += char
                    placeholder.markdown(displayed_text + "▌")
                    time.sleep(0.005)
                placeholder.markdown(displayed_text)

        st.rerun()

# ----------------- Tab 2: Tasks Dashboard -----------------
with tab2:
    st.markdown("### Active Tasks Board")
    st.markdown("Verify scheduled items and modify tasks directly within the monthly calendar view.")

    # Fetch database entries
    try:
        plans = get_all_plans()
    except Exception as e:
        st.error(f"Could not connect to ChromaDB: {str(e)}")
        plans = []

    # Calendar Navigation Header
    st.markdown("<br>", unsafe_allow_html=True)
    c_prev, c_center, c_next = st.columns([1, 2, 1])
    
    with c_prev:
        st.button("Previous Month", on_click=prev_month, use_container_width=True, key="btn_prev_month")
    with c_center:
        month_name = calendar.month_name[st.session_state.cal_month]
        st.markdown(f"<h3 style='text-align: center; margin: 0px;'>{month_name} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with c_next:
        st.button("Next Month", on_click=next_month, use_container_width=True, key="btn_next_month")
        
    st.markdown("<br>", unsafe_allow_html=True)

    # Weekdays Headers
    weekday_cols = st.columns(7)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for col, wday in zip(weekday_cols, weekdays):
        col.markdown(f"<p style='text-align: center; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #555;'>{wday}</p>", unsafe_allow_html=True)

    # Monthly Grid Weeks calculation
    cal_weeks = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    
    for week_idx, week in enumerate(cal_weeks):
        cols = st.columns(7)
        for day_idx, day in enumerate(week):
            if day == 0:
                cols[day_idx].markdown("")
            else:
                with cols[day_idx]:
                    st.markdown(f"<div style='font-size: 14px; font-weight: 800; color: #9D4EDD; border-bottom: 1px solid #333; padding-bottom: 2px; margin-bottom: 5px;'>{day}</div>", unsafe_allow_html=True)
                    
                    # Filter tasks matching this date
                    cell_date = date(st.session_state.cal_year, st.session_state.cal_month, day)
                    day_plans = [p for p in plans if parse_plan_date(p) == cell_date]
                    
                    for plan in day_plans:
                        pid = plan.get("plan_id", "N/A")
                        title = plan.get("title", "No Title")
                        status = plan.get("status", "pending")
                        label_status = f"[{status.upper()}]"
                        
                        # Expandable task card
                        with st.expander(f"{label_status} {title}", expanded=False):
                            st.write(f"ID: {pid}")
                            
                            # Inline Alteration Fields
                            new_title = st.text_input("Title", value=title, key=f"t_val_{pid}_{week_idx}_{day_idx}")
                            new_desc = st.text_area("Description", value=plan.get("description", ""), key=f"d_val_{pid}_{week_idx}_{day_idx}")
                            new_status = st.selectbox(
                                "Status", 
                                ["pending", "in_progress", "completed"], 
                                index=["pending", "in_progress", "completed"].index(status.lower()), 
                                key=f"s_val_{pid}_{week_idx}_{day_idx}"
                            )
                            
                            btn1, btn2 = st.columns(2)
                            with btn1:
                                if st.button("Save", key=f"save_act_{pid}", use_container_width=True):
                                    try:
                                        update_plan(plan_id=pid, title=new_title, description=new_desc, status=new_status)
                                        st.success("Saved")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as db_err:
                                        st.error(str(db_err))
                            with btn2:
                                if st.button("Delete", key=f"del_act_{pid}", use_container_width=True):
                                    try:
                                        delete_plan(plan_id=pid)
                                        st.success("Deleted")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as db_err:
                                        st.error(str(db_err))

    # Fallback/Inbox list for tasks without valid date or out of the current month view
    st.markdown("<br><hr style='border-color: #333;'>", unsafe_allow_html=True)
    st.markdown("#### Inbox and Out-of-Range Tasks")
    
    unscheduled_plans = []
    for plan in plans:
        p_date = parse_plan_date(plan)
        if p_date is None:
            unscheduled_plans.append(plan)
        elif p_date.year != st.session_state.cal_year or p_date.month != st.session_state.cal_month:
            unscheduled_plans.append(plan)
            
    if not unscheduled_plans:
        st.info("No unscheduled or out-of-range tasks.")
    else:
        for plan in unscheduled_plans:
            pid = plan.get("plan_id", "N/A")
            title = plan.get("title", "No Title")
            desc = plan.get("description", "")
            due = plan.get("due_time", "")
            status = plan.get("status", "pending")
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([5, 2, 3])
                with col1:
                    st.markdown(f"##### [{status.upper()}] {title} `({pid})`")
                    st.write(f"Description: {desc}")
                    st.write(f"Due Time: {due}")
                with col2:
                    new_status = st.selectbox(
                        "Status", 
                        ["pending", "in_progress", "completed"], 
                        index=["pending", "in_progress", "completed"].index(status.lower()), 
                        key=f"inbox_s_{pid}"
                    )
                    if new_status != status:
                        update_plan(plan_id=pid, status=new_status)
                        st.rerun()
                with col3:
                    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"inbox_del_{pid}", use_container_width=True):
                        delete_plan(plan_id=pid)
                        st.rerun()

# ----------------- Tab 3: Instructions -----------------
with tab3:
    st.markdown("### Operational Instructions & Preferences")
    st.markdown("Add or remove dynamic rules guiding system behavior and agent planning.")
    
    # Form to add a new operational rule
    with st.container(border=True):
        st.markdown("##### Add New Operational Instruction")
        r_col1, r_col2 = st.columns([1, 3])
        with r_col1:
            new_rule_id = st.text_input("Rule ID (e.g. rule_001)", value="", placeholder="Leave blank to auto-generate")
        with r_col2:
            new_rule_content = st.text_input("Rule Content", value="", placeholder="e.g. Always schedule meetings in the afternoon")
            
        if st.button("Add Instruction", use_container_width=True):
            if not new_rule_content.strip():
                st.error("Rule content cannot be empty.")
            else:
                assigned_id = new_rule_id.strip() if new_rule_id.strip() else "rule_001"
                try:
                    added_id = add_rule(rule_id=assigned_id, content=new_rule_content.strip())
                    st.success(f"Added instruction (ID: {added_id})")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as ex:
                    st.error(str(ex))
                    
    # List active system rules from ChromaDB
    st.markdown("<br>##### Active System Rules", unsafe_allow_html=True)
    try:
        active_rules = get_all_rules()
    except Exception as ex:
        st.error(f"Could not retrieve rules from ChromaDB: {str(ex)}")
        active_rules = []
        
    if not active_rules:
        st.info("No active system rules or instructions.")
    else:
        for rule in active_rules:
            rid = rule.get("rule_id", "N/A")
            rcontent = rule.get("content", "")
            
            with st.container(border=True):
                col_r1, col_r2 = st.columns([5, 1])
                with col_r1:
                    st.markdown(f"**ID:** `{rid}`")
                    st.write(rcontent)
                with col_r2:
                    st.markdown("<div style='margin-top:5px;'></div>", unsafe_allow_html=True)
                    if st.button("Delete", key=f"del_rule_btn_{rid}", use_container_width=True):
                        try:
                            delete_rule(rule_id=rid)
                            st.success("Deleted")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as ex:
                            st.error(str(ex))
