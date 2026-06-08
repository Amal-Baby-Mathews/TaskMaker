from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError, model_validator

class TaskItemSchema(BaseModel):
    action: str = Field(description="Action to perform: 'create', 'update', 'delete', or 'create_repeating'")
    plan_id: str = Field(description="Unique identifier of the plan")
    title: Optional[str] = Field(None, description="Title of the plan/task")
    description: Optional[str] = Field(None, description="Description of the plan/task")
    due_time: Optional[str] = Field(None, description="Due time, e.g., '17:00' or '2026-06-01 17:00'")
    status: Optional[str] = Field(None, description="Status: 'pending', 'in_progress', or 'completed'")
    frequency: Optional[str] = Field(None, description="Frequency of repeat: 'daily' or 'weekly'")
    repeat_count: Optional[int] = Field(None, description="Number of times to repeat the task")
    subtasks: Optional[Any] = Field(None, description="Optional subtasks list or serialized JSON string")

    @model_validator(mode="after")
    def validate_action_fields(self) -> 'TaskItemSchema':
        action = self.action
        if action == "create":
            if not self.title:
                raise ValueError("title is required for 'create' action")
            if not self.description:
                raise ValueError("description is required for 'create' action")
            if not self.due_time:
                raise ValueError("due_time is required for 'create' action")
        elif action == "create_repeating":
            if not self.title:
                raise ValueError("title is required for 'create_repeating' action")
            if not self.description:
                raise ValueError("description is required for 'create_repeating' action")
            if not self.due_time:
                raise ValueError("due_time is required for 'create_repeating' action")
            if not self.frequency:
                self.frequency = "daily"
            if not self.repeat_count:
                self.repeat_count = 7
        elif action == "update":
            # At least one field should be updated
            if not any([self.title, self.description, self.due_time, self.status, self.subtasks]):
                raise ValueError("At least one update field (title, description, due_time, status, subtasks) must be provided for 'update' action")
        elif action == "delete":
            pass # Only plan_id is required
        else:
            raise ValueError("action must be 'create', 'update', 'delete', or 'create_repeating'")
        return self

class TaskPayloadSchema(BaseModel):
    tasks: List[TaskItemSchema] = Field(description="List of task items to execute")

def sanitize_subtasks(subtasks: Any) -> Any:
    if not subtasks:
        return subtasks
    
    # If it is a JSON string, try to parse it
    if isinstance(subtasks, str):
        try:
            import json
            parsed = json.loads(subtasks)
            if isinstance(parsed, list):
                subtasks = parsed
        except Exception:
            return subtasks
            
    if isinstance(subtasks, list):
        sanitized = []
        for item in subtasks:
            if isinstance(item, dict):
                item_copy = dict(item)
                completed_val = item_copy.get("completed")
                if isinstance(completed_val, str):
                    lower_val = completed_val.lower().strip()
                    if lower_val in ("true", "1", "yes", "completed"):
                        item_copy["completed"] = True
                    elif lower_val in ("false", "0", "no", "pending"):
                        item_copy["completed"] = False
                elif completed_val is None:
                    item_copy["completed"] = False
                sanitized.append(item_copy)
            else:
                sanitized.append(item)
        return sanitized
    return subtasks

def run_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates task_payload schema containing a list of tasks.
    If valid, marks validated=True and routes to executor.
    If invalid, sets errors info and routes to executor for correction.
    """
    # Create a shallow copy of task_payload to avoid side effects
    task_payload = dict(state.get("task_payload", {}) or {})
    
    # Sanitize subtasks before validation
    if "tasks" in task_payload and isinstance(task_payload["tasks"], list):
        sanitized_tasks = []
        for task in task_payload["tasks"]:
            if isinstance(task, dict):
                task_copy = dict(task)
                if "subtasks" in task_copy:
                    task_copy["subtasks"] = sanitize_subtasks(task_copy["subtasks"])
                sanitized_tasks.append(task_copy)
            else:
                sanitized_tasks.append(task)
        task_payload["tasks"] = sanitized_tasks
    
    try:
        # Validate schema
        validated_data = TaskPayloadSchema(**task_payload)
        updated_payload = validated_data.model_dump()
        updated_payload["validated"] = True
        
        # Clear errors if any
        if "errors" in updated_payload:
            del updated_payload["errors"]
            
        return {
            "task_payload": updated_payload,
            "next_agent": "executor"
        }
    except ValidationError as e:
        # Gather error messages
        errors_list = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            errors_list.append(f"{loc}: {error['msg']}")
        
        updated_payload = dict(task_payload)
        updated_payload["validated"] = False
        updated_payload["errors"] = "; ".join(errors_list)
        
        return {
            "task_payload": updated_payload,
            "next_agent": "executor"
        }
