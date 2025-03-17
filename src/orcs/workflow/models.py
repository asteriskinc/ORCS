from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import logging

# Set up logger
logger = logging.getLogger("orcs.workflow.models")


class TaskStatus(Enum):
    """Status states for tasks"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(Enum):
    """Status states for workflows"""
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    """Represents a single unit of work in a workflow"""
    
    def __init__(self, 
                title: str, 
                description: str,
                agent_id: str,
                id: Optional[str] = None,
                dependencies: Optional[List[str]] = None):
        """Initialize a new task
        
        Args:
            title: Short descriptive title for the task
            description: Detailed description of what needs to be done
            agent_id: The ID of the agent that should handle this task
            id: Optional ID (generated if not provided)
            dependencies: List of task IDs that this task depends on
        """
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.agent_id = agent_id
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result = None
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.metadata: Dict[str, Any] = {}
        
        logger.info("Created task '%s' (ID: %s) for agent '%s'", title, self.id, agent_id)
        if dependencies:
            logger.debug("Task '%s' depends on tasks: %s", self.id, ', '.join(dependencies))
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation
        
        Returns:
            Dictionary representation of the task
        """
        logger.debug("Serializing task '%s' to dictionary", self.id)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "agent_id": self.agent_id,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a task from dictionary data
        
        Args:
            data: Dictionary containing task data
            
        Returns:
            A new Task instance
        """
        logger.debug("Deserializing task from dictionary (ID: %s)", data.get("id", "unknown"))
        task = cls(
            title=data["title"],
            description=data["description"],
            agent_id=data["agent_id"],
            id=data.get("id"),
            dependencies=data.get("dependencies", [])
        )
        
        # Set additional fields if they exist
        if "status" in data:
            task.status = TaskStatus(data["status"])
        if "result" in data:
            task.result = data["result"]
        if "created_at" in data:
            task.created_at = data["created_at"]
        if "started_at" in data:
            task.started_at = data["started_at"]
        if "completed_at" in data:
            task.completed_at = data["completed_at"]
        if "metadata" in data:
            task.metadata = data["metadata"]
            
        return task


class Workflow:
    """Represents a complete workflow with multiple tasks"""
    
    def __init__(self, 
                title: str,
                description: str,
                query: str,
                id: Optional[str] = None):
        """Initialize a new workflow
        
        Args:
            title: Short descriptive title for the workflow
            description: Detailed description of the workflow
            query: The original query that created this workflow
            id: Optional ID (generated if not provided)
        """
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.query = query
        self.tasks: Dict[str, Task] = {}  # Dict[task_id, Task]
        self.status = WorkflowStatus.PLANNING
        self.results: Dict[str, Any] = {}  # Dict[task_id, result]
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.metadata: Dict[str, Any] = {}
        
        logger.info("Created workflow '%s' (ID: %s) for query: '%s'", title, self.id, query)
    
    def add_task(self, task: Task) -> None:
        """Add a task to the workflow
        
        Args:
            task: The task to add
        """
        logger.info("Adding task '%s' (ID: %s) to workflow '%s'", task.title, task.id, self.id)
        self.tasks[task.id] = task
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID
        
        Args:
            task_id: The ID of the task to get
            
        Returns:
            The task if found, None otherwise
        """
        task = self.tasks.get(task_id)
        if task:
            logger.debug("Retrieved task '%s' from workflow '%s'", task_id, self.id)
        else:
            logger.warning("Task '%s' not found in workflow '%s'", task_id, self.id)
        return task
        
    def get_executable_tasks(self) -> List[Task]:
        """Get tasks that can be executed (dependencies satisfied)
        
        Returns:
            List of executable tasks
        """
        completed_tasks = {task_id for task_id, task in self.tasks.items() 
                          if task.status == TaskStatus.COMPLETED}
        
        executable = []
        for task_id, task in self.tasks.items():
            if (task.status == TaskStatus.PENDING and 
                all(dep in completed_tasks for dep in task.dependencies)):
                executable.append(task)
        
        logger.info("Found %d executable tasks in workflow '%s'", len(executable), self.id)
        if executable:
            logger.debug("Executable tasks: %s", ', '.join(task.id for task in executable))
                
        return executable
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary representation
        
        Returns:
            Dictionary representation of the workflow
        """
        logger.debug("Serializing workflow '%s' to dictionary", self.id)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "query": self.query,
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "status": self.status.value,
            "results": self.results,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create a workflow from dictionary data
        
        Args:
            data: Dictionary containing workflow data
            
        Returns:
            A new Workflow instance
        """
        logger.debug("Deserializing workflow from dictionary (ID: %s)", data.get("id", "unknown"))
        workflow = cls(
            title=data["title"],
            description=data["description"],
            query=data["query"],
            id=data.get("id")
        )
        
        # Set additional fields if they exist
        if "status" in data:
            workflow.status = WorkflowStatus(data["status"])
        if "results" in data:
            workflow.results = data["results"]
        if "created_at" in data:
            workflow.created_at = data["created_at"]
        if "started_at" in data:
            workflow.started_at = data["started_at"]
        if "completed_at" in data:
            workflow.completed_at = data["completed_at"]
        if "metadata" in data:
            workflow.metadata = data["metadata"]
            
        # Add tasks
        if "tasks" in data:
            logger.info("Loading %d tasks for workflow '%s'", len(data["tasks"]), workflow.id)
            for task_id, task_data in data["tasks"].items():
                task = Task.from_dict(task_data)
                workflow.add_task(task)
                
        return workflow 