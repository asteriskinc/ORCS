#!/usr/bin/env python3
"""
ORCS 2.0 Milestone 1 Demo

This script demonstrates the basic usage of the ORCS 2.0 components
implemented in Milestone 1:
- Memory System
- Workflow and Task Models
- Basic Workflow Controller
- Integration with OpenAI Agent SDK

Requirements:
- OpenAI API key set as environment variable OPENAI_API_KEY
"""

import os
import asyncio
import json
from pprint import pprint

from openai import OpenAI

from src.orcs.memory.system import MemorySystem
from src.orcs.workflow.models import Workflow, Task, WorkflowStatus, TaskStatus
from src.orcs.workflow.controller import WorkflowController
from src.orcs.agent.infrastructure import create_planner_agent


async def main():
    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set it to your OpenAI API key and try again.")
        return
    
    print("=== ORCS 2.0 Milestone 1 Demo ===\n")
    
    # Initialize components
    print("Initializing components...")
    memory = MemorySystem()
    
    # Create a planner agent using the OpenAI Agent SDK
    planner = create_planner_agent(model="gpt-4")
    
    # Create the workflow controller
    controller = WorkflowController(
        planner_agent=planner,
        memory_system=memory
    )
    
    # Create a workflow
    query = input("Enter a query for workflow creation: ")
    if not query:
        query = "Create a tutorial on how to use Python for data analysis"
    
    print(f"\nCreating workflow for query: '{query}'")
    try:
        workflow_id = await controller.create_workflow(query)
        print(f"Workflow created with ID: {workflow_id}")
        
        # Get the workflow details
        workflow = await controller.get_workflow(workflow_id)
        
        # Print workflow details
        print("\n=== Workflow Details ===")
        print(f"Title: {workflow.title}")
        print(f"Status: {workflow.status.value}")
        print(f"Created at: {workflow.created_at}")
        
        # Print tasks
        print("\n=== Tasks ===")
        for task_id, task in workflow.tasks.items():
            print(f"\nTask: {task.title}")
            print(f"  Description: {task.description}")
            print(f"  Agent: {task.agent_id}")
            print(f"  Dependencies: {task.dependencies}")
            
        # Display executable tasks
        print("\n=== Executable Tasks ===")
        for task in workflow.get_executable_tasks():
            print(f"- {task.title}")
            
    except Exception as e:
        print(f"Error creating workflow: {str(e)}")
    
    print("\nDemo completed.")


if __name__ == "__main__":
    asyncio.run(main()) 