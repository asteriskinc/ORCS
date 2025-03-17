import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from agents.agent import Agent
from agents.run import RunResult
from agents.items import ItemHelpers
from agents.model_settings import ModelSettings

from orcs.memory.system import MemorySystem
from orcs.workflow.models import Workflow, Task, WorkflowStatus, TaskStatus
from orcs.workflow.controller import WorkflowController


class TestMilestone1Integration:
    """Integration tests for Milestone 1 components"""
    
    @pytest.mark.asyncio
    @patch('agents.run.Runner.run')
    async def test_basic_workflow_creation(self, mock_runner_run):
        """Test creating a workflow using all components with OpenAI Agent SDK"""
        # Set up mock response from the Runner.run method
        mock_run_result = MagicMock(spec=RunResult)
        mock_run_result.output = json.dumps({
            "tasks": [
                {
                    "title": "Research Task",
                    "description": "Gather information about the topic",
                    "agent_id": "research_agent",
                    "dependencies": []
                },
                {
                    "title": "Analysis Task",
                    "description": "Analyze the gathered information",
                    "agent_id": "data_agent",
                    "dependencies": [0]
                },
                {
                    "title": "Summary Task",
                    "description": "Write a summary of the findings",
                    "agent_id": "writing_agent",
                    "dependencies": [1]
                }
            ]
        })
        mock_runner_run.return_value = mock_run_result
        
        # Create memory system
        memory = MemorySystem()
        
        # Create planner agent with OpenAI's Agent class
        planner = Agent(
            name="planner",
            instructions="You are a workflow planner.",
            model="gpt-4",
            model_settings=ModelSettings(
                temperature=0.2,
                response_format={"type": "json_object"}
            )
        )
        
        # Create workflow controller
        controller = WorkflowController(
            planner_agent=planner,
            memory_system=memory
        )
        
        # Create a workflow
        workflow_id = await controller.create_workflow(
            "Create a tutorial on how to use Python for data analysis"
        )
        
        # Verify mock was called properly
        mock_runner_run.assert_called_once()
        
        # Get the workflow
        workflow = await controller.get_workflow(workflow_id)
        
        # Verify workflow was created correctly
        assert workflow is not None
        assert workflow.status == WorkflowStatus.READY
        
        # Verify tasks were created
        assert len(workflow.tasks) == 3
        
        # Get tasks in order
        tasks = list(workflow.tasks.values())
        research_task = next((t for t in tasks if t.title == "Research Task"), None)
        analysis_task = next((t for t in tasks if t.title == "Analysis Task"), None)
        summary_task = next((t for t in tasks if t.title == "Summary Task"), None)
        
        # Verify tasks were created with correct metadata
        assert research_task is not None
        assert analysis_task is not None
        assert summary_task is not None
        
        # Verify dependencies were set correctly
        assert len(research_task.dependencies) == 0
        assert analysis_task.dependencies[0] in [t.id for t in tasks if t.title == "Research Task"]
        assert summary_task.dependencies[0] in [t.id for t in tasks if t.title == "Analysis Task"]
        
        # Verify all tasks are in pending state
        for task in tasks:
            assert task.status == TaskStatus.PENDING
            
    @pytest.mark.asyncio
    @patch('agents.run.Runner.run')
    async def test_workflow_with_planning_error(self, mock_runner_run):
        """Test handling of planning errors"""
        # Set up mock to raise an exception
        mock_runner_run.side_effect = Exception("Planning failed")
        
        # Create memory system
        memory = MemorySystem()
        
        # Create planner agent
        planner = Agent(
            name="planner",
            instructions="You are a workflow planner.",
            model="gpt-4"
        )
        
        # Create workflow controller
        controller = WorkflowController(
            planner_agent=planner,
            memory_system=memory
        )
        
        # Create a workflow and expect exception
        with pytest.raises(Exception) as excinfo:
            await controller.create_workflow("This will fail")
            
        # Verify exception message
        assert "Planning failed" in str(excinfo.value)
        
        # Get all workflows
        workflows = await controller.list_workflows()
        
        # Get the workflow (there should be one)
        workflow_id = list(workflows.keys())[0]
        workflow = await controller.get_workflow(workflow_id)
        
        # Verify workflow status is failed
        assert workflow.status == WorkflowStatus.FAILED
        assert "Planning failed" in workflow.metadata.get("planning_error", "")
        
    @pytest.mark.asyncio
    async def test_workflow_list_and_retrieval(self):
        """Test workflow listing and retrieval functionality"""
        # Create a mock planner agent
        planner = MagicMock()
        planner.execute = AsyncMock(return_value={"tasks": []})
        
        # Create controller
        memory = MemorySystem()
        controller = WorkflowController(
            planner_agent=planner,
            memory_system=memory
        )
        
        # Create multiple workflows
        id1 = await controller.create_workflow("Query 1")
        id2 = await controller.create_workflow("Query 2")
        id3 = await controller.create_workflow("Query 3")
        
        # List workflows
        workflows = await controller.list_workflows()
        
        # Check that all workflows are listed
        assert len(workflows) == 3
        assert id1 in workflows
        assert id2 in workflows
        assert id3 in workflows
        
        # Retrieve each workflow
        workflow1 = await controller.get_workflow(id1)
        workflow2 = await controller.get_workflow(id2)
        workflow3 = await controller.get_workflow(id3)
        
        # Check workflows were retrieved correctly
        assert workflow1.query == "Query 1"
        assert workflow2.query == "Query 2"
        assert workflow3.query == "Query 3" 