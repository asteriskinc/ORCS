import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from orcs.agent.infrastructure import (
    RunContextWrapper, Agent, EnhancedAgent, PlannerAgent
)
from orcs.memory.system import MemorySystem, AgentContext


class TestRunContextWrapper:
    """Test suite for RunContextWrapper"""
    
    def test_initialization(self):
        """Test initializing a run context wrapper"""
        context = "test_context"
        wrapper = RunContextWrapper(context)
        
        assert wrapper.context == "test_context"


class TestAgent:
    """Test suite for the base Agent class"""
    
    class ConcreteAgent(Agent):
        """Concrete implementation of Agent for testing"""
        
        def __init__(self, model, run_result=None, client=None):
            super().__init__(model, client)
            self.run_result = run_result or {}
            
        async def _run(self, context, query):
            return self.run_result
    
    def test_initialization(self):
        """Test agent initialization"""
        agent = self.ConcreteAgent("test_model")
        
        assert agent.model == "test_model"
        assert agent.client is not None
        
    @pytest.mark.asyncio
    async def test_execute(self):
        """Test execute method"""
        expected_result = {"result": "test_result"}
        agent = self.ConcreteAgent("test_model", expected_result)
        
        result = await agent.execute("test_context", "test_query")
        
        assert result == expected_result
        
    @pytest.mark.asyncio
    async def test_execute_with_context_wrapping(self):
        """Test that execute properly wraps the context"""
        # Create a spy version of _run to capture the wrapped context
        context_spy = None
        
        class SpyAgent(Agent):
            async def _run(self, context, query):
                nonlocal context_spy
                context_spy = context
                return {"result": "ok"}
                
        agent = SpyAgent("test_model")
        original_context = "test_context"
        
        await agent.execute(original_context, "test_query")
        
        assert context_spy is not None
        assert isinstance(context_spy, RunContextWrapper)
        assert context_spy.context == original_context


class TestEnhancedAgent:
    """Test suite for EnhancedAgent"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test enhanced agent initialization"""
        agent = EnhancedAgent(
            model="test_model",
            system_prompt="test_prompt"
        )
        
        assert agent.model == "test_model"
        assert agent.system_prompt == "test_prompt"
        
    @pytest.mark.asyncio
    async def test_run_with_memory_context(self):
        """Test _run method with memory context"""
        # Create a mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({"result": "test_result"})))
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Create an enhanced agent with the mock client
        agent = EnhancedAgent(
            model="test_model",
            system_prompt="test_prompt",
            client=mock_client
        )
        
        # Create memory system and context
        memory = MemorySystem()
        agent_context = memory.create_agent_context("test_agent", "test_workflow")
        
        # Add some data to memory
        memory.store("global:test_data", "global_value", "global")
        agent_context.store("agent_data", "agent_value")
        
        # Create a wrapped context
        wrapped_context = RunContextWrapper(agent_context)
        
        # Run the agent
        result = await agent._run(wrapped_context, "test_query")
        
        # Check that the client was called with the correct arguments
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        
        # Check that the system prompt includes memory context
        system_message = call_args["messages"][0]["content"]
        assert "test_prompt" in system_message
        assert "Memory Context:" in system_message
        assert "global:test_data" in system_message
        assert "agent_data" in system_message
        
        # Check that the result was returned correctly
        assert result == {"result": "test_result"}
        
        # Check that the result was stored in memory
        # Get all keys from memory
        keys = agent_context.list_keys(include_global=False)
        
        # Check that there's a result key
        result_keys = [k for k in keys if k.startswith("result:")]
        assert len(result_keys) == 1
        
    @pytest.mark.asyncio
    async def test_run_with_exception(self):
        """Test _run method with exception handling"""
        # Create a mock OpenAI client that raises an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Test error"))
        
        # Create an enhanced agent with the mock client
        agent = EnhancedAgent(
            model="test_model",
            system_prompt="test_prompt",
            client=mock_client
        )
        
        # Create memory system and context
        memory = MemorySystem()
        agent_context = memory.create_agent_context("test_agent", "test_workflow")
        
        # Create a wrapped context
        wrapped_context = RunContextWrapper(agent_context)
        
        # Run the agent (should raise an exception)
        with pytest.raises(Exception, match="Test error"):
            await agent._run(wrapped_context, "test_query")
            
        # Check that the error was stored in memory
        keys = agent_context.list_keys(include_global=False)
        error_keys = [k for k in keys if k.startswith("error:")]
        assert len(error_keys) == 1
        
        # Check the error content
        error_data = agent_context.retrieve(error_keys[0])
        assert error_data["error"] == "Test error"


class TestPlannerAgent:
    """Test suite for PlannerAgent"""
    
    def test_initialization(self):
        """Test planner agent initialization"""
        agent = PlannerAgent(model="test_model")
        
        assert agent.model == "test_model"
        assert "workflow planner" in agent.system_prompt.lower()
        assert "tasks" in agent.system_prompt
        assert "dependencies" in agent.system_prompt 