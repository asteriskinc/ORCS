#!/usr/bin/env python3
"""
Demo script for the agent registry in ORCS
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

from orcs.memory.system import BasicMemorySystem, MemorySystem
from orcs.workflow.controller import WorkflowController 
from orcs.workflow.orchestrator import WorkflowOrchestrator
from orcs.agent.infrastructure import create_planner_agent
from orcs.agent.registry import global_registry, AgentRegistry
from orcs.workflow.models import WorkflowStatus, Workflow, Task

# Import agent factories to ensure they're registered
import orcs.agent.factories

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_registry_demo")

# Use gpt-4o-mini for testing
MODEL = "gpt-4o-mini"


def detect_cycle(tasks: Dict[str, Task], start_id: str, visited: set = None, path: List[str] = None) -> List[str]:
    """
    Detect cycles in the task dependency graph
    
    Args:
        tasks: Dictionary of tasks indexed by ID
        start_id: ID of the task to start from
        visited: Set of visited task IDs
        path: Current path in the graph
        
    Returns:
        List of task IDs forming a cycle, or empty list if no cycle is found
    """
    if visited is None:
        visited = set()
    if path is None:
        path = []
    
    # This task is already in the current path, which means we found a cycle
    if start_id in path:
        return path[path.index(start_id):] + [start_id]
    
    # If we've already visited this task in another path, no need to check again
    if start_id in visited:
        return []
    
    # Add this task to both the current path and visited set
    path.append(start_id)
    visited.add(start_id)
    
    # If this task doesn't exist, return empty list
    if start_id not in tasks:
        path.pop()
        return []
    
    # Check all dependencies of this task
    for dep_id in tasks[start_id].dependencies:
        if dep_id in tasks:  # Ensure the dependency exists
            cycle = detect_cycle(tasks, dep_id, visited, path.copy())
            if cycle:
                return cycle
    
    return []


def fix_cyclic_dependencies(workflow: Workflow) -> bool:
    """
    Check for and fix cyclic dependencies in the workflow tasks
    
    Args:
        workflow: The workflow to fix
        
    Returns:
        True if fixed successfully, False if still has cycles
    """
    modified = False
    
    # First, remove self-dependencies
    for task_id, task in workflow.tasks.items():
        # Remove self-dependencies
        if task_id in task.dependencies:
            logger.warning(f"Removing self-dependency in task {task_id}")
            task.dependencies.remove(task_id)
            modified = True
        
        # Check for duplicate dependencies
        if len(task.dependencies) != len(set(task.dependencies)):
            logger.warning(f"Removing duplicate dependencies in task {task_id}")
            task.dependencies = list(set(task.dependencies))
            modified = True
        
        # Remove dependencies to non-existent tasks
        invalid_deps = [dep for dep in task.dependencies if dep not in workflow.tasks]
        if invalid_deps:
            logger.warning(f"Removing invalid dependencies {invalid_deps} in task {task_id}")
            task.dependencies = [dep for dep in task.dependencies if dep in workflow.tasks]
            modified = True
            
    # Then detect and fix cycles
    for _ in range(10):  # Limit the number of attempts to prevent infinite loops
        # Find a cycle
        for task_id in workflow.tasks:
            cycle = detect_cycle(workflow.tasks, task_id)
            if cycle:
                # Remove the last dependency to break the cycle
                last_id = cycle[-1]
                prev_id = cycle[-2]
                logger.warning(f"Breaking cycle by removing dependency from {prev_id} to {last_id}")
                
                if last_id in workflow.tasks[prev_id].dependencies:
                    workflow.tasks[prev_id].dependencies.remove(last_id)
                    modified = True
                    break
        else:
            # No cycles found
            return modified
    
    # If we reach here, we may still have cycles
    for task_id in workflow.tasks:
        cycle = detect_cycle(workflow.tasks, task_id)
        if cycle:
            logger.warning(f"Could not fully resolve cycles, remaining cycle: {cycle}")
            return False
    
    return modified


async def main():
    """Run the agent registry demo"""
    logger.info("Starting ORCS Agent Registry Demo")
    
    # Display available agent types
    agent_types = global_registry.list_agent_types()
    logger.info(f"Available agent types: {', '.join(agent_types)}")
    
    # Initialize memory system
    memory = BasicMemorySystem()
    
    # Create planner agent with registry
    planner = create_planner_agent(model=MODEL, agent_registry=global_registry)
    
    # Create workflow controller
    controller = WorkflowController(
        planner_agent=planner,
        memory_system=memory,
        agent_registry=global_registry
    )
    
    # Create workflow orchestrator
    orchestrator = WorkflowOrchestrator(
        memory_system=memory,
        agent_registry=global_registry
    )
    
    # Sample query for creating a workflow
    query = "Create a tutorial on Python data analysis with pandas and matplotlib"
    
    # Create the workflow
    try:
        # Create workflow and generate tasks
        logger.info(f"Creating workflow for query: '{query}'")
        workflow_id = await controller.create_workflow(query)
        
        # Get the workflow - Need to await this since it's an async method
        workflow = await controller.get_workflow(workflow_id)
        
        # Apply the fix for cyclic dependencies
        if fix_cyclic_dependencies(workflow):
            logger.info("Fixed cyclic dependencies in the workflow")
        
        logger.info(f"Created workflow '{workflow.title}' with {len(workflow.tasks)} tasks")
        
        # Print task information
        logger.info("Tasks:")
        for i, (task_id, task) in enumerate(workflow.tasks.items()):
            # Handle dependencies correctly - the dependencies could be indices or task IDs
            if task.dependencies:
                # If the dependencies are already task IDs, use them directly
                # If they're indices, try to map them to task IDs
                try:
                    # Try using dependencies as indices if they're integers
                    if all(isinstance(dep, int) for dep in task.dependencies):
                        # Map integer indices to task IDs
                        task_ids = list(workflow.tasks.keys())
                        deps = ", ".join([task_ids[dep] if dep < len(task_ids) else "unknown" 
                                         for dep in task.dependencies])
                    else:
                        # Dependencies are already task IDs
                        deps = ", ".join(task.dependencies)
                except (TypeError, IndexError):
                    # Fallback if there's any issue
                    deps = str(task.dependencies)
            else:
                deps = "None"
                
            logger.info(f"  {i+1}. {task.title} (Agent: {task.agent_id}, Dependencies: {deps})")
        
        # Execute the workflow if there are tasks
        if workflow.tasks:
            logger.info("Executing workflow...")
            
            # Define a status callback
            async def status_callback(status: Workflow):
                # The status parameter is a Workflow object, not a dictionary
                logger.info(f"Status update: Workflow '{status.title}' is {status.status.value}")
            
            # Execute the workflow
            results = await orchestrator.execute(workflow, status_callback)
            
            # Display results
            logger.info(f"Workflow execution completed with status: {results.get('status', 'unknown')}")
            
            if workflow.status == WorkflowStatus.COMPLETED:
                logger.info("Results summary:")
                # Task results are in results["tasks"] not results["results"]
                for task_id, task_data in results["tasks"].items():
                    task = workflow.tasks[task_id]
                    # Truncate result if it's too long
                    result_str = str(task_data["result"])
                    if len(result_str) > 100:
                        result_str = result_str[:100] + "..."
                    logger.info(f"  {task.title}: {result_str}")
                    
                # Save full results to a file
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                
                # Create a more reasonable filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = os.path.join(output_dir, f"pandas_matplotlib_tutorial_{timestamp}.txt")
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"Workflow: {workflow.title}\n")
                    f.write(f"Query: {query}\n")
                    f.write("-" * 80 + "\n\n")
                    
                    # Write each task result
                    for task_id, task_data in results["tasks"].items():
                        task = workflow.tasks[task_id]
                        f.write(f"Task: {task.title}\n")
                        f.write(f"Agent: {task.agent_id}\n")
                        f.write("-" * 40 + "\n")
                        f.write(f"{task_data['result']}\n\n")
                    
                    # Write full compiled result if available
                    if "final_result" in results:
                        f.write("=" * 80 + "\n")
                        f.write("FINAL RESULT\n")
                        f.write("=" * 80 + "\n")
                        f.write(f"{results['final_result']}\n")
                
                logger.info(f"Full results saved to {output_file}")
            else:
                # Handle failed workflow - use safe dictionary access with a default value
                error_message = results.get("error", "Unknown error")
                logger.error(f"Workflow failed: {error_message}")
        else:
            logger.warning("No tasks were created for the workflow")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 