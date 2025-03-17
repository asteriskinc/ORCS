import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import json
import logging

from agents.agent import Agent
from agents.run import Runner, RunConfig
from orcs.workflow.models import Workflow, Task, WorkflowStatus
from orcs.memory.system import MemorySystem, AgentContext
from orcs.agent.infrastructure import ORCSRunHooks, ORCSAgentHooks
from orcs.agent.registry import AgentRegistry, global_registry
# Import agent factories to ensure they are registered
import orcs.agent.factories

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
            external_context = workflow.metadata.get("external_context", {})
            if external_context:
                context_str = "\n".join([f"{k}: {v}" for k, v in external_context.items()])
                # TODO: Reference of user, maybe make it more general
                query = f"{query}\n\nUser Context:\n{context_str}"
            
            # Set up hooks for memory integration
            logger.debug("Setting up hooks for memory integration")
            agent_hooks = ORCSAgentHooks(self.memory, workflow.id)
            run_hooks = ORCSRunHooks(self.memory, workflow.id)
            
            # Attach agent hooks to the planner agent
            self.planner_agent.hooks = agent_hooks
            
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
            
            # Work directly with PlanResult object
            try:
                logger.debug("Processing PlanResult object")
                # Get tasks directly from the PlanResult object
                tasks_data = result_content.tasks
                logger.info(f"Retrieved {len(tasks_data)} tasks from planner")
                
                # Process the plan result
                task_id_map = {}  # Map from index to task ID
                
                # First pass: Create all tasks
                logger.debug("Creating tasks")
                for i, task_data in enumerate(tasks_data):
                    # Directly access Pydantic model attributes
                    task = Task(
                        id=str(uuid.uuid4()),
                        title=task_data.title,
                        description=task_data.description,
                        agent_id=task_data.agent_id
                    )
                    workflow.add_task(task)
                    task_id_map[i] = task.id
                    logger.debug(f"Created task {task.id}: {task.title}")
                    
                # Second pass: Set up dependencies
                logger.debug("Setting up task dependencies")
                for i, task_data in enumerate(tasks_data):
                    task_id = task_id_map[i]
                    task = workflow.get_task(task_id)
                    
                    # Directly access dependencies from Pydantic model
                    if task_data.dependencies:
                        for dep_idx in task_data.dependencies:
                            if isinstance(dep_idx, int) and 0 <= dep_idx < len(tasks_data):
                                task.dependencies.append(task_id_map[dep_idx])
                                logger.debug(f"Added dependency {task_id_map[dep_idx]} to task {task_id}")
                
                # Validate the dependency graph for cycles
                has_cycles, cycle_path = self._detect_dependency_cycles(workflow)
                if has_cycles:
                    logger.error(f"Workflow {workflow.id} contains cyclic dependencies: {cycle_path}")
                    workflow.status = WorkflowStatus.FAILED
                    workflow.metadata["planning_error"] = f"Cyclic dependency detected: {cycle_path}"
                    raise ValueError(f"Dependency cycle detected in workflow: {cycle_path}")
                
                # Update workflow status
                workflow.status = WorkflowStatus.READY
                logger.info(f"Workflow {workflow.id} planning completed successfully")
                
            except AttributeError as e:
                # Handle missing attribute errors (e.g., if the model structure doesn't match)
                logger.error(f"Invalid structure in agent output: {str(e)}")
                workflow.status = WorkflowStatus.FAILED
                workflow.metadata["planning_error"] = f"Invalid output structure: {str(e)}"
                raise ValueError(f"Agent output has invalid structure: {str(e)}")
                
        except Exception as e:
            # If planning fails, mark the workflow as failed
            logger.error(f"Workflow planning failed: {str(e)}")
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["planning_error"] = str(e)
            # Re-raise the exception
            raise
    
    def _detect_dependency_cycles(self, workflow: Workflow) -> Tuple[bool, Optional[List[str]]]:
        """Check for cycles in the workflow dependency graph
        
        Args:
            workflow: The workflow to check for cycles
            
        Returns:
            Tuple of (has_cycles, cycle_path) where cycle_path is a list of task IDs in the cycle or None
        """
        # Track visited and in-progress nodes for DFS
        visited = set()
        in_progress = set()
        back_edges = []
        
        def dfs(task_id):
            if task_id in in_progress:
                # Found a cycle
                return True, task_id
            
            if task_id in visited:
                # Already processed this node, no cycle found
                return False, None
            
            # Mark as in-progress
            in_progress.add(task_id)
            
            # Check dependencies
            task = workflow.get_task(task_id)
            if task:
                for dep_id in task.dependencies:
                    has_cycle, cycle_start = dfs(dep_id)
                    if has_cycle:
                        # Add this task to back edges and return
                        back_edges.append(task_id)
                        return True, cycle_start
            
            # Mark as visited and remove from in-progress
            visited.add(task_id)
            in_progress.remove(task_id)
            return False, None
            
        # Check each task for cycles
        for task_id in workflow.tasks:
            has_cycle, cycle_start = dfs(task_id)
            if has_cycle:
                # Reconstruct the cycle path
                cycle_path = back_edges + [cycle_start]
                # Reorder to start with the cycle_start node
                start_idx = cycle_path.index(cycle_start)
                cycle_path = cycle_path[start_idx:] + cycle_path[:start_idx] + [cycle_start]
                return True, cycle_path
                
        return False, None