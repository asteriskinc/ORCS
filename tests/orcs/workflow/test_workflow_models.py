import pytest
from orcs.workflow.models import Task, TaskStatus, Workflow, WorkflowStatus


class TestTask:
    """Test suite for the Task class"""
    
    def test_task_initialization(self):
        """Test basic task initialization"""
        task = Task(
            title="Test Task",
            description="This is a test task",
            agent_id="test_agent"
        )
        
        assert task.title == "Test Task"
        assert task.description == "This is a test task"
        assert task.agent_id == "test_agent"
        assert task.id is not None  # Should have a generated ID
        assert task.dependencies == []  # Empty dependencies by default
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.metadata == {}
        
    def test_task_with_dependencies(self):
        """Test task with dependencies"""
        task = Task(
            title="Dependent Task",
            description="This task depends on others",
            agent_id="test_agent",
            dependencies=["task1", "task2"]
        )
        
        assert task.dependencies == ["task1", "task2"]
        
    def test_task_with_custom_id(self):
        """Test task with custom ID"""
        task = Task(
            title="Custom ID Task",
            description="This task has a custom ID",
            agent_id="test_agent",
            id="custom_id"
        )
        
        assert task.id == "custom_id"
        
    def test_task_to_dict(self):
        """Test task serialization to dictionary"""
        task = Task(
            title="Serialization Test",
            description="Testing to_dict method",
            agent_id="test_agent",
            id="test_id"
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["id"] == "test_id"
        assert task_dict["title"] == "Serialization Test"
        assert task_dict["description"] == "Testing to_dict method"
        assert task_dict["agent_id"] == "test_agent"
        assert task_dict["status"] == "pending"
        assert task_dict["dependencies"] == []
        assert task_dict["result"] is None
        
    def test_task_from_dict(self):
        """Test task deserialization from dictionary"""
        task_data = {
            "id": "task123",
            "title": "Deserialization Test",
            "description": "Testing from_dict method",
            "agent_id": "test_agent",
            "dependencies": ["dep1", "dep2"],
            "status": "running",
            "result": {"output": "Some result"},
            "created_at": "2023-01-01T00:00:00",
            "started_at": "2023-01-01T01:00:00",
            "metadata": {"priority": "high"}
        }
        
        task = Task.from_dict(task_data)
        
        assert task.id == "task123"
        assert task.title == "Deserialization Test"
        assert task.description == "Testing from_dict method"
        assert task.agent_id == "test_agent"
        assert task.dependencies == ["dep1", "dep2"]
        assert task.status == TaskStatus.RUNNING
        assert task.result == {"output": "Some result"}
        assert task.created_at == "2023-01-01T00:00:00"
        assert task.started_at == "2023-01-01T01:00:00"
        assert task.metadata == {"priority": "high"}


class TestWorkflow:
    """Test suite for the Workflow class"""
    
    def test_workflow_initialization(self):
        """Test basic workflow initialization"""
        workflow = Workflow(
            title="Test Workflow",
            description="This is a test workflow",
            query="Create a workflow for testing"
        )
        
        assert workflow.title == "Test Workflow"
        assert workflow.description == "This is a test workflow"
        assert workflow.query == "Create a workflow for testing"
        assert workflow.id is not None  # Should have a generated ID
        assert workflow.tasks == {}  # No tasks initially
        assert workflow.status == WorkflowStatus.PLANNING
        assert workflow.results == {}
        assert workflow.created_at is not None
        assert workflow.started_at is None
        assert workflow.completed_at is None
        assert workflow.metadata == {}
        
    def test_workflow_with_custom_id(self):
        """Test workflow with custom ID"""
        workflow = Workflow(
            title="Custom ID Workflow",
            description="This workflow has a custom ID",
            query="Test query",
            id="custom_workflow_id"
        )
        
        assert workflow.id == "custom_workflow_id"
        
    def test_add_task(self):
        """Test adding a task to a workflow"""
        workflow = Workflow(
            title="Task Addition Test",
            description="Testing task addition",
            query="Test query"
        )
        
        task = Task(
            title="Test Task",
            description="A task to add",
            agent_id="test_agent",
            id="task_id"
        )
        
        workflow.add_task(task)
        
        assert len(workflow.tasks) == 1
        assert "task_id" in workflow.tasks
        assert workflow.tasks["task_id"] is task
        
    def test_get_task(self):
        """Test retrieving a task from a workflow"""
        workflow = Workflow(
            title="Task Retrieval Test",
            description="Testing task retrieval",
            query="Test query"
        )
        
        task1 = Task(
            title="Task 1",
            description="First task",
            agent_id="test_agent",
            id="task1"
        )
        
        task2 = Task(
            title="Task 2",
            description="Second task",
            agent_id="test_agent",
            id="task2"
        )
        
        workflow.add_task(task1)
        workflow.add_task(task2)
        
        retrieved_task = workflow.get_task("task1")
        assert retrieved_task is task1
        
        # Test retrieving a non-existent task
        assert workflow.get_task("nonexistent") is None
        
    def test_get_executable_tasks(self):
        """Test getting executable tasks from a workflow"""
        workflow = Workflow(
            title="Executable Tasks Test",
            description="Testing executable tasks logic",
            query="Test query"
        )
        
        # Task with no dependencies
        task1 = Task(
            title="Task 1",
            description="No dependencies",
            agent_id="test_agent",
            id="task1"
        )
        
        # Task depending on task1
        task2 = Task(
            title="Task 2",
            description="Depends on task1",
            agent_id="test_agent",
            id="task2",
            dependencies=["task1"]
        )
        
        # Task depending on task1 and task2
        task3 = Task(
            title="Task 3",
            description="Depends on task1 and task2",
            agent_id="test_agent",
            id="task3",
            dependencies=["task1", "task2"]
        )
        
        workflow.add_task(task1)
        workflow.add_task(task2)
        workflow.add_task(task3)
        
        # Initially, only task1 should be executable
        executable = workflow.get_executable_tasks()
        assert len(executable) == 1
        assert executable[0].id == "task1"
        
        # Mark task1 as completed
        task1.status = TaskStatus.COMPLETED
        
        # Now task2 should be executable
        executable = workflow.get_executable_tasks()
        assert len(executable) == 1
        assert executable[0].id == "task2"
        
        # Mark task2 as completed
        task2.status = TaskStatus.COMPLETED
        
        # Now task3 should be executable
        executable = workflow.get_executable_tasks()
        assert len(executable) == 1
        assert executable[0].id == "task3"
        
    def test_workflow_to_dict(self):
        """Test workflow serialization to dictionary"""
        workflow = Workflow(
            title="Serialization Test",
            description="Testing to_dict method",
            query="Test query",
            id="workflow_id"
        )
        
        task = Task(
            title="Test Task",
            description="A test task",
            agent_id="test_agent",
            id="task_id"
        )
        
        workflow.add_task(task)
        workflow.results["task_id"] = {"output": "Task result"}
        
        workflow_dict = workflow.to_dict()
        
        assert workflow_dict["id"] == "workflow_id"
        assert workflow_dict["title"] == "Serialization Test"
        assert workflow_dict["description"] == "Testing to_dict method"
        assert workflow_dict["query"] == "Test query"
        assert workflow_dict["status"] == "planning"
        assert "task_id" in workflow_dict["tasks"]
        assert workflow_dict["results"] == {"task_id": {"output": "Task result"}}
        
    def test_workflow_from_dict(self):
        """Test workflow deserialization from dictionary"""
        task_data = {
            "id": "task_id",
            "title": "Test Task",
            "description": "A test task",
            "agent_id": "test_agent",
            "status": "completed"
        }
        
        workflow_data = {
            "id": "workflow_id",
            "title": "Deserialization Test",
            "description": "Testing from_dict method",
            "query": "Test query",
            "tasks": {"task_id": task_data},
            "status": "running",
            "results": {"task_id": {"output": "Task result"}},
            "created_at": "2023-01-01T00:00:00",
            "started_at": "2023-01-01T01:00:00",
            "metadata": {"priority": "high"}
        }
        
        workflow = Workflow.from_dict(workflow_data)
        
        assert workflow.id == "workflow_id"
        assert workflow.title == "Deserialization Test"
        assert workflow.description == "Testing from_dict method"
        assert workflow.query == "Test query"
        assert workflow.status == WorkflowStatus.RUNNING
        assert len(workflow.tasks) == 1
        assert "task_id" in workflow.tasks
        assert workflow.tasks["task_id"].title == "Test Task"
        assert workflow.tasks["task_id"].status == TaskStatus.COMPLETED
        assert workflow.results == {"task_id": {"output": "Task result"}}
        assert workflow.created_at == "2023-01-01T00:00:00"
        assert workflow.started_at == "2023-01-01T01:00:00"
        assert workflow.metadata == {"priority": "high"} 