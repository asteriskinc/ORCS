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
from agents.tool import function_tool

from src.orcs.memory.system import AgentContext
from src.orcs.agent.registry import AgentRegistry, global_registry

# Set up logger with appropriate name
logger = logging.getLogger("orcs.agent.infrastructure")


# Define a JSON structure for planning results
class TaskData(BaseModel):
    title: str
    description: str
    agent_id: str
    dependencies: List[int] = []

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
        
    async def on_agent_start(self, agent: Agent[AgentContext], run_id: str) -> None:
        """Called when an agent starts executing
        
        Args:
            agent: The agent that started
            run_id: The ID of the run
        """
        logger.info("Agent '%s' starting run '%s' in workflow '%s'", 
                   agent.name, run_id, self.workflow_id)
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_start:{run_id}",
            value={"timestamp": asyncio.get_event_loop().time()}
        )
        
    async def on_agent_end(self, agent: Agent[AgentContext], run_id: str, output: str) -> None:
        """Called when an agent finishes executing
        
        Args:
            agent: The agent that finished
            run_id: The ID of the run
            output: The output of the agent
        """
        logger.info("Agent '%s' completed run '%s' in workflow '%s'", 
                   agent.name, run_id, self.workflow_id)
        logger.debug("Agent '%s' output length: %d characters", agent.name, len(output))
        self.memory.create_agent_context(
            agent_id=agent.name,
            workflow_id=self.workflow_id
        ).store(
            key=f"agent_result:{run_id}",
            value={"output": output, "timestamp": asyncio.get_event_loop().time()}
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
        
    async def on_run_start(self, run_id: str) -> None:
        """Called when a run starts
        
        Args:
            run_id: The ID of the run
        """
        logger.info("Starting run '%s' for workflow '%s'", run_id, self.workflow_id)
        self.memory.store(
            key=f"run_start:{run_id}",
            value={"timestamp": asyncio.get_event_loop().time()},
            scope=f"workflow:{self.workflow_id}"
        )
        
    async def on_run_end(self, run_id: str, result) -> None:
        """Called when a run ends
        
        Args:
            run_id: The ID of the run
            result: The result of the run
        """
        logger.info("Completed run '%s' for workflow '%s'", run_id, self.workflow_id)
        logger.debug("Run result output length: %d characters", 
                    len(result.final_output) if result.final_output else 0)
        # Store the final output in memory
        self.memory.store(
            key=f"run_result:{run_id}",
            value={"output": result.final_output, "timestamp": asyncio.get_event_loop().time()},
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
    
    Return your plan as a JSON object with a "tasks" array containing task objects with these fields:
    - title: A short descriptive title
    - description: Detailed instructions for the task
    - agent_id: The type of agent to use (must be one of the available agent types)
    - dependencies: Array of task indices that must be completed first (0-based)
    
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
        tools=[get_memory_context]
    )


async def execute_agent_with_memory(
    agent: Agent[AgentContext],
    memory_system,
    workflow_id: str,
    query: str,
    agent_id: str = None
) -> Any:
    """Execute an agent with memory system integration
    
    Args:
        agent: The agent to execute
        memory_system: The memory system to use
        workflow_id: The ID of the workflow
        query: The query to execute
        agent_id: Optional agent ID (defaults to agent.name)
        
    Returns:
        The result of the agent execution
    """
    # Create agent context
    agent_id = agent_id or agent.name
    logger.info("Executing agent '%s' for workflow '%s' with query: '%s'", 
               agent_id, workflow_id, query)
    context = memory_system.create_agent_context(
        agent_id=agent_id,
        workflow_id=workflow_id
    )
    
    # Create hooks for memory integration
    logger.debug("Setting up hooks for agent execution")
    agent_hooks = ORCSAgentHooks(memory_system, workflow_id)
    run_hooks = ORCSRunHooks(memory_system, workflow_id)
    
    # Configure run
    run_config = RunConfig(
        workflow_name=f"ORCS Workflow: {workflow_id}",
        model_settings=agent.model_settings,
        tracing_disabled=False
    )
    
    # Execute the agent
    try:
        logger.debug("Starting agent execution")
        result = await Runner.run(
            starting_agent=agent,
            input=query,
            context=context,
            run_config=run_config,
            hooks=run_hooks
        )
        
        # Store the result in memory
        logger.debug("Storing final result in memory")
        context.store(
            key=f"final_result:{agent_id}",
            value={"output": result.final_output}
        )
        
        # Try to parse JSON if agent was configured to return JSON
        if hasattr(agent, 'output_type') and agent.output_type is not None:
            logger.debug("Attempting to parse JSON output")
            try:
                json_result = json.loads(result.final_output)
                logger.info("Successfully parsed JSON output")
                return json_result
            except json.JSONDecodeError:
                logger.warning("Agent output was not valid JSON: %s", result.final_output[:100] + "..." 
                              if len(result.final_output) > 100 else result.final_output)
                return {"raw_output": result.final_output}
        
        logger.info("Agent execution completed successfully")
        return result.final_output
        
    except Exception as e:
        logger.error("Error executing agent: %s", str(e))
        # Store the error in memory
        context.store(
            key=f"error:{agent_id}",
            value={"error": str(e)}
        )
        # Re-raise the exception
        raise 