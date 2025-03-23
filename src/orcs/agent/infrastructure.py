from typing import Dict, Any, Optional, List, Callable, Union
import json
import asyncio
import logging
from pydantic import BaseModel

from openai import OpenAI
from agents.agent import Agent
from agents.model_settings import ModelSettings
from agents.run import Runner, RunConfig
from agents.run_context import RunContextWrapper
from agents.lifecycle import RunHooks, AgentHooks
from agents.tool import Tool, function_tool

from orcs.context.agent_context import AgentContext
from orcs.agent.registry import global_registry

# Set up logger with appropriate name
logger = logging.getLogger("orcs.agent.infrastructure")


# Define a JSON structure for planning results
class TaskData(BaseModel):
    title: str
    description: str
    agent_id: str
    dependencies: List[int]

class PlanResult(BaseModel):
    tasks: List[TaskData]


class ORCSAgentHooks(AgentHooks[AgentContext]):
    """Hooks for ORCS agents to integrate with memory system"""
    
    def __init__(self, memory_system, workflow_id: str):
        """Initialize the agent hooks
        
        Args:
            memory_system: The memory system to use
            workflow_id: The ID of the workflow
        """
        logger.debug("Initializing ORCSAgentHooks for workflow '%s'", workflow_id)
        self.memory = memory_system
        self.workflow_id = workflow_id
        
    async def on_start(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext]) -> None:
        """Called when an agent starts executing
        
        Args:
            context: The run context wrapper
            agent: The agent that started
        """
        logger.info("Agent '%s' starting in workflow '%s'", 
                   agent.name, self.workflow_id)
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_start:{agent.name}",
            value={"timestamp": asyncio.get_event_loop().time()}
        )
        
    async def on_end(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], output: Any) -> None:
        """Called when an agent finishes executing
        
        Args:
            context: The run context wrapper
            agent: The agent that finished
            output: The output of the agent
        """
        logger.info("Agent '%s' completed in workflow '%s'", 
                   agent.name, self.workflow_id)
        logger.debug("Agent '%s' output length: %d characters", 
                   agent.name, len(str(output)) if output is not None else 0)
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_result:{agent.name}",
            value={"output": output, "timestamp": asyncio.get_event_loop().time()}
        )
        
    async def on_tool_start(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], tool: Tool) -> None:
        """Called when an agent starts a tool execution
        
        Args:
            context: The run context wrapper
            agent: The agent that is executing the tool
            tool: The tool being executed
        """
        logger.info("Agent '%s' starting tool '%s' in workflow '%s'", 
                   agent.name, tool.name, self.workflow_id)
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_tool_start:{agent.name}:{tool.name}",
            value={
                "timestamp": asyncio.get_event_loop().time(),
                "tool_name": tool.name
            }
        )
        
    async def on_tool_end(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], tool: Tool, result: str) -> None:
        """Called when an agent completes a tool execution
        
        Args:
            context: The run context wrapper
            agent: The agent that executed the tool
            tool: The tool that was executed
            result: The result of the tool execution
        """
        logger.info("Agent '%s' completed tool '%s' in workflow '%s'", 
                   agent.name, tool.name, self.workflow_id)
        result_preview = result[:200] + "..." if len(result) > 200 else result
        logger.debug("Tool '%s' result: %s", tool.name, result_preview)
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_tool_result:{agent.name}:{tool.name}",
            value={
                "timestamp": asyncio.get_event_loop().time(),
                "tool_name": tool.name,
                "result": result[:1000] if len(result) > 1000 else result  # Truncate large results
            }
        )
        
    async def on_handoff(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], source: Agent[AgentContext]) -> None:
        """Called when control is handed to this agent
        
        Args:
            context: The run context wrapper
            agent: The agent receiving control
            source: The agent handing off control
        """
        logger.info("Agent '%s' receiving handoff from '%s' in workflow '%s'", 
                   agent.name, source.name, self.workflow_id)
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_handoff:{agent.name}",
            value={
                "timestamp": asyncio.get_event_loop().time(),
                "source_agent": source.name
            }
        )


class ORCSRunHooks(RunHooks[AgentContext]):
    """Hooks for ORCS runs to integrate with memory system"""
    
    def __init__(self, memory_system, workflow_id: str):
        """Initialize the run hooks
        
        Args:
            memory_system: The memory system to use
            workflow_id: The ID of the workflow
        """
        logger.debug("Initializing ORCSRunHooks for workflow '%s'", workflow_id)
        self.memory = memory_system
        self.workflow_id = workflow_id
        
    async def on_agent_start(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext]) -> None:
        """Called when an agent starts executing within a run
        
        Args:
            context: The run context wrapper
            agent: The agent that started
        """
        logger.info("Run: Agent '%s' starting in workflow '%s'", 
                   agent.name, self.workflow_id)
        self.memory.store(
            key=f"run_agent_start:{agent.name}",
            value={"timestamp": asyncio.get_event_loop().time()},
            scope=f"workflow:{self.workflow_id}"
        )
        
    async def on_agent_end(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], output: Any) -> None:
        """Called when an agent finishes executing within a run
        
        Args:
            context: The run context wrapper
            agent: The agent that finished
            output: The output of the agent
        """
        logger.info("Run: Agent '%s' completed in workflow '%s'", 
                   agent.name, self.workflow_id)
        self.memory.store(
            key=f"run_agent_result:{agent.name}",
            value={"output": output, "timestamp": asyncio.get_event_loop().time()},
            scope=f"workflow:{self.workflow_id}"
        )
        
    async def on_tool_start(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], tool: Tool) -> None:
        """Called when a tool starts execution within a run
        
        Args:
            context: The run context wrapper
            agent: The agent executing the tool
            tool: The tool being executed
        """
        logger.info("Run: Tool '%s' starting for agent '%s' in workflow '%s'", 
                   tool.name, agent.name, self.workflow_id)
        self.memory.store(
            key=f"run_tool_start:{agent.name}:{tool.name}",
            value={
                "timestamp": asyncio.get_event_loop().time(),
                "agent_name": agent.name,
                "tool_name": tool.name
            },
            scope=f"workflow:{self.workflow_id}"
        )
        
    async def on_tool_end(self, context: RunContextWrapper[AgentContext], agent: Agent[AgentContext], tool: Tool, result: str) -> None:
        """Called when a tool completes execution within a run
        
        Args:
            context: The run context wrapper
            agent: The agent that executed the tool
            tool: The tool that was executed
            result: The result from the tool
        """
        logger.info("Run: Tool '%s' completed for agent '%s' in workflow '%s'", 
                   tool.name, agent.name, self.workflow_id)
        result_preview = result[:200] + "..." if len(result) > 200 else result
        logger.debug("Tool '%s' result: %s", tool.name, result_preview)
        self.memory.store(
            key=f"run_tool_result:{agent.name}:{tool.name}",
            value={
                "timestamp": asyncio.get_event_loop().time(),
                "agent_name": agent.name,
                "tool_name": tool.name,
                "result": result[:1000] if len(result) > 1000 else result  # Truncate large results
            },
            scope=f"workflow:{self.workflow_id}"
        )
        
    async def on_handoff(self, context: RunContextWrapper[AgentContext], from_agent: Agent[AgentContext], to_agent: Agent[AgentContext]) -> None:
        """Called when one agent hands off to another within a run
        
        Args:
            context: The run context wrapper
            from_agent: The agent handing off control
            to_agent: The agent receiving control
        """
        logger.info("Run: Handoff from agent '%s' to '%s' in workflow '%s'", 
                   from_agent.name, to_agent.name, self.workflow_id)
        self.memory.store(
            key=f"run_handoff:{from_agent.name}:{to_agent.name}",
            value={
                "timestamp": asyncio.get_event_loop().time(),
                "from_agent": from_agent.name,
                "to_agent": to_agent.name
            },
            scope=f"workflow:{self.workflow_id}"
        )


def create_planner_agent(model: str = "gpt-4o-mini", config_provider=None, agent_registry=None) -> Agent[AgentContext]:
    """Create a workflow planner agent using OpenAI Agent
    
    Args:
        model: The model to use
        config_provider: Optional provider for agent configuration
        agent_registry: Optional agent registry to use for available agent types
        
    Returns:
        An OpenAI Agent configured for planning
    """
    logger.info("Creating planner agent with model '%s'", model)
    
    # Apply configuration if provider exists
    model_settings = ModelSettings(
        temperature=0.2,
    )
    
    if config_provider:
        logger.debug("Applying custom configuration for planner agent")
        config = config_provider.get_configuration('agent')
        if 'model' in config:
            model = config['model']
            logger.debug("Using custom model: %s", model)
        if 'temperature' in config:
            model_settings.temperature = config['temperature']
            logger.debug("Using custom temperature: %f", model_settings.temperature)
    
    # Get the list of available agent types from the registry
    if agent_registry is None:
        agent_registry = global_registry
    
    # Build the available agent types string
    available_agent_types = agent_registry.list_agent_types()
    logger.debug("Found %d available agent types in registry", len(available_agent_types))
    
    agent_types_description = ""
    for agent_id in available_agent_types:
        description = agent_registry.get_factory_docstring(agent_id)
        agent_types_description += f"- {agent_id}: {description}\n"
    
    if not agent_types_description:
        # Default agent types if registry is empty
        agent_types_description = """
        - research_agent: For gathering information and conducting research
        - writing_agent: For creating content and documentation
        - coding_agent: For writing and reviewing code
        - data_agent: For data analysis and processing
        """
    
    # Planner system prompt
    planner_instructions = f"""
    You are a workflow planner. Your job is to break down complex tasks into smaller, 
    manageable tasks that can be executed by specialized agents.
    
    Each task should have:
    1. A descriptive title
    2. A detailed description of what needs to be done
    3. The type of agent that should handle it
    4. Any dependencies (other tasks that must be completed first)
    
    IMPORTANT: Always ensure there are NO CYCLES in the dependency graph. If task A depends on task B, 
    and task B depends on task C, then task C must NOT depend on task A (directly or indirectly).
    Dependency cycles will cause deadlocks in execution. Always construct dependencies as a 
    directed acyclic graph (DAG).
    
    Return your plan as a JSON object with a "tasks" array containing task objects with these fields:
    - title: A short descriptive title (required)
    - description: Detailed instructions for the task (required)
    - agent_id: The type of agent to use (required, must be one of the available agent types)
    - dependencies: Array of task indices that must be completed first, 0-based indices (required, use empty array if no dependencies)
    
    Available agent types:
    {agent_types_description}
    """
    
    # Create memory context tool
    @function_tool
    def get_memory_context(context: RunContextWrapper[AgentContext], workflow_id: str) -> str:
        """Get relevant memory items for the current workflow
        
        Args:
            context: The run context wrapper
            workflow_id: The ID of the workflow
            
        Returns:
            A formatted string with memory items
        """
        logger.debug("Getting memory context for workflow '%s'", workflow_id)
        agent_context = context.context
        
        # Get keys that might be relevant to the agent
        keys = agent_context.list_keys()
        logger.debug("Found %d keys in memory for context", len(keys))
        
        # Build a context string with memory content
        context_parts = []
        
        # Add global memory items first
        global_count = 0
        for key in keys:
            if key.startswith("global:"):
                try:
                    value = agent_context.retrieve_global(key)
                    context_parts.append(f"{key}: {json.dumps(value)}")
                    global_count += 1
                except:
                    # Skip keys that can't be retrieved
                    logger.warning("Could not retrieve global key '%s'", key)
                    pass
        
        logger.debug("Added %d global memory items to context", global_count)
                    
        # Add workflow-specific memory items
        workflow_count = 0
        for key in keys:
            if not key.startswith("global:") and not key.startswith("result:") and not key.startswith("error:"):
                try:
                    value = agent_context.retrieve(key)
                    context_parts.append(f"{key}: {json.dumps(value)}")
                    workflow_count += 1
                except:
                    # Skip keys that can't be retrieved
                    logger.warning("Could not retrieve workflow key '%s'", key)
                    pass
        
        logger.debug("Added %d workflow-specific memory items to context", workflow_count)
                    
        if context_parts:
            logger.info("Returning memory context with %d items", len(context_parts))
            return "Memory Context:\n" + "\n".join(context_parts)
        else:
            logger.info("No memory items found for context")
            return "No memory items found."
    
    # Create the planner agent
    logger.info("Planner agent created successfully")
    return Agent[AgentContext](
        name="planner",
        instructions=planner_instructions,
        model=model,
        model_settings=model_settings,
        tools=[get_memory_context],
        output_type=PlanResult
    ) 