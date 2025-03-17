import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import time

from agents.agent import Agent
from agents.run import Runner, RunConfig
from orcs.workflow.models import Workflow, WorkflowStatus, Task, TaskStatus
from orcs.agent.registry import AgentRegistry, global_registry
from orcs.agent.infrastructure import ORCSRunHooks

# Set up logger
logger = logging.getLogger("orcs.workflow.orchestrator")


class WorkflowOrchestrator:
    """Orchestrates the execution of workflows"""
    
    def __init__(self, 
                memory_system,
                agent_registry: Optional[AgentRegistry] = None,
                resource_manager=None,
                telemetry_collector=None):
        """Initialize the workflow orchestrator
        
        Args:
            memory_system: The memory system to use
            agent_registry: Registry of available agents (uses global registry if None)
            resource_manager: Optional resource manager for resource allocation
            telemetry_collector: Optional telemetry collector for metrics and events
        """
        self.memory = memory_system
        self.agent_registry = agent_registry or global_registry
        self.resource_manager = resource_manager
        self.telemetry_collector = telemetry_collector
        
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
        
        # Allocate resources if manager is provided
        if self.resource_manager:
            logger.debug("Allocating resources for workflow '%s'", workflow.id)
            resources_allocated = await self.resource_manager.allocate_resources(
                workflow.id, workflow.metadata.get("resource_requirements", {})
            )
            if not resources_allocated:
                logger.error("Failed to allocate resources for workflow '%s'", workflow.id)
                workflow.status = WorkflowStatus.FAILED
                workflow.metadata["error"] = "Failed to allocate resources"
                return self._create_output(workflow)
        
        try:
            # Initialize workflow execution
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now().isoformat()
            logger.info("Workflow '%s' started at %s", workflow.id, workflow.started_at)
            
            # Record workflow started event
            if self.telemetry_collector:
                logger.debug("Recording workflow started event")
                await self.telemetry_collector.record_event(
                    event_type='workflow_started',
                    resource_id=workflow.id,
                    metadata={
                        'query': workflow.query,
                        'timestamp': workflow.started_at
                    }
                )
            
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
                        
                        # Record workflow completed event
                        if self.telemetry_collector:
                            logger.debug("Recording workflow completed event")
                            await self.telemetry_collector.record_event(
                                event_type='workflow_completed',
                                resource_id=workflow.id,
                                metadata={
                                    'duration': time.time() - datetime.fromisoformat(workflow.started_at).timestamp(),
                                    'timestamp': workflow.completed_at
                                }
                            )
                        break
                    
                    # If we can't execute any tasks but not all are completed,
                    # we might have a deadlock or some other issue
                    if all(task.status != TaskStatus.RUNNING for task in workflow.tasks.values()):
                        logger.error("Workflow '%s' execution deadlocked", workflow.id)
                        workflow.status = WorkflowStatus.FAILED
                        workflow.metadata["error"] = "Workflow execution deadlocked"
                        
                        # Record workflow failed event
                        if self.telemetry_collector:
                            logger.debug("Recording workflow failed event")
                            await self.telemetry_collector.record_event(
                                event_type='workflow_failed',
                                resource_id=workflow.id,
                                metadata={
                                    'error': "Workflow execution deadlocked",
                                    'timestamp': datetime.now().isoformat()
                                }
                            )
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
            
            # Record workflow failed event
            if self.telemetry_collector:
                logger.debug("Recording workflow failed event")
                await self.telemetry_collector.record_event(
                    event_type='workflow_failed',
                    resource_id=workflow.id,
                    metadata={
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            return self._create_output(workflow)
            
        finally:
            # Always release resources if manager exists
            if self.resource_manager:
                logger.debug("Releasing resources for workflow '%s'", workflow.id)
                await self.resource_manager.release_resources(workflow.id)
    
    async def _execute_task(self, workflow: Workflow, task: Task, status_callback: Optional[Callable] = None) -> None:
        """Execute a single task using the Agent SDK
        
        Args:
            workflow: The workflow containing the task
            task: The task to execute
            status_callback: Optional callback for status updates
        """
        logger.info("Executing task '%s' (%s) in workflow '%s'", 
                   task.title, task.id, workflow.id)
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        # Notify status if callback provided
        if status_callback:
            logger.debug("Notifying task started via callback")
            await status_callback({
                "workflow_id": workflow.id,
                "task_id": task.id,
                "status": task.status.value,
                "message": f"Started task: {task.title}"
            })
        
        # Record task started event
        if self.telemetry_collector:
            logger.debug("Recording task started event")
            await self.telemetry_collector.record_event(
                event_type='task_started',
                resource_id=task.id,
                metadata={
                    'workflow_id': workflow.id,
                    'agent_id': task.agent_id,
                    'timestamp': task.started_at
                }
            )
        
        try:
            # Get the agent for this task
            logger.debug("Getting agent '%s' from registry", task.agent_id)
            agent = self.agent_registry.get_agent(task.agent_id)
            
            # Create agent context
            logger.debug("Creating agent context for agent '%s'", task.agent_id)
            agent_context = self.memory.create_agent_context(
                agent_id=task.agent_id,
                workflow_id=workflow.id
            )
            
            # Set up run hooks for memory integration
            run_hooks = ORCSRunHooks(self.memory, workflow.id)
            
            # Execute the agent using the AgentSDK Runner
            logger.debug("Executing agent '%s' with AgentSDK Runner", task.agent_id)
            result = await Runner.run(
                starting_agent=agent,
                input=task.description,
                context=agent_context,
                run_config=RunConfig(
                    workflow_name=f"Task {task.id} in Workflow {workflow.id}",
                    tracing_disabled=False
                ),
                hooks=run_hooks
            )
            
            # Store the result
            logger.debug("Storing task result")
            task.result = result.final_output
            workflow.results[task.id] = result.final_output
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            logger.info("Task '%s' completed successfully", task.id)
            
            # Record task completed event
            if self.telemetry_collector:
                logger.debug("Recording task completed event")
                await self.telemetry_collector.record_event(
                    event_type='task_completed',
                    resource_id=task.id,
                    metadata={
                        'workflow_id': workflow.id,
                        'duration': time.time() - datetime.fromisoformat(task.started_at).timestamp(),
                        'timestamp': task.completed_at
                    }
                )
            
            # Notify status if callback provided
            if status_callback:
                logger.debug("Notifying task completed via callback")
                await status_callback({
                    "workflow_id": workflow.id,
                    "task_id": task.id,
                    "status": task.status.value,
                    "message": f"Completed task: {task.title}"
                })
                
        except Exception as e:
            # Update task status
            logger.error("Task '%s' failed: %s", task.id, str(e), exc_info=True)
            task.status = TaskStatus.FAILED
            task.result = {"error": str(e)}
            
            # Record task failed event
            if self.telemetry_collector:
                logger.debug("Recording task failed event")
                await self.telemetry_collector.record_event(
                    event_type='task_failed',
                    resource_id=task.id,
                    metadata={
                        'workflow_id': workflow.id,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            # Notify status if callback provided
            if status_callback:
                logger.debug("Notifying task failed via callback")
                await status_callback({
                    "workflow_id": workflow.id,
                    "task_id": task.id,
                    "status": task.status.value,
                    "message": f"Failed task: {task.title} - {str(e)}"
                })
    
    def _create_output(self, workflow: Workflow) -> Dict[str, Any]:
        """Create the final output for a workflow
        
        Args:
            workflow: The executed workflow
            
        Returns:
            Dictionary with the workflow execution results
        """
        logger.debug("Creating final output for workflow '%s'", workflow.id)
        return {
            "workflow_id": workflow.id,
            "status": workflow.status.value,
            "results": workflow.results,
            "metadata": {
                "title": workflow.title,
                "description": workflow.description,
                "query": workflow.query,
                "created_at": workflow.created_at,
                "started_at": workflow.started_at,
                "completed_at": workflow.completed_at,
                "error": workflow.metadata.get("error")
            }
        } 