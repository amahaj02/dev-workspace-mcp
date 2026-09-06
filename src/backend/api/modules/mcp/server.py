from typing import Any
import json
from mcp.server import MCPServer
from pathlib import Path
import logging
import uuid

# Initialize MCPServer
mcp = MCPServer("project-dev-workspace-mcp")
JsonObject = dict[str, Any]
Task = JsonObject
CompleteTaskResult = Task | dict[str, str]

# Constants
WORKSPACE = Path(__file__).parent / "workspace"

TASKS = WORKSPACE / "tasks.json"
PROJECTS = WORKSPACE / "projects.json"
NOTES = WORKSPACE / "notes.md"
SEARCHABLE_FILES = (NOTES, TASKS, PROJECTS)

# Setup logger
logger = logging.getLogger(__name__)


# Helpers
def read_json_file(file_path: str) -> list[JsonObject]:
    """Read and parse data from a JSON file.

    Args:
        file_path (str): The system path to the target JSON file.

    Returns:
        A list of JSON objects parsed from the file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON syntax.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            # json.load parses an open file object directly
            return json.load(file)
    except FileNotFoundError:
        logger.exception(f"Error: The file at {file_path} was not found.")
        raise
    except json.JSONDecodeError:
        logger.exception(f"Error: The file at {file_path} contains invalid JSON.")
        raise


# Tool 1: create_task
@mcp.tool()
async def create_task(title: str, project: str, priority: str = "medium"):
    """
    Appends a task to tasks.json and returns a created task ID + summary
    Args:
        title: title for the new task
        project: the project that the new task will be a part of
        priority: priority of the task to be added, default is medium
    Returns:
        task ID + summary
    """
    data = read_json_file(TASKS)

    new_task = {
        "id": str(uuid.uuid4()),
        "title": title,
        "project": project,
        "priority": priority,
        "completed": False,
    }

    data.append(new_task)

    with open(TASKS, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return new_task


# Tool 2: complete_task
@mcp.tool()
async def complete_task(task_id: str) -> CompleteTaskResult:
    """
    Marks a task as completed
    Args:
        task_id: string-based ID for the task to be marked as completed
    Returns:
        The updated task, or a message if it was already completed.
    Raises:
        TaskNotFound error: if the task is not found
    """
    data = read_json_file(TASKS)
    for task in data:
        if task["id"] != task_id:
            continue
        if task["completed"]:
            return {"message": "task is already completed"}
        task["completed"] = True
        with open(TASKS, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        return task
    raise ValueError(f"Task `{task_id}` not found")


# Tool 3: search_workspace
@mcp.tool()
async def search_workspace(query: str) -> list[dict[str, str]]:
    """Search workspace files for a case-insensitive substring.

    Args:
        query: Text to search for in notes.md, tasks.json, and projects.json.

    Returns:
        A list of matching lines, including the source file name.
    """
    query = query.strip()
    if not query:
        return []

    query_lower = query.casefold()
    matches: list[dict[str, str]] = []

    for file_path in SEARCHABLE_FILES:
        if not file_path.exists():
            continue

        for line in file_path.read_text(encoding="utf-8").splitlines():
            if query_lower in line.casefold():
                matches.append(
                    {
                        "source": file_path.name,
                        "content": line.strip(),
                    }
                )

    return matches


# Resource 1: workspace://tasks -> returns all tasks
@mcp.resource(
    "workspace://tasks",
    name="All tasks",
    description="Returns all workspace tasks",
    mime_type="application/json",
)
async def get_tasks() -> str:
    return TASKS.read_text(encoding="utf-8")


# Resource 2: workspace://projects/mcp-learning -> returns the matching project object
@mcp.resource(
    "workspace://projects/{project_id}",
    name="Project details",
    description="Returns details for one project",
    mime_type="application/json",
)
async def get_project(project_id: str) -> str:
    projects = read_json_file(PROJECTS)
    for project in projects:
        if project["id"] == project_id:
            return json.dumps(project, indent=2)
    return json.dumps({"error": f"Project `{project_id} not found"})
