#!/usr/bin/env python3
"""
Demo script for the agent registry in ORCS
"""

import asyncio
import logging
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from orcs.memory.system import MemorySystem
from orcs.workflow.controller import WorkflowController 
from orcs.workflow.orchestrator import WorkflowOrchestrator
from orcs.agent.infrastructure import create_planner_agent
from orcs.agent.registry import global_registry, AgentRegistry
from orcs.workflow.models import WorkflowStatus

# Import agent factories to ensure they're registered
import orcs.agent.factories

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_registry_demo")

# Use gpt-4o-mini for testing
MODEL = "gpt-4o-mini"


async def main():
    """Run the agent registry demo"""
    logger.info("Starting ORCS Agent Registry Demo")
    
    # Display available agent types
    agent_types = global_registry.list_agent_types()
    logger.info(f"Available agent types: {', '.join(agent_types)}")
    
    # Initialize memory system
    memory = MemorySystem()
    
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
            async def status_callback(status: Dict[str, Any]):
                logger.info(f"Status update: {status['message']}")
            
            # Execute the workflow
            results = await orchestrator.execute(workflow, status_callback)
            
            # Display results
            logger.info(f"Workflow execution completed with status: {results['status']}")
            
            if workflow.status == WorkflowStatus.COMPLETED:
                logger.info("Results summary:")
                for task_id, result in results["results"].items():
                    task = workflow.tasks[task_id]
                    # Truncate result if it's too long
                    result_str = str(result)
                    if len(result_str) > 100:
                        result_str = result_str[:100] + "..."
                    logger.info(f"  {task.title}: {result_str}")
            else:
                logger.error(f"Workflow failed: {results['metadata']['error']}")
        else:
            logger.warning("No tasks were created for the workflow")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 