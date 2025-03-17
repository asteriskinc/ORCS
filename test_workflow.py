#!/usr/bin/env python3
"""
Simple test script for the workflow models
"""

from orcs.workflow.models import Task, TaskStatus, Workflow, WorkflowStatus

def test_task():
    """Test basic task functionality"""
    # Create a task
    task = Task(
        title="Test Task",
        description="This is a test task",
        agent_id="test_agent",
        id="task1"
    )
    
    # Check task properties
    assert task.id == "task1"
    assert task.title == "Test Task"
    assert task.description == "This is a test task"
    assert task.agent_id == "test_agent"
    assert task.status == TaskStatus.PENDING
    
    # Test task serialization
    task_dict = task.to_dict()
    assert task_dict["id"] == "task1"
    assert task_dict["title"] == "Test Task"
    assert task_dict["status"] == "pending"
    
    # Test task deserialization
    task2 = Task.from_dict(task_dict)
    assert task2.id == "task1"
    assert task2.title == "Test Task"
    assert task2.status == TaskStatus.PENDING
    
    print("Task tests passed!")

def test_workflow():
    """Test basic workflow functionality"""
    # Create a workflow
    workflow = Workflow(
        title="Test Workflow",
        description="This is a test workflow",
        query="Test query",
        id="workflow1"
    )
    
    # Check workflow properties
    assert workflow.id == "workflow1"
    assert workflow.title == "Test Workflow"
    assert workflow.description == "This is a test workflow"
    assert workflow.query == "Test query"
    assert workflow.status == WorkflowStatus.PLANNING
    
    # Add tasks to the workflow
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
        id="task2",
        dependencies=["task1"]
    )
    
    workflow.add_task(task1)
    workflow.add_task(task2)
    
    # Check tasks were added
    assert len(workflow.tasks) == 2
    assert workflow.get_task("task1") is task1
    assert workflow.get_task("task2") is task2
    
    # Test executable tasks
    executable_tasks = workflow.get_executable_tasks()
    assert len(executable_tasks) == 1
    assert executable_tasks[0].id == "task1"
    
    # Mark task1 as completed
    task1.status = TaskStatus.COMPLETED
    
    # Now task2 should be executable
    executable_tasks = workflow.get_executable_tasks()
    assert len(executable_tasks) == 1
    assert executable_tasks[0].id == "task2"
    
    # Test workflow serialization
    workflow_dict = workflow.to_dict()
    assert workflow_dict["id"] == "workflow1"
    assert workflow_dict["title"] == "Test Workflow"
    assert workflow_dict["status"] == "planning"
    assert len(workflow_dict["tasks"]) == 2
    
    # Test workflow deserialization
    workflow2 = Workflow.from_dict(workflow_dict)
    assert workflow2.id == "workflow1"
    assert workflow2.title == "Test Workflow"
    assert len(workflow2.tasks) == 2
    assert workflow2.get_task("task1").status == TaskStatus.COMPLETED
    
    print("Workflow tests passed!")

if __name__ == "__main__":
    test_task()
    test_workflow()
    print("All tests passed!") 