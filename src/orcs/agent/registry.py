from typing import Dict, Any, Callable, Optional, Union, TypeVar
import logging
from agents.agent import Agent

from orcs.memory.system import AgentContext

# Set up logger
logger = logging.getLogger("orcs.agent.registry")

# Type for agent factory functions
AgentFactory = Callable[..., Agent[AgentContext]]
AgentT = TypeVar('AgentT', bound=Agent[AgentContext])

class AgentRegistry:
    """Registry for agent types and instances"""
    
    def __init__(self):
        self._agent_factories: Dict[str, AgentFactory] = {}  # Maps agent_id to factory function
        self._agent_instances: Dict[str, Agent[AgentContext]] = {}  # Maps agent_id to instantiated agents
        logger.info("Initialized AgentRegistry")
        
    def register_agent_type(self, agent_id: str, factory_function: AgentFactory) -> None:
        """Register an agent factory function
        
        Args:
            agent_id: The ID for this agent type
            factory_function: Function that creates an instance of this agent
        """
        self._agent_factories[agent_id] = factory_function
        logger.info("Registered agent type '%s'", agent_id)
        
    def create_agent(self, agent_id: str, **kwargs) -> Agent[AgentContext]:
        """Create and register an agent instance
        
        Args:
            agent_id: The ID for the agent
            **kwargs: Arguments to pass to the factory function
            
        Returns:
            The created agent instance
            
        Raises:
            ValueError: If agent_id is not registered
        """
        if agent_id not in self._agent_factories:
            logger.error("Agent type '%s' not registered", agent_id)
            raise ValueError(f"Agent type '{agent_id}' not registered")
            
        logger.info("Creating agent instance for type '%s'", agent_id)
        agent = self._agent_factories[agent_id](**kwargs)
        self._agent_instances[agent_id] = agent
        return agent
        
    def get_agent(self, agent_id: str) -> Agent[AgentContext]:
        """Get a registered agent instance
        
        Args:
            agent_id: The ID of the agent to get
            
        Returns:
            The agent instance if found
            
        Raises:
            ValueError: If agent_id is not registered or instantiated
        """
        if agent_id in self._agent_instances:
            logger.debug("Retrieved agent instance '%s'", agent_id)
            return self._agent_instances[agent_id]
            
        # Try to create it if we have a factory but no instance
        if agent_id in self._agent_factories:
            logger.info("Lazily creating agent instance for type '%s'", agent_id)
            return self.create_agent(agent_id)
            
        logger.error("Agent '%s' not registered or instantiated", agent_id)
        raise ValueError(f"Agent '{agent_id}' not registered or instantiated")
        
    def register_instance(self, agent_id: str, agent_instance: Agent[AgentContext]) -> None:
        """Register an existing agent instance
        
        Args:
            agent_id: The ID for the agent
            agent_instance: The agent instance to register
        """
        self._agent_instances[agent_id] = agent_instance
        logger.info("Registered agent instance '%s'", agent_id)
        
    def list_agent_types(self) -> list[str]:
        """List all registered agent types
        
        Returns:
            List of agent type IDs
        """
        return list(self._agent_factories.keys())
        
    def list_agent_instances(self) -> list[str]:
        """List all instantiated agents
        
        Returns:
            List of agent instance IDs
        """
        return list(self._agent_instances.keys())
        
    def get_factory_docstring(self, agent_id: str) -> str:
        """Get a docstring from a factory function
        
        Args:
            agent_id: The ID of the agent type
            
        Returns:
            First sentence of factory docstring or empty string
        """
        if agent_id not in self._agent_factories:
            return ""
            
        factory = self._agent_factories[agent_id]
        if not factory.__doc__:
            return ""
            
        # Return first sentence of docstring
        return factory.__doc__.strip().split('.')[0]


# Create global registry instance
global_registry = AgentRegistry()

def register_agent_type(registry=None, agent_id=None):
    """Decorator to register a factory function as an agent type
    
    Args:
        registry: The AgentRegistry to register with (defaults to global registry)
        agent_id: Optional ID for the agent type (defaults to function name)
        
    Returns:
        Decorator function
    """
    if registry is None:
        registry = global_registry
        
    def decorator(factory_function):
        nonlocal agent_id
        if agent_id is None:
            agent_id = factory_function.__name__.replace('create_', '')
            
        registry.register_agent_type(agent_id, factory_function)
        return factory_function
        
    return decorator 