import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Type
from datetime import datetime
from pydantic import BaseModel

from agents.agent import Agent
from agents.run import Runner, RunConfig
from orcs.workflow.models import Workflow, WorkflowStatus, Task, TaskStatus
from orcs.agent.registry import AgentRegistry, global_registry

# Import metrics hooks
from orcs.metrics import (
    MetricsAgentHooks,
    MetricsRunHooks
)

# Import memory system
from orcs.memory import (
    get_default_memory_system
)

# Set up logger
logger = logging.getLogger("orcs.workflow.orchestrator")


class WorkflowOrchestrator:
    """Orchestrates the execution of workflows"""
    
    def __init__(self, 
                memory_system=None,
                agent_registry: Optional[AgentRegistry] = None):
        """Initialize the workflow orchestrator
        
        Args:
            memory_system: The memory system to use (default: global default)
            agent_registry: Registry of available agents (uses global registry if None)
        """
        # Get the default memory system if none provided
        self.memory = memory_system or get_default_memory_system()
        
        self.agent_registry = agent_registry or global_registry
        
        # Log available agent types
        agent_types = self.agent_registry.list_agent_types()
        logger.info("WorkflowOrchestrator initialized with %d agent types", len(agent_types))
        if agent_types:
            logger.debug("Available agent types: %s", ", ".join(agent_types))
        else:
            logger.warning("No agent types registered in the agent registry")
        
    async def execute(self, workflow: Workflow, status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a workflow
        
        Args:
            workflow: The workflow to execute
            status_callback: Optional callback for status updates
            
        Returns:
            The workflow execution results
        """
        logger.info("Starting execution of workflow '%s'", workflow.id)
        
        try:
            # Initialize workflow execution
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now().isoformat()
            logger.info("Workflow '%s' started at %s", workflow.id, workflow.started_at)
            
            # Main execution loop
            while True:
                # Get tasks that can be executed now
                executable_tasks = workflow.get_executable_tasks()
                
                # If no tasks can be executed and all tasks are completed, we're done
                completed_count = sum(1 for task in workflow.tasks.values() 
                                    if task.status == TaskStatus.COMPLETED)
                
                if not executable_tasks:
                    if completed_count == len(workflow.tasks):
                        logger.info("All tasks completed for workflow '%s'", workflow.id)
                        workflow.status = WorkflowStatus.COMPLETED
                        workflow.completed_at = datetime.now().isoformat()
                        break
                    
                    # If we can't execute any tasks but not all are completed,
                    # we might have a deadlock or some other issue
                    if all(task.status != TaskStatus.RUNNING for task in workflow.tasks.values()):
                        logger.error("Workflow '%s' execution deadlocked", workflow.id)
                        workflow.status = WorkflowStatus.FAILED
                        workflow.metadata["error"] = "Workflow execution deadlocked"
                        break
                    
                    # Otherwise, wait a bit and check again
                    logger.debug("No executable tasks at the moment, waiting...")
                    await asyncio.sleep(0.1)
                    continue
                
                # Execute the next task
                logger.info("Found %d executable tasks, executing next task", len(executable_tasks))
                next_task = executable_tasks[0]  # In this implementation, we execute sequentially
                await self._execute_task(workflow, next_task, status_callback)
            
            # Prepare final output
            logger.info("Workflow '%s' execution complete with status: %s", 
                       workflow.id, workflow.status.value)
            return self._create_output(workflow)
            
        except Exception as e:
            # Handle any uncaught exceptions
            logger.error("Uncaught exception in workflow '%s': %s", workflow.id, str(e), exc_info=True)
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["error"] = str(e)
            
            return self._create_output(workflow)
    
    async def _execute_task(self, workflow: Workflow, task: Task, 
                             status_callback: Optional[Callable] = None) -> None:
        """Execute a single task using the Agent SDK
        
        Args:
            workflow: The workflow containing the task
            task: The task to execute
            status_callback: Optional callback for status updates
        """
        logger.info("Executing task '%s' (%s) in workflow '%s'", 
                   task.id, task.agent_id, workflow.id)
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        # Notify callback if provided
        if status_callback:
            await status_callback(workflow)
        
        try:
            # Look up the agent from the registry
            agent_instance = self.agent_registry.get_agent(task.agent_id)
            if not agent_instance:
                logger.error("Agent type '%s' not found in registry", task.agent_id)
                task.status = TaskStatus.FAILED
                task.metadata["error"] = f"Agent type '{task.agent_id}' not found"
                return
            
            # Get the output type from agent
            output_schema = getattr(agent_instance, 'output_type', None)
            
            # Set up hooks
            agent_hooks = MetricsAgentHooks(workflow_id=workflow.id)
            run_hooks = MetricsRunHooks(workflow_id=workflow.id)
            
            # Configure the run
            run_config = RunConfig(
                workflow_name=f"Task execution: {task.id}",
                trace_metadata={
                    "workflow_id": workflow.id,
                    "task_id": task.id,
                    "agent_id": task.agent_id
                }
            )
            
            # Execute the agent with the Agent SDK
            logger.info("Running agent '%s' for task '%s'", 
                      task.agent_id, task.id)
            
            # Get input from task or previous task outputs
            task_input = await self._get_task_input(workflow, task)
            
            # Execute the agent
            run_result = await Runner.run(
                starting_agent=agent_instance,
                input=task_input,
                run_config=run_config,
                hooks=run_hooks
            )
            
            # Process the result
            logger.info("Task '%s' completed successfully", task.id)
            
            # Parse the result using the output schema if available
            if output_schema and issubclass(output_schema, BaseModel):
                try:
                    # If the result is already a dictionary, use it directly
                    if isinstance(run_result.final_output, dict):
                        parsed_output = output_schema(**run_result.final_output)
                        task.result = parsed_output.model_dump()
                        logger.info(
                            f"Successfully parsed dictionary output for task '{task.id}' into {output_schema.__name__}"
                        )
                    else:
                        # If the result is a string, log a warning
                        logger.warning(
                            f"Agent output for task '{task.id}' is not a dictionary. "
                            f"Expected format matching {output_schema.__name__}. "
                            f"Storing raw output instead."
                        )
                        task.result = run_result.final_output
                except Exception as e:
                    logger.warning(
                        f"Failed to parse agent output using schema {output_schema.__name__}: {str(e)}. "
                        f"Storing raw output instead."
                    )
                    task.result = run_result.final_output
            else:
                # If no output schema is defined, store the raw output
                task.result = run_result.final_output
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            
            # Notify callback if provided
            if status_callback:
                await status_callback(workflow)
                
        except Exception as e:
            logger.exception("Error executing task '%s': %s", task.id, str(e))
            task.status = TaskStatus.FAILED
            task.metadata["error"] = str(e)
            
            # Notify callback if provided
            if status_callback:
                await status_callback(workflow)
    
    async def _get_task_input(self, workflow: Workflow, task: Task) -> str:
        """Get the input for a task
        
        The input can come either directly from the task's input_data or
        from the outputs of previous tasks that this task depends on.
        
        Args:
            workflow: The workflow containing the task
            task: The task to get input for
            
        Returns:
            The task input as a string
        """
        # Check for custom input in task metadata
        if task.metadata.get("input_data"):
            logger.info("Using custom input data for task '%s'", task.id)
            return task.metadata.get("input_data")
            
        # Build input from task description and dependencies
        input_parts = []
        
        if task.title:
            input_parts.append(f"Task: {task.title}")
        if task.description:
            input_parts.append(f"Description: {task.description}")
            
        # Add outputs from dependencies
        if task.dependencies:
            logger.info("Adding outputs from %d dependencies to task input", len(task.dependencies))
            input_parts.append("\nPrevious task outputs:")
            for dep_id in task.dependencies:
                dep_task = workflow.get_task(dep_id)
                if dep_task.status == TaskStatus.COMPLETED:
                    if dep_task.result:
                        input_parts.append(f"Output from {dep_task.agent_id} (Task {dep_id}):")
                        # Convert result to string if it's not already a string
                        result_str = str(dep_task.result)
                        input_parts.append(result_str)
                        input_parts.append("---")
        
        # If we didn't find any inputs, use a generic prompt
        if not input_parts:
            logger.warning("No input sources found for task '%s', using generic prompt", task.id)
            return f"Please perform task '{task.agent_id}' for workflow '{workflow.id}'."
            
        # Join input parts with newlines
        return "\n".join(input_parts)
    
    def _create_output(self, workflow: Workflow) -> Dict[str, Any]:
        """Create the final output for a workflow
        
        Args:
            workflow: The workflow to create output for
            
        Returns:
            Dict containing workflow results
        """
        # Gather individual task results
        task_results = {}
        for task_id, task in workflow.tasks.items():
            task_results[task_id] = {
                "id": task_id,
                "agent_id": task.agent_id,
                "status": task.status.value,
                "result": task.result,
                "start_time": task.started_at,
                "end_time": task.completed_at
            }
        
        # Build the output structure
        output = {
            "workflow_id": workflow.id,
            "status": workflow.status.value,
            "query": workflow.query,
            "started_at": workflow.started_at,
            "completed_at": getattr(workflow, "completed_at", None),
            "error": workflow.metadata.get("error"),
            "tasks": task_results
        }
        
        return output 