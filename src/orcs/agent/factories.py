import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from agents.agent import Agent
from agents.model_settings import ModelSettings
from agents.tool import function_tool
from agents.run_context import RunContextWrapper

from orcs.agent.registry import register_agent_type, global_registry
from orcs.context.metrics_context import MetricsAgentContext

# Set up logger
logger = logging.getLogger("orcs.agent.factories")

# Default model to use for all agents
DEFAULT_MODEL = "gpt-4o-mini"

# Define structured output types for each agent
class ResearchOutput(BaseModel):
    findings: List[str]
    summary: str
    sources: List[str]
    confidence_level: str

class WritingOutput(BaseModel):
    content: str
    title: str
    summary: str
    sections: List[str]

class CodeOutput(BaseModel):
    code: str
    language: str
    explanation: str
    test_cases: List[str]

class DataOutput(BaseModel):
    analysis: str
    insights: List[str]
    data_summary: str
    visualization_suggestions: List[str]


@register_agent_type(global_registry)
def research_agent(model: str = DEFAULT_MODEL, 
                 memory_system=None, 
                 workflow_id: Optional[str] = None, 
                 config_provider=None) -> Agent[MetricsAgentContext]:
    """Create a research agent specialized in gathering and analyzing information.
    
    Args:
        model: The model to use
        memory_system: The memory system to use
        workflow_id: The ID of the workflow
        config_provider: Optional configuration provider
        
    Returns:
        An Agent configured for research tasks
    """
    logger.info("Creating research agent with model '%s'", model)
    
    # Apply configuration if provider exists
    model_settings = ModelSettings(temperature=0.1)
    
    if config_provider:
        config = config_provider.get_configuration('agent.research')
        if 'model' in config:
            model = config['model']
            logger.debug("Using custom model: %s", model)
        if 'temperature' in config:
            model_settings.temperature = config['temperature']
            logger.debug("Using custom temperature: %f", model_settings.temperature)
    
    instructions = """
    You are a research agent specialized in gathering, analyzing, and synthesizing information.
    
    Your capabilities include:
    1. Searching for relevant information
    2. Analyzing data and identifying patterns
    3. Summarizing complex topics
    4. Providing well-organized findings
    
    Structure your output with:
    - findings: Array of key findings (required)
    - summary: A concise summary (required)
    - sources: Array of sources for your information (required, provide an empty array if none)
    - confidence_level: Your level of confidence in the findings (required, use "low", "medium", or "high")
    """
    
    @function_tool
    def get_research_context(context: RunContextWrapper[MetricsAgentContext], workflow_id: str, query: str) -> str:
        """Retrieve research context from memory
        
        Args:
            context: The agent context
            workflow_id: The workflow ID
            query: The research query
            
        Returns:
            Context information related to the research query
        """
        logger.debug("Getting research context for workflow '%s' with query '%s'", workflow_id, query)
        if memory_system and workflow_id:
            try:
                # Get relevant memory items for this research query
                memory_data = memory_system.search(
                    workflow_id=workflow_id,
                    query=query,
                    limit=5
                )
                if memory_data:
                    return f"Research context:\n{memory_data}"
                else:
                    return "No existing research context found."
            except Exception as e:
                logger.error("Error retrieving research context: %s", str(e))
                return f"Error retrieving context: {str(e)}"
        return "No memory system available for research context."
    
    # Create and return the agent
    return Agent[MetricsAgentContext](
        name="research_agent",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[],
        output_type=ResearchOutput
    )


@register_agent_type(global_registry)
def writing_agent(model: str = DEFAULT_MODEL, 
                memory_system=None, 
                workflow_id: Optional[str] = None,
                config_provider=None) -> Agent[MetricsAgentContext]:
    """Create a writing agent specialized in content creation.
    
    Args:
        model: The model to use
        memory_system: The memory system to use
        workflow_id: The ID of the workflow
        config_provider: Optional configuration provider
        
    Returns:
        An Agent configured for writing tasks
    """
    logger.info("Creating writing agent with model '%s'", model)
    
    # Apply configuration if provider exists
    model_settings = ModelSettings(temperature=0.7)
    
    if config_provider:
        config = config_provider.get_configuration('agent.writing')
        if 'model' in config:
            model = config['model']
            logger.debug("Using custom model: %s", model)
        if 'temperature' in config:
            model_settings.temperature = config['temperature']
            logger.debug("Using custom temperature: %f", model_settings.temperature)
    
    instructions = """
    You are a writing agent specialized in creating clear, engaging, and well-structured content.
    
    Your capabilities include:
    1. Creating various types of content (articles, reports, documentation, etc.)
    2. Adapting tone and style to different audiences
    3. Organizing information logically
    4. Generating engaging and appropriate titles
    
    Structure your output with:
    - content: The well-organized main content (required)
    - title: A compelling title (required)
    - summary: A brief summary of the content (required, can be empty string if not applicable)
    - sections: Array of section headings (required, provide an empty array if not applicable)
    """
    
    @function_tool
    def get_writing_materials(context: RunContextWrapper[MetricsAgentContext], workflow_id: str, content_type: str) -> str:
        """Retrieve writing materials from memory
        
        Args:
            context: The agent context
            workflow_id: The workflow ID
            content_type: The type of content being written
            
        Returns:
            Materials related to the writing task
        """
        logger.debug("Getting writing materials for workflow '%s' with type '%s'", workflow_id, content_type)
        if memory_system and workflow_id:
            try:
                # Get relevant memory items for this writing task
                memory_data = memory_system.search(
                    workflow_id=workflow_id,
                    query=f"writing materials for {content_type}",
                    limit=5
                )
                if memory_data:
                    return f"Writing materials:\n{memory_data}"
                else:
                    return "No existing writing materials found."
            except Exception as e:
                logger.error("Error retrieving writing materials: %s", str(e))
                return f"Error retrieving materials: {str(e)}"
        return "No memory system available for writing materials."
    
    # Create and return the agent
    return Agent[MetricsAgentContext](
        name="writing_agent",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[],
        output_type=WritingOutput
    )


@register_agent_type(global_registry)
def coding_agent(model: str = DEFAULT_MODEL, 
                memory_system=None, 
                workflow_id: Optional[str] = None,
                config_provider=None) -> Agent[MetricsAgentContext]:
    """Create a coding agent specialized in writing and reviewing code.
    
    Args:
        model: The model to use
        memory_system: The memory system to use
        workflow_id: The ID of the workflow
        config_provider: Optional configuration provider
        
    Returns:
        An Agent configured for coding tasks
    """
    logger.info("Creating coding agent with model '%s'", model)
    
    # Apply configuration if provider exists
    model_settings = ModelSettings(temperature=0.3)
    
    if config_provider:
        config = config_provider.get_configuration('agent.coding')
        if 'model' in config:
            model = config['model']
            logger.debug("Using custom model: %s", model)
        if 'temperature' in config:
            model_settings.temperature = config['temperature']
            logger.debug("Using custom temperature: %f", model_settings.temperature)
    
    instructions = """
    You are a coding agent specialized in writing clean, efficient, and well-documented code.
    
    Your capabilities include:
    1. Writing code in various programming languages
    2. Explaining code functionality
    3. Troubleshooting and debugging
    4. Suggesting test cases
    
    Structure your output with:
    - code: The complete code implementation (required)
    - language: The programming language used (required)
    - explanation: An explanation of how the code works (required)
    - test_cases: Array of suggested test cases (required, provide an empty array if not applicable)
    """
    
    @function_tool
    def get_code_context(context: RunContextWrapper[MetricsAgentContext], workflow_id: str, language: str, task: str) -> str:
        """Retrieve code context from memory
        
        Args:
            context: The agent context
            workflow_id: The workflow ID
            language: The programming language
            task: The coding task description
            
        Returns:
            Context information related to the coding task
        """
        logger.debug("Getting code context for workflow '%s' with language '%s'", workflow_id, language)
        if memory_system and workflow_id:
            try:
                # Get relevant memory items for this coding task
                memory_data = memory_system.search(
                    workflow_id=workflow_id,
                    query=f"{language} code for {task}",
                    limit=5
                )
                if memory_data:
                    return f"Code context:\n{memory_data}"
                else:
                    return f"No existing code context found for {language}."
            except Exception as e:
                logger.error("Error retrieving code context: %s", str(e))
                return f"Error retrieving context: {str(e)}"
        return "No memory system available for code context."
    
    # Create and return the agent
    return Agent[MetricsAgentContext](
        name="coding_agent",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[],
        output_type=CodeOutput
    )


@register_agent_type(global_registry)
def data_agent(model: str = DEFAULT_MODEL, 
              memory_system=None, 
              workflow_id: Optional[str] = None,
              config_provider=None) -> Agent[MetricsAgentContext]:
    """Create a data agent specialized in data analysis and processing.
    
    Args:
        model: The model to use
        memory_system: The memory system to use
        workflow_id: The ID of the workflow
        config_provider: Optional configuration provider
        
    Returns:
        An Agent configured for data tasks
    """
    logger.info("Creating data agent with model '%s'", model)
    
    # Apply configuration if provider exists
    model_settings = ModelSettings(temperature=0.2)
    
    if config_provider:
        config = config_provider.get_configuration('agent.data')
        if 'model' in config:
            model = config['model']
            logger.debug("Using custom model: %s", model)
        if 'temperature' in config:
            model_settings.temperature = config['temperature']
            logger.debug("Using custom temperature: %f", model_settings.temperature)
    
    instructions = """
    You are a data agent specialized in analyzing and extracting insights from data.
    
    Your capabilities include:
    1. Analyzing data patterns and trends
    2. Drawing insights from complex datasets
    3. Suggesting visualization approaches
    4. Providing clear data summaries
    
    Structure your output with:
    - analysis: A comprehensive analysis of the data (required)
    - insights: Array of key insights from the data (required)
    - data_summary: A concise summary of the data (required)
    - visualization_suggestions: Array of visualization suggestions (required, provide an empty array if not applicable)
    """
    
    @function_tool
    def get_data_context(context: RunContextWrapper[MetricsAgentContext], workflow_id: str, data_type: str) -> str:
        """Retrieve data context from memory
        
        Args:
            context: The agent context
            workflow_id: The workflow ID
            data_type: The type of data being analyzed
            
        Returns:
            Context information related to the data task
        """
        logger.debug("Getting data context for workflow '%s' with type '%s'", workflow_id, data_type)
        if memory_system and workflow_id:
            try:
                # Get relevant memory items for this data task
                memory_data = memory_system.search(
                    workflow_id=workflow_id,
                    query=f"data analysis for {}",
                    limit=5
                )
                if memory_data:
                    return f"Data context:\n{memory_data}"
                else:
                    return f"No existing data context found for {data_type}."
            except Exception as e:
                logger.error("Error retrieving data context: %s", str(e))
                return f"Error retrieving context: {str(e)}"
        return "No memory system available for data context."
    
    # Create and return the agent
    return Agent[MetricsAgentContext](
        name="data_agent",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[],
        output_type=DataOutput
    ) 