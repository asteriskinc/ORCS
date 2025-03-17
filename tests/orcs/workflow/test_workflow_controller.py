import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from orcs.workflow.controller import WorkflowController
from orcs.workflow.models import Workflow, Task, WorkflowStatus
from orcs.memory.system import MemorySystem, AgentContext


class MockAgent:
    """Mock implementation of an agent for testing"""
    
    def __init__(self, return_value=None):
        self.execute = AsyncMock(return_value=return_value or {})
        

class TestWorkflowController:
    """Test suite for the WorkflowController"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.memory = MemorySystem()
        
        # Create a mock planner agent that returns predefined tasks
        self.planner_return_value = {
            "tasks": [
                {
                    "title": "Task 1",
                    "description": "Description for task 1",
                    "agent_id": "research_agent",
                    "dependencies": []
                },
                {
                    "title": "Task 2",
                    "description": "Description for task 2",
                    "agent_id": "writing_agent",
                    "dependencies": [0]  # Depends on Task 1
                },
                {
                    "title": "Task 3",
                    "description": "Description for task 3",
                    "agent_id": "coding_agent",
                    "dependencies": [0, 1]  # Depends on Task 1 and Task 2
                }
            ]
        }
        
        self.planner_agent = MockAgent(self.planner_return_value)
        self.controller = WorkflowController(
            planner_agent=self.planner_agent,
            memory_system=self.memory
        )
    
    @pytest.mark.asyncio
    async def test_create_workflow(self):
        """Test creating a new workflow"""
        query = "Create a workflow for testing"
        workflow_id = await self.controller.create_workflow(query)
        
        # Check that a workflow was created
        assert workflow_id in self.controller.workflows
        
        # Get the workflow
        workflow = self.controller.workflows[workflow_id]
        
        # Check workflow properties
        assert workflow.query == query
        assert workflow.title.startswith("Workflow for: Create a workflow for testing")
        assert workflow.status == WorkflowStatus.READY
        
        # Check that the planner agent was called
        self.planner_agent.execute.assert_called_once()
        call_args = self.planner_agent.execute.call_args[1]
        assert call_args["query"] == query
        assert isinstance(call_args["context"], AgentContext)
        
    @pytest.mark.asyncio
    async def test_workflow_task_creation(self):
        """Test that tasks are created properly from planner output"""
        workflow_id = await self.controller.create_workflow("Test query")
        workflow = self.controller.workflows[workflow_id]
        
        # Check that tasks were created
        assert len(workflow.tasks) == 3
        
        # Get tasks sorted by title
        tasks = sorted(workflow.tasks.values(), key=lambda t: t.title)
        
        # Check task 1
        assert tasks[0].title == "Task 1"
        assert tasks[0].description == "Description for task 1"
        assert tasks[0].agent_id == "research_agent"
        assert tasks[0].dependencies == []
        
        # Check task 2
        assert tasks[1].title == "Task 2"
        assert tasks[1].description == "Description for task 2"
        assert tasks[1].agent_id == "writing_agent"
        assert len(tasks[1].dependencies) == 1
        
        # Check task 3
        assert tasks[2].title == "Task 3"
        assert tasks[2].description == "Description for task 3"
        assert tasks[2].agent_id == "coding_agent"
        assert len(tasks[2].dependencies) == 2
        
    @pytest.mark.asyncio
    async def test_get_workflow(self):
        """Test retrieving a workflow"""
        workflow_id = await self.controller.create_workflow("Test query")
        
        # Get the workflow
        workflow = await self.controller.get_workflow(workflow_id)
        
        # Check that we got the right workflow
        assert workflow is self.controller.workflows[workflow_id]
        
        # Try to get a non-existent workflow
        non_existent = await self.controller.get_workflow("non_existent_id")
        assert non_existent is None
        
    @pytest.mark.asyncio
    async def test_cycle_detection(self):
        """Test detection of cyclic dependencies in workflows"""
        # Create a custom planner that returns tasks with cyclic dependencies
        cyclic_tasks = {
            "tasks": [
                {
                    "title": "Task 1",
                    "description": "Description for task 1",
                    "agent_id": "research_agent",
                    "dependencies": [2]  # Depends on Task 3
                },
                {
                    "title": "Task 2",
                    "description": "Description for task 2",
                    "agent_id": "writing_agent",
                    "dependencies": [0]  # Depends on Task 1
                },
                {
                    "title": "Task 3",
                    "description": "Description for task 3",
                    "agent_id": "coding_agent",
                    "dependencies": [1]  # Depends on Task 2, creating a cycle
                }
            ]
        }
        
        # Create a controller with the cyclic tasks
        planner_agent = MockAgent(cyclic_tasks)
        controller = WorkflowController(
            planner_agent=planner_agent,
            memory_system=self.memory
        )
        
        # Creating a workflow should fail due to cyclic dependencies
        with pytest.raises(ValueError) as excinfo:
            await controller.create_workflow("Test query with cyclic dependencies")
        
        # Verify the error message mentions cyclic dependencies
        assert "cycle" in str(excinfo.value).lower()
        
    @pytest.mark.asyncio
    async def test_list_workflows(self):
        """Test listing workflows"""
        # Create a few workflows
        id1 = await self.controller.create_workflow("Query 1")
        id2 = await self.controller.create_workflow("Query 2")
        
        # List workflows
        workflows = await self.controller.list_workflows()
        
        # Check that both workflows are in the list
        assert id1 in workflows
        assert id2 in workflows
        
        # Check summary info
        assert workflows[id1]["title"].startswith("Workflow for: Query 1")
        assert workflows[id2]["title"].startswith("Workflow for: Query 2")
        
    @pytest.mark.asyncio
    async def test_planning_failure(self):
        """Test handling of planning failures"""
        # Make the planner agent raise an exception
        self.planner_agent.execute = AsyncMock(side_effect=Exception("Planning failed"))
        
        # Create a workflow (this should not raise but should mark the workflow as failed)
        with pytest.raises(Exception, match="Planning failed"):
            await self.controller.create_workflow("Test query")
            
        # Check that we have a workflow but it's marked as failed
        assert len(self.controller.workflows) == 1
        workflow_id = list(self.controller.workflows.keys())[0]
        workflow = self.controller.workflows[workflow_id]
        
        assert workflow.status == WorkflowStatus.FAILED
        assert "planning_error" in workflow.metadata
        assert workflow.metadata["planning_error"] == "Planning failed" 