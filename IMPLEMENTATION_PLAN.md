# ORCS 2.0 Implementation Plan

## Overview
ORCS 2.0 is an advanced agent orchestration system built on top of the OpenAI Agent SDK. This document outlines the implementation plan broken down into strategic milestones.

## Architecture Evaluation

### Strengths
- Clean separation of concerns with modular components
- Unified memory system with proper access controls
- Good support for parallel execution and task dependencies
- Built-in interruption and clarification mechanisms
- Flexible output system with adapter pattern

### Areas for Enhancement
- State persistence/serialization mechanisms
- More robust error handling and recovery systems
- Comprehensive observability/logging infrastructure
- Enhanced callback system for cross-component communication
- Extension hooks for multi-tenant deployments

### Core Architectural Principle: Environment Agnosticism

ORCS is designed to be agnostic about user environments while providing clear extension points for multi-tenant deployments. The core system:

1. Focuses exclusively on orchestration logic
2. Makes no assumptions about user contexts
3. Avoids embedding user/tenant concepts in core components
4. Provides extension points rather than built-in solutions

### Extension Hooks for Multi-User Environments

To accommodate both single-user and multi-tenant deployments, ORCS implements the following extension hooks:

1. **Context Injection Hook**: Allows external systems to provide user-specific context to workflows
2. **Resource Isolation Interface**: Enables external resource management and isolation
3. **Data Isolation Hook**: Provides mechanisms for isolating memory storage between users
4. **Authorization Hook**: Allows integration with external permission systems
5. **Telemetry Hook**: Enables collection of metrics and events
6. **Configuration Provider Hook**: Supports externalized configuration management

## Implementation Milestones

### Milestone 1: Core Foundation
**Objective**: Establish the basic infrastructure and core components leveraging the OpenAI Agent SDK.

**Key Components**:
- [ ] Memory System
  - Basic key-value storage
  - Access control implementation
  - Scope management
  - Data isolation hook
- [ ] Workflow and Task Models
  - Base workflow structure
  - Task definition and metadata
  - Basic state management
  - Context injection hook
- [ ] Basic Workflow Controller
  - Initial planning capabilities using OpenAI Agents
  - Simple workflow creation
  - Basic workflow management
  - Authorization hook
- [ ] Agent Infrastructure Integration
  - Utilize OpenAI's Agent class directly
  - Extend with custom hooks for memory integration
  - Custom RunContextWrapper for our workflows
  - Configuration provider hook

#### Architectural Design: Milestone 1

##### Memory System with Isolation Hook

```python
class MemorySystem:
    """Unified memory system with access controls and scoping"""
    
    def __init__(self, isolation_provider=None):
        self.data = {}  # Key-value store
        self.access_scopes = {}  # Maps keys to their access scopes
        self.isolation_provider = isolation_provider
        
    def _get_isolated_key(self, key: str) -> str:
        """Get key with isolation prefix if provider exists"""
        if not self.isolation_provider:
            return key
            
        isolation_prefix = self.isolation_provider.get_isolation_prefix()
        return f"{isolation_prefix}:{key}"
        
    def store(self, key: str, value: Any, scope: str = "global") -> None:
        """Store data with scope information and optional isolation"""
        isolated_key = self._get_isolated_key(key)
        self.data[isolated_key] = value
        self.access_scopes[isolated_key] = scope
```

##### Workflow Controller with Context Injection and Authorization

```python
class WorkflowController:
    """Central controller for workflow operations"""
    
    def __init__(self, 
                planner_agent: Agent,
                memory_system: MemorySystem,
                permission_checker=None):
        self.planner_agent = planner_agent
        self.memory = memory_system
        self.workflows = {}  # Dict[workflow_id, Workflow]
        self.permission_checker = permission_checker
        
    async def create_workflow(self, 
                            query: str, 
                            context_provider=None) -> str:
        """Create a new workflow from a user query with optional context injection"""
        # Create a new workflow
        workflow_id = str(uuid.uuid4())
        
        # Fetch external context if provider is supplied
        external_context = {}
        if context_provider:
            external_context = await context_provider.get_context()
            
        workflow = Workflow(
            id=workflow_id,
            title=f"Workflow for: {query[:50]}...",
            description=f"Generated workflow for query: {query}",
            query=query,
            external_context=external_context
        )
        
        # Store the workflow
        self.workflows[workflow_id] = workflow
        
        # Plan the workflow using the planner agent
        await self._plan_workflow(workflow)
        
        return workflow_id
        
    async def _plan_workflow(self, workflow: Workflow) -> None:
        """Use the planner agent to create tasks for the workflow"""
        # Create context for the planner
        context = self.memory.create_agent_context(
            agent_id="planner",
            workflow_id=workflow.id
        )
        
        # Use the OpenAI Agent Runner to execute the planner agent
        from agents.run import Runner
        
        plan_result = await Runner.run(
            starting_agent=self.planner_agent,
            input=workflow.query,
            context=context
        )
        
        # Process the plan result (expected to be a list of tasks)
        result_content = plan_result.output
        try:
            tasks_data = json.loads(result_content).get("tasks", [])
            
            for task_data in tasks_data:
                task = Task(
                    id=str(uuid.uuid4()),
                    title=task_data["title"],
                    description=task_data["description"],
                    agent_id=task_data["agent_id"],
                    dependencies=task_data.get("dependencies", [])
                )
                workflow.add_task(task)
                
            # Update workflow status
            workflow.status = WorkflowStatus.READY
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["planning_error"] = str(e)
            # Re-raise the exception
            raise
            
    async def get_workflow(self, workflow_id: str) -> Workflow:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)
```

##### Agent Infrastructure Integration

```python
from agents.agent import Agent
from agents.run import Runner
from agents.run_context import RunContextWrapper
from agents.model_settings import ModelSettings
from agents.lifecycle import RunHooks

class ORCSRunHooks(RunHooks):
    """Hooks to integrate OpenAI Agent SDK with ORCS memory system"""
    
    def __init__(self, memory_system: MemorySystem, workflow_id: str):
        self.memory = memory_system
        self.workflow_id = workflow_id
        
    async def on_agent_run_start(self, run_id: str, agent: Agent) -> None:
        """Captures the start of an agent run and stores info in memory"""
        self.memory.store(
            key=f"agent_run:{run_id}:start",
            value={"timestamp": datetime.now().isoformat(), "agent_name": agent.name},
            scope=f"workflow:{self.workflow_id}"
        )
        
    async def on_agent_run_end(self, run_id: str, result: RunResult) -> None:
        """Captures the end of an agent run and stores results in memory"""
        self.memory.store(
            key=f"agent_run:{run_id}:result",
            value={"output": result.output, "timestamp": datetime.now().isoformat()},
            scope=f"workflow:{self.workflow_id}"
        )

# Function to create a planner agent using OpenAI's Agent
def create_planner_agent() -> Agent:
    """Create a planner agent using OpenAI's Agent SDK"""
    
    planner_instructions = """
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
    - agent_id: The type of agent to use (research, coding, writing, etc.)
    - dependencies: Array of task indices that must be completed first (0-based)
    
    Available agent types:
    - research_agent: For gathering information and conducting research
    - writing_agent: For creating content and documentation
    - coding_agent: For writing and reviewing code
    - data_agent: For data analysis and processing
    """
    
    model_settings = ModelSettings(
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    return Agent(
        name="planner",
        instructions=planner_instructions,
        model="gpt-4",
        model_settings=model_settings
    )
```

### Milestone 2: Basic Orchestration
**Objective**: Implement fundamental workflow orchestration capabilities leveraging the OpenAI Agent SDK.

**Key Components**:
- [ ] Workflow Orchestrator
  - Integration with OpenAI's Runner class
  - Basic dependency resolution
  - Sequential task execution
  - Task lifecycle management
  - Resource isolation interface
- [ ] Output System
  - Leverage OpenAI Agent output capabilities
  - Result adaptation and transformation
  - Basic result collection
  - Simple output formatting
  - Initial storage mechanisms
- [ ] Planner Integration
  - Custom agent creation for planning
  - Task decomposition
  - Basic planning strategies
  - Simple workflow generation

#### Architectural Design: Milestone 2

##### Workflow Orchestrator with Resource Management Hook

```python
from agents.agent import Agent
from agents.run import Runner, RunConfig
from agents.lifecycle import RunHooks

class WorkflowOrchestrator:
    """Orchestrates workflow execution with dependency management"""
    
    def __init__(self, 
                memory_system: MemorySystem,
                agent_registry: Dict[str, Agent],
                resource_manager=None,
                telemetry_collector=None):
        self.memory = memory_system
        self.agent_registry = agent_registry
        self.resource_manager = resource_manager
        self.telemetry_collector = telemetry_collector
        
    async def execute(self, 
                     workflow: Workflow, 
                     status_callback: Callable = None) -> Dict[str, Any]:
        """Execute a workflow respecting dependencies with resource management"""
        # Allocate resources if manager is provided
        if self.resource_manager:
            resources_allocated = await self.resource_manager.allocate_resources(
                workflow.id, workflow.metadata.get("resource_requirements", {})
            )
            if not resources_allocated:
                workflow.status = WorkflowStatus.FAILED
                workflow.metadata["error"] = "Failed to allocate resources"
                return self._create_output(workflow)
                
        try:
            # Initialize workflow execution
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now().isoformat()
            
            # Record telemetry if collector exists
            if self.telemetry_collector:
                await self.telemetry_collector.record_event(
                    event_type='workflow_started',
                    resource_id=workflow.id,
                    metadata={
                        'query': workflow.query,
                        'timestamp': workflow.started_at
                    }
                )
            
            # Get the tasks in execution order
            tasks = self._get_execution_order(workflow)
            
            # Execute each task in order
            for task in tasks:
                await self._execute_task(workflow, task, status_callback)
                
                # Check if workflow was stopped/paused
                if workflow.status != WorkflowStatus.RUNNING:
                    break
            
            # If all tasks completed, mark workflow as completed
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now().isoformat()
                
                # Record workflow completion
                if self.telemetry_collector:
                    await self.telemetry_collector.record_event(
                        event_type='workflow_completed',
                        resource_id=workflow.id,
                        metadata={
                            'timestamp': workflow.completed_at,
                            'duration': time.time() - datetime.fromisoformat(workflow.started_at).timestamp()
                        }
                    )
            
            return self._create_output(workflow)
        except Exception as e:
            # Handle errors
            workflow.status = WorkflowStatus.FAILED
            workflow.metadata["error"] = str(e)
            
            # Record workflow failure
            if self.telemetry_collector:
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
                await self.resource_manager.release_resources(workflow.id)
                
    async def _execute_task(self, 
                          workflow: Workflow, 
                          task: Task, 
                          status_callback: Callable = None) -> None:
        """Execute a single task with telemetry using OpenAI Agent SDK"""
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        # Create agent context
        context = self.memory.create_agent_context(
            agent_id=task.agent_id,
            workflow_id=workflow.id
        )
        
        # Get the agent from registry
        agent = self.agent_registry.get(task.agent_id)
        if not agent:
            raise ValueError(f"Agent {task.agent_id} not found in registry")
        
        # Create run hooks for memory integration
        hooks = ORCSRunHooks(self.memory, workflow.id)
        
        # Configure run
        run_config = RunConfig(
            workflow_name=f"Task: {task.title}",
            model_settings=agent.model_settings,
            tracing_disabled=False
        )
        
        # Record task started telemetry
        if self.telemetry_collector:
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
            # Use OpenAI's Runner to execute the agent
            result = await Runner.run(
                starting_agent=agent,
                input=task.description,
                context=context,
                config=run_config,
                hooks=hooks
            )
            
            # Store task result
            task.result = result.output
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            
            # Store result in memory
            self.memory.store(
                key=f"task_result:{task.id}",
                value=task.result,
                scope=f"workflow:{workflow.id}"
            )
            
            # Record task completed telemetry
            if self.telemetry_collector:
                await self.telemetry_collector.record_event(
                    event_type='task_completed',
                    resource_id=task.id,
                    metadata={
                        'workflow_id': workflow.id,
                        'duration': time.time() - datetime.fromisoformat(task.started_at).timestamp(),
                        'timestamp': task.completed_at
                    }
                )
                
            # Call status callback if provided
            if status_callback:
                await status_callback(workflow, task)
                
        except Exception as e:
            # Update task status
            task.status = TaskStatus.FAILED
            task.error = str(e)
            
            # Record task failed telemetry
            if self.telemetry_collector:
                await self.telemetry_collector.record_event(
                    event_type='task_failed',
                    resource_id=task.id,
                    metadata={
                        'workflow_id': workflow.id,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                )
                
            # Call status callback if provided
            if status_callback:
                await status_callback(workflow, task)
                
            # Re-raise the exception
            raise
```

### Milestone 3: Parallel Execution & Advanced Orchestration
**Objective**: Enable concurrent task execution and enhance orchestration capabilities.

**Key Components**:
- [ ] Parallel Execution
  - Concurrent task handling
  - Resource management
  - Execution optimization
- [ ] DAG Management
  - Complex dependency graphs
  - Cycle detection
  - Execution order optimization
- [ ] Status Tracking
  - Real-time status updates
  - Progress monitoring
  - Performance metrics
- [ ] Error Handling
  - Basic error recovery
  - Retry mechanisms
  - Failure isolation

### Milestone 4: Interactive Control
**Objective**: Implement user interaction and control mechanisms.

**Key Components**:
- [ ] Workflow Control
  - Pause/resume functionality
  - State preservation
  - Execution control
- [ ] Task Management
  - Individual task control
  - Task state management
  - Priority handling
- [ ] Interruption System
  - Interruption processing
  - Context switching
  - State preservation
- [ ] Clarification System
  - Request handling
  - Response processing
  - Context updates

### Milestone 5: Memory & Context
**Objective**: Enhance memory management and context handling.

**Key Components**:
- [ ] Advanced Memory System
  - Enhanced scoping mechanisms
  - Memory optimization
  - Access patterns
- [ ] Context Management
  - Context building
  - Information sharing
  - State management
- [ ] Memory Features
  - Snapshots
  - Versioning
  - Recovery mechanisms
- [ ] Cross-Task Communication
  - Data sharing protocols
  - Information flow control
  - Context synchronization

### Milestone 6: Output & Integration
**Objective**: Implement comprehensive output handling and system integration.

**Key Components**:
- [ ] Output Framework
  - Multiple format support
  - Adapter system
  - Transformation pipeline
- [ ] Progressive Results
  - Partial result handling
  - Update mechanisms
  - Stream processing
- [ ] Result Processing
  - Aggregation system
  - Result validation
  - Quality checks
- [ ] Visualization
  - Basic visualizations
  - Data formatting
  - UI integration

### Milestone 7: Advanced Features
**Objective**: Implement sophisticated orchestration capabilities.

**Key Components**:
- [ ] Dynamic Planning
  - Real-time plan updates
  - Adaptive execution
  - Strategy optimization
- [ ] Iterative Processing
  - Result refinement
  - Quality improvement
  - Progressive enhancement
- [ ] Evaluation System
  - Result assessment
  - Gap analysis
  - Quality metrics
- [ ] Learning System
  - Pattern recognition
  - Optimization learning
  - Strategy adaptation

### Milestone 8: System Integration & Hardening
**Objective**: Finalize system integration and enhance reliability.

**Key Components**:
- [ ] Error Management
  - Comprehensive recovery
  - System resilience
  - Failure handling
- [ ] Observability
  - Logging infrastructure
  - Monitoring systems
  - Debug capabilities
- [ ] Performance
  - System optimization
  - Resource management
  - Scaling capabilities
- [ ] SDK Integration
  - API finalization
  - Documentation
  - Example implementations

## Timeline and Dependencies
- Each milestone is expected to take 2-4 weeks depending on complexity
- Milestones 1-3 are sequential and must be completed in order
- Milestones 4-7 can be partially parallelized based on resource availability
- Milestone 8 should begin alongside Milestone 6 and continue through project completion

## Success Criteria
- All components pass integration tests
- System can handle complex workflows with multiple agents
- Interactive features work reliably
- Performance meets target metrics
- Documentation is complete and comprehensive
- SDK is ready for external use

## Next Steps
1. Begin with Milestone 1 implementation
2. Set up development environment and testing infrastructure
3. Create detailed technical specifications for each component
4. Establish regular review checkpoints 

## Integration Examples for Multi-User Environments

### User Context Provider Example

```python
class UserContextProvider:
    """Provides user-specific context for workflows"""
    
    def __init__(self, user_id: str, user_db):
        self.user_id = user_id
        self.user_db = user_db
        
    async def get_context(self) -> Dict[str, Any]:
        """Get user-specific context for workflow execution"""
        user = await self.user_db.get_user(self.user_id)
        return {
            'preferences': user.preferences,
            'history': user.previous_queries,
            'permissions': user.permission_levels
        }
```

### Data Isolation Provider Example

```python
class UserIsolationProvider:
    """Provides isolation for user data"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
    def get_isolation_prefix(self) -> str:
        """Get prefix for isolating user data"""
        return f"user:{self.user_id}"
```

### Permission Checker Example

```python
class UserPermissionChecker:
    """Checks user permissions for operations"""
    
    def __init__(self, user_id: str, permission_service):
        self.user_id = user_id
        self.permission_service = permission_service
        
    def check_permission(self, operation: str, resource_id: str) -> bool:
        """Check if user has permission for an operation"""
        return self.permission_service.has_permission(
            self.user_id, operation, resource_id
        )
```

### Resource Manager Example

```python
class UserResourceManager:
    """Manages resources for users"""
    
    def __init__(self, user_id: str, quota_service):
        self.user_id = user_id
        self.quota_service = quota_service
        
    async def allocate_resources(self, 
                               workflow_id: str, 
                               requirements: Dict[str, Any]) -> bool:
        """Check if user has sufficient quota and allocate resources"""
        return await self.quota_service.allocate_resources(
            self.user_id, workflow_id, requirements
        )
        
    async def release_resources(self, workflow_id: str) -> None:
        """Release allocated resources"""
        await self.quota_service.release_resources(
            self.user_id, workflow_id
        )
```

### Multi-User Integration Example

```python
async def handle_user_workflow(user_id: str, query: str):
    """Integrate ORCS in a multi-user environment"""
    
    # Create user-specific providers
    context_provider = UserContextProvider(user_id, user_db)
    isolation_provider = UserIsolationProvider(user_id)
    permission_checker = UserPermissionChecker(user_id, permission_service)
    resource_manager = UserResourceManager(user_id, quota_service)
    telemetry_collector = UserTelemetryCollector(user_id)
    config_provider = UserConfigProvider(user_id)
    
    # Initialize ORCS with user-specific providers
    memory_system = MemorySystem(isolation_provider=isolation_provider)
    
    controller = WorkflowController(
        planner_agent=PlannerAgent(
            model="gpt-4",
            config_provider=config_provider
        ),
        memory_system=memory_system,
        permission_checker=permission_checker
    )
    
    orchestrator = WorkflowOrchestrator(
        memory_system=memory_system,
        resource_manager=resource_manager,
        telemetry_collector=telemetry_collector
    )
    
    # Create and execute workflow
    workflow_id = await controller.create_workflow(
        query=query,
        context_provider=context_provider
    )
    
    workflow = await controller.get_workflow(workflow_id)
    result = await orchestrator.execute(workflow)
    
    return result 