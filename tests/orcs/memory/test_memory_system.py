import pytest
from src.orcs.memory.system import MemorySystem, AgentContext


class TestMemorySystem:
    """Test suite for the MemorySystem"""

    def test_store_and_retrieve(self):
        """Test basic storage and retrieval"""
        memory = MemorySystem()
        memory.store("test_key", "test_value")
        
        # Global scope should be accessible by any scope
        assert memory.retrieve("test_key", "any_scope") == "test_value"
        
    def test_scoped_access(self):
        """Test scoped access controls"""
        memory = MemorySystem()
        
        # Store data in different scopes
        memory.store("global_key", "global_value", "global")
        memory.store("workflow_key", "workflow_value", "workflow:123")
        memory.store("task_key", "task_value", "workflow:123:task:456")
        memory.store("agent_key", "agent_value", "workflow:123:agent:789")
        
        # Global data is accessible to all
        assert memory.retrieve("global_key", "workflow:123") == "global_value"
        assert memory.retrieve("global_key", "workflow:123:task:456") == "global_value"
        
        # Workflow can access its own data
        assert memory.retrieve("workflow_key", "workflow:123") == "workflow_value"
        
        # Workflow can access its task's data
        assert memory.retrieve("task_key", "workflow:123") == "task_value"
        
        # Task can access its own data
        assert memory.retrieve("task_key", "workflow:123:task:456") == "task_value"
        
        # Task cannot access sibling agent's data
        with pytest.raises(PermissionError):
            memory.retrieve("agent_key", "workflow:123:task:456")
            
        # Different workflow cannot access other workflow's data
        with pytest.raises(PermissionError):
            memory.retrieve("workflow_key", "workflow:999")
            
    def test_list_keys(self):
        """Test listing keys by scope pattern"""
        memory = MemorySystem()
        
        # Store data in different scopes
        memory.store("global_key", "global_value", "global")
        memory.store("workflow1_key", "workflow1_value", "workflow:123")
        memory.store("workflow2_key", "workflow2_value", "workflow:456")
        memory.store("task_key", "task_value", "workflow:123:task:789")
        
        # List all keys
        all_keys = memory.list_keys()
        assert len(all_keys) == 4
        assert "global_key" in all_keys
        assert "workflow1_key" in all_keys
        assert "workflow2_key" in all_keys
        assert "task_key" in all_keys
        
        # List keys in workflow:123
        workflow_keys = memory.list_keys("workflow:123")
        assert len(workflow_keys) == 1
        assert "workflow1_key" in workflow_keys
        
        # List keys in any workflow
        all_workflow_keys = memory.list_keys("workflow:*")
        assert len(all_workflow_keys) == 2
        assert "workflow1_key" in all_workflow_keys
        assert "workflow2_key" in all_workflow_keys
        
        # List keys in workflow:123 and its children
        workflow_and_children = memory.list_keys("workflow:123*")
        assert len(workflow_and_children) == 2
        assert "workflow1_key" in workflow_and_children
        assert "task_key" in workflow_and_children
        
    def test_key_not_found(self):
        """Test behavior when key is not found"""
        memory = MemorySystem()
        
        with pytest.raises(KeyError):
            memory.retrieve("nonexistent_key", "any_scope")


class TestAgentContext:
    """Test suite for the AgentContext"""
    
    def test_agent_context_store_retrieve(self):
        """Test storing and retrieving data through agent context"""
        memory = MemorySystem()
        agent_context = memory.create_agent_context("agent1", "workflow1")
        
        # Store data through agent context
        agent_context.store("agent_key", "agent_value")
        
        # Retrieve data through agent context
        assert agent_context.retrieve("agent_key") == "agent_value"
        
        # Check the actual scope used
        assert memory.access_scopes["agent_key"] == "workflow:workflow1:agent:agent1"
        
    def test_agent_context_sub_scope(self):
        """Test using sub-scopes within agent context"""
        memory = MemorySystem()
        agent_context = memory.create_agent_context("agent1", "workflow1")
        
        # Store data in a sub-scope
        agent_context.store("task_key", "task_value", "task1")
        
        # Retrieve data (agent can access its sub-scopes)
        assert agent_context.retrieve("task_key") == "task_value"
        
        # Check the actual scope used
        assert memory.access_scopes["task_key"] == "workflow:workflow1:agent:agent1:task1"
        
    def test_agent_global_access(self):
        """Test agent access to global data"""
        memory = MemorySystem()
        agent_context = memory.create_agent_context("agent1", "workflow1")
        
        # Store global data directly in memory
        memory.store("global_key", "global_value", "global")
        
        # Agent can access global data
        assert agent_context.retrieve_global("global_key") == "global_value"
        
    def test_agent_list_keys(self):
        """Test listing keys accessible to an agent"""
        memory = MemorySystem()
        agent_context = memory.create_agent_context("agent1", "workflow1")
        
        # Store various data
        memory.store("global_key", "global_value", "global")
        agent_context.store("agent_key", "agent_value")
        agent_context.store("task_key", "task_value", "task1")
        memory.store("other_agent", "other_value", "workflow:workflow1:agent:agent2")
        
        # List all keys accessible to the agent
        keys = agent_context.list_keys()
        assert len(keys) == 3  # global_key, agent_key, task_key
        assert "global_key" in keys
        assert "agent_key" in keys
        assert "task_key" in keys
        assert "other_agent" not in keys  # Not accessible to this agent
        
        # List only agent-specific keys
        agent_keys = agent_context.list_keys(include_global=False)
        assert len(agent_keys) == 2  # agent_key, task_key
        assert "global_key" not in agent_keys
        assert "agent_key" in agent_keys
        assert "task_key" in agent_keys 