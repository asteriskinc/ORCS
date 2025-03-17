import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import json
import logging

from agents.agent import Agent
from agents.run import Runner, RunConfig
from src.orcs.workflow.models import Workflow, Task, WorkflowStatus
from src.orcs.memory.system import MemorySystem, AgentContext
from src.orcs.agent.infrastructure import execute_agent_with_memory, ORCSRunHooks
from src.orcs.agent.registry import AgentRegistry, global_registry
# Import agent factories to ensure they are registered
import src.orcs.agent.factories

# Setup logger
logger = logging.getLogger("orcs.workflow.controller")


class WorkflowController:
    """Central controller for workflow operations"""
    
    def __init__(self, 
                planner_agent: Agent[AgentContext],
                memory_system: MemorySystem,
                agent_registry: Optional[AgentRegistry] = None,
                permission_checker=None):
        """Initialize a workflow controller
        
        Args:
            planner_agent: The agent to use for planning workflows
            memory_system: The memory system to use for storing workflow data
            agent_registry: Registry for specialized agents (uses global registry if None)
            permission_checker: Optional checker for permission validation
        """
        self.planner_agent = planner_agent
        self.memory = memory_system
        self.agent_registry = agent_registry or global_registry
        self.workflows: Dict[str, Workflow] = {}  # Dict[workflow_id, Workflow]
        self.permission_checker = permission_checker
        
        # Log the available agent types
        agent_types = self.agent_registry.list_agent_types()
        logger.info("WorkflowController initialized with %d agent types", len(agent_types))
        if agent_types:
            logger.debug("Available agent types: %s", ", ".join(agent_types))
        else:
            logger.warning("No agent types registered in the agent registry")
        
    async def create_workflow(self, query: str, context_provider=None) -> str:
        """Create a new workflow from a user query
        
        Args:
            query: The user query to create a workflow for
            context_provider: Optional provider for external context
            
        Returns:
            The ID of the created workflow
        """
        logger.info("Creating workflow for query: '%s'", query)
        
        # Create a new workflow
        workflow_id = str(uuid.uuid4())
        logger.debug("Generated workflow ID: %s", workflow_id)
        
        # Fetch external context if provider is supplied
        external_context = {}
        if context_provider:
            logger.debug("Fetching external context")
            external_context = await context_provider.get_context()
            logger.debug("Retrieved external context: %s", json.dumps(external_context)[:100] + "..." 
                        if len(json.dumps(external_context)) > 100 else json.dumps(external_context))
            
        workflow = Workflow(
            id=workflow_id,
            title=f"Workflow for: {query[:50]}{'...' if len(query) > 50 else ''}",
            description=f"Generated workflow for query: {query}",
            query=query
        )
        
        # Store external context in workflow metadata if available
        if external_context:
            logger.debug("Storing external context in workflow metadata")
            workflow.metadata["external_context"] = external_context
        
        # Store the workflow
        self.workflows[workflow_id] = workflow
        
        # Plan the workflow using the planner agent
        logger.info(f"Planning workflow {workflow_id}")
        await self._plan_workflow(workflow)
        
        logger.info(f"Workflow {workflow_id} created with status: {workflow.status.value}")
        return workflow_id
        
    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID
        
        Args:
            workflow_id: The ID of the workflow to get
            
        Returns:
            The workflow if found, None otherwise
            
        Raises:
            PermissionError: If permission check fails
        """
        logger.debug(f"Getting workflow {workflow_id}")
        
        # Check permissions if checker exists
        if self.permission_checker and not self.permission_checker.check_permission('read', workflow_id):
            logger.warning(f"Permission denied to read workflow {workflow_id}")
            raise PermissionError(f"Permission denied to read workflow {workflow_id}")
            
        workflow = self.workflows.get(workflow_id)
        if workflow:
            logger.debug(f"Found workflow {workflow_id}")
        else:
            logger.debug(f"Workflow {workflow_id} not found")
            
        return workflow
        
    async def list_workflows(self) -> Dict[str, Dict[str, Any]]:
        """List all workflows
        
        Returns:
            Dictionary of workflow IDs to summary information
            
        Note:
            If permission_checker is provided, only workflows the user has access to will be returned
        """
        logger.debug("Listing workflows")
        
        workflows_dict = {}
        
        for workflow_id, workflow in self.workflows.items():
            # Skip workflows the user doesn't have access to
            if self.permission_checker and not self.permission_checker.check_permission('list', workflow_id):
                logger.debug(f"Skipping workflow {workflow_id} due to permission check")
                continue
                
            workflows_dict[workflow_id] = {
                "id": workflow.id,
                "title": workflow.title,
                "status": workflow.status.value,
                "created_at": workflow.created_at,
                "query": workflow.query
            }
            
        logger.debug(f"Listed {len(workflows_dict)} workflows")
        return workflows_dict
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """Execute a workflow
        
        Args:
            workflow_id: The ID of the workflow to execute
            
        Returns:
            True if execution started successfully, False otherwise
            
        Raises:
            PermissionError: If permission check fails
        """
        logger.info(f"Executing workflow {workflow_id}")
        
        # Check permissions if checker exists
        if self.permission_checker and not self.permission_checker.check_permission('execute', workflow_id):
            logger.warning(f"Permission denied to execute workflow {workflow_id}")
            raise PermissionError(f"Permission denied to execute workflow {workflow_id}")
            
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.warning(f"Workflow {workflow_id} not found")
            return False
            
        # TODO: Workflow execution would be implemented here
        # For now, just update the status
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now().isoformat()
        logger.info(f"Workflow {workflow_id} status set to {workflow.status.value}")
        
        return True
        
    async def _plan_workflow(self, workflow: Workflow) -> None:
        """Use the planner agent to create tasks for the workflow
        
        Args:
            workflow: The workflow to plan
        """
        logger.debug(f"Planning workflow {workflow.id}")
        
        # Create context for the planner
        context = self.memory.create_agent_context(
            agent_id="planner",
            workflow_id=workflow.id
        )
        logger.debug("Created agent context for planner")
        
        # Set workflow status to planning
        workflow.status = WorkflowStatus.PLANNING
        
        try:
            # Include external context in the query if available
            query = workflow.query
            if "external_context" in workflow.metadata:
                logger.debug("Including external context in query")
                external_context = workflow.metadata["external_context"]
                # Format external context as a string to include in the query
                context_str = "\n".join([f"{k}: {v}" for k, v in external_context.items()])
                # TODO: Reference of user, maybe make it more general
                query = f"{query}\n\nUser Context:\n{context_str}"
            
            # Create run hooks for memory integration
            run_hooks = ORCSRunHooks(self.memory, workflow.id)
            
            # Configure run
            run_config = RunConfig(
                workflow_name=f"Workflow Planning: {workflow.id}",
                model_settings=self.planner_agent.model_settings,
                tracing_disabled=False
            )
            logger.debug("Configured run settings")
            
            # Use the OpenAI Agent SDK Runner to execute the planner agent
            logger.info("Executing planner agent")
            result = await Runner.run(
                starting_agent=self.planner_agent,
                input=query,
                context=context,
                run_config=run_config,
                hooks=run_hooks
            )
            logger.debug("Planner agent execution completed")
            
            # Extract the result content
            result_content = result.final_output
            logger.debug(f"Received result content (length: {len(str(result_content))})")
            
            # Parse the JSON result
            try:
                logger.debug("Parsing JSON result")
                parsed_result = json.loads(result_content)
                tasks_data = parsed_result.get("tasks", [])
                logger.info(f"Retrieved {len(tasks_data)} tasks from planner")
                
                # Process the plan result
                task_id_map = {}  # Map from index to task ID
                
                # First pass: Create all tasks
                logger.debug("Creating tasks")
                for i, task_data in enumerate(tasks_data):
                    task = Task(
                        id=str(uuid.uuid4()),
                        title=task_data["title"],
                        description=task_data["description"],
                        agent_id=task_data["agent_id"]
                    )
                    workflow.add_task(task)
                    task_id_map[i] = task.id
                    logger.debug(f"Created task {task.id}: {task.title}")
                    
                # Second pass: Set up dependencies
                logger.debug("Setting up task dependencies")
                for i, task_data in enumerate(tasks_data):
                    if "dependencies" in task_data and task_data["dependencies"]:
                        task_id = task_id_map[i]
                        task = workflow.get_task(task_id)
                        
                        # Convert dependency indices to task IDs
                        for dep_idx in task_data["dependencies"]:
                            if isinstance(dep_idx, int) and 0 <= dep_idx < len(tasks_data):
                                task.dependencies.append(task_id_map[dep_idx])
                                logger.debug(f"Added dependency {task_id_map[dep_idx]} to task {task_id}")
                
                # Update workflow status
                workflow.status = WorkflowStatus.READY
                logger.info(f"Workflow {workflow.id} planning completed successfully")
                
            except json.JSONDecodeError as e:
                # Handle JSON parsing errors
                logger.error(f"Failed to parse JSON result: {str(e)}")
                workflow.status = WorkflowStatus.FAILED
                workflow.metadata["planning_error"] = f"Invalid JSON result: {str(e)}"
                workflow.metadata["raw_result"] = result_content
                raise ValueError(f"Planner agent returned invalid JSON: {str(e)}")
                
        except Exception as e:
            # If planning fails, mark the workflow as failed
            logger.error(f"Workflow planning failed: {str(e)}")
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["planning_error"] = str(e)
            # Re-raise the exception
            raise