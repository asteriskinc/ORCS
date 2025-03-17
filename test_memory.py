#!/usr/bin/env python3
"""
Simple test script for the memory system
"""

from src.orcs.memory.system import MemorySystem, AgentContext

def test_memory_system():
    """Test basic memory system functionality"""
    memory = MemorySystem()
    
    # Test storing and retrieving data
    memory.store("test_key", "test_value")
    assert memory.retrieve("test_key", "any_scope") == "test_value"
    
    # Test scoped access
    memory.store("workflow_key", "workflow_value", "workflow:123")
    memory.store("task_key", "task_value", "workflow:123:task:456")
    
    # Global data is accessible to all
    assert memory.retrieve("test_key", "workflow:123") == "test_value"
    
    # Workflow can access its own data
    assert memory.retrieve("workflow_key", "workflow:123") == "workflow_value"
    
    # Workflow can access its task's data
    assert memory.retrieve("task_key", "workflow:123") == "task_value"
    
    print("Memory system tests passed!")

def test_agent_context():
    """Test agent context functionality"""
    memory = MemorySystem()
    agent_context = memory.create_agent_context("agent1", "workflow1")
    
    # Test storing and retrieving data
    agent_context.store("agent_key", "agent_value")
    assert agent_context.retrieve("agent_key") == "agent_value"
    
    # Test sub-scopes
    agent_context.store("task_key", "task_value", "task1")
    assert agent_context.retrieve("task_key") == "task_value"
    
    # Test global access
    memory.store("global_key", "global_value", "global")
    assert agent_context.retrieve_global("global_key") == "global_value"
    
    print("Agent context tests passed!")

if __name__ == "__main__":
    test_memory_system()
    test_agent_context()
    print("All tests passed!") 