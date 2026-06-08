import sys
import os
import re
import readline
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt

# Add current workspace directory to python path to avoid import resolution issues
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage, AIMessage
from graph import app
from tools.db_tools import get_all_plans
from tools.config_loader import load_config
from tools.logger import reset_log

reset_log()

console = Console()

def clean_response(text: str) -> str:
    """
    Strips out <think>...</think> tags and their contents from the generated output.
    Also handles unclosed <think> blocks gracefully.
    """
    if not text:
        return ""
    # Strip closed think tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Strip open/unclosed think tags
    if "<think>" in text:
        text = text.split("<think>")[0]
    return text.strip()

def print_banner():
    banner_text = Text()
    banner_text.append(" ⚡  PROJECT TaskMaker AI  ⚡ \n", style="bold magenta")
    banner_text.append("Multi-Agent AI Secretary for task management\n", style="italic cyan")
    banner_text.append("────────────────────────────────────────────────────────────\n", style="dim magenta")
    banner_text.append("Local vLLM: ", style="bold dim")
    banner_text.append(f"{load_config()['LLM_BASE_URL']}\n", style="bold green")
    banner_text.append("Memory Engine: ", style="bold dim")
    banner_text.append("ChromaDB (Embedded mode)\n", style="bold blue")
    banner_text.append("Available Commands:\n", style="bold dim")
    banner_text.append("  /tasks", style="bold yellow")
    banner_text.append(" - Show all plans in a formatted table\n", style="dim")
    banner_text.append("  /clear", style="bold yellow")
    banner_text.append(" - Clear console and show this header\n", style="dim")
    banner_text.append("  /exit ", style="bold yellow")
    banner_text.append(" - Terminate the terminal session\n", style="dim")
    
    console.print(Panel(banner_text, border_style="magenta", expand=False))

def show_tasks_table():
    try:
        plans = get_all_plans()
        if not plans:
            console.print("\n[bold yellow]⚠️  No tasks/plans found in the database.[/bold yellow]\n")
            return
            
        table = Table(title="📅 TaskMaker AI Memory - Active Plans", show_header=True, header_style="bold magenta", border_style="dim magenta")
        table.add_column("Plan ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="bold white")
        table.add_column("Description", style="white")
        table.add_column("Due Time", style="green")
        table.add_column("Status", style="bold yellow")
        
        for plan in plans:
            status = plan.get("status", "pending").lower()
            if status == "completed":
                status_str = f"[bold green]● {status}[/bold green]"
            elif status in ["in_progress", "in progress"]:
                status_str = f"[bold blue]● {status}[/bold blue]"
            else:
                status_str = f"[bold orange3]● {status}[/bold orange3]"
                
            table.add_row(
                plan.get("plan_id", "N/A"),
                plan.get("title", "N/A"),
                plan.get("description", "N/A"),
                plan.get("due_time", "N/A"),
                status_str
            )
        console.print("")
        console.print(table)
        console.print("")
    except Exception as e:
        console.print(f"[bold red]Error loading plans: {str(e)}[/bold red]")

def run_startup_checks():
    console.print("[bold magenta]🔍 Running TaskMaker AI Startup Checks...[/bold magenta]\n")
    
    # 1. Warm up ChromaDB and download embedding models
    with console.status("[bold cyan]Warming up ChromaDB and pre-loading embedding model...[/bold cyan]", spinner="dots"):
        try:
            from tools.db_tools import collection
            # Trigger lazy load of the embedding function by querying
            collection.query(query_texts=["warmup check"], n_results=1)
            console.print("[green]✓ ChromaDB memory engine & embedding models loaded successfully.[/green]")
        except Exception as e:
            console.print(f"[bold red]✗ Failed to initialize ChromaDB: {str(e)}[/bold red]")
            
    # 2. Check local LLM connectivity
    llm_url = load_config()["LLM_BASE_URL"]
    # Health check endpoint
    base_host = llm_url.split("/v1")[0]
    health_url = f"{base_host}/health"
    
    with console.status(f"[bold cyan]Checking local LLM connectivity at {llm_url}...[/bold cyan]", spinner="dots"):
        try:
            response = httpx.get(health_url, timeout=5.0)
            if response.status_code == 200:
                console.print(f"[green]✓ Local LLM connection verified (healthy).[/green]\n")
            else:
                # Try fallback models list
                resp_models = httpx.get(f"{llm_url}/models", timeout=5.0)
                if resp_models.status_code == 200:
                    console.print(f"[green]✓ Local LLM connection verified.[/green]\n")
                else:
                    console.print(f"[yellow]⚠ LLM endpoint returned status {response.status_code}. It might still work.[/yellow]\n")
        except Exception as e:
            console.print(f"[bold yellow]⚠ LLM endpoint unreachable: {str(e)}[/bold yellow]")
            console.print("[yellow]Please ensure your local vLLM server is running or SSH tunnel is active.[/yellow]\n")
            
    console.print("[bold green]Press Enter to launch TaskMaker AI console...[/bold green]")
    input()

def main():
    console.clear()
    run_startup_checks()
    console.clear()
    print_banner()
    
    chat_history = []
    
    while True:
        try:
            # Styled prompt
            user_input = Prompt.ask("[bold cyan]> User[/bold cyan]").strip()
            
            if not user_input:
                continue
                
            # Handle Commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/exit":
                    console.print("\n[bold magenta]Shutting down TaskMaker AI interface. Goodbye![/bold magenta] 👋\n")
                    break
                elif cmd == "/clear":
                    console.clear()
                    print_banner()
                    continue
                elif cmd == "/tasks":
                    show_tasks_table()
                    continue
                else:
                    console.print(f"[bold red]Unknown command: {user_input}. Type /tasks, /clear, or /exit.[/bold red]")
                    continue
            
            # Format and append user message
            chat_history.append(HumanMessage(content=user_input))
            old_history_len = len(chat_history)
            
            # Run the LangGraph agent network with a spinner
            with console.status("[bold magenta]TaskMaker AI is ruminating...[/bold magenta]", spinner="dots"):
                try:
                    response_state = app.invoke({
                        "messages": chat_history,
                        "task_payload": {},
                        "next_agent": "supervisor"
                    })
                    chat_history = response_state.get("messages", [])
                except Exception as e:
                    console.print(f"\n[bold red]Orchestration Error:[/bold red] {str(e)}\n")
                    # Remove the last message since it failed to process
                    chat_history.pop()
                    continue
            
            # Print new messages returned by the agent network
            for msg in chat_history[old_history_len:]:
                # Identify assistant / AI messages
                if msg.type == "ai" or getattr(msg, "role", "") == "assistant":
                    content = msg.content
                    
                    # Highlight system tool executions differently if desired
                    if content.startswith("[System"):
                        console.print(Panel(content, border_style="dim white", title="Database Log", title_align="left"))
                    else:
                        cleaned = clean_response(content)
                        if cleaned:
                            TaskMaker_header = Text("● TaskMaker AI", style="bold magenta")
                            console.print(TaskMaker_header)
                            console.print(f"{cleaned}\n")
                        
        except KeyboardInterrupt:
            console.print("\n[bold magenta]Session interrupted. Goodbye![/bold magenta] 👋\n")
            break
        except Exception as e:
            console.print(f"[bold red]Unexpected error: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()
