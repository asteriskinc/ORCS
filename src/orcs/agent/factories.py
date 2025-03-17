import logging
from typing import Dict, Any, Optional, List
from agents.agent import Agent
from agents.model_settings import ModelSettings
from agents.tool import function_tool

from orcs.agent.registry import register_agent_type, global_registry
from orcs.memory.system import AgentContext

# Set up logger
logger = logging.getLogger("orcs.agent.factories")

# Default model to use for all agents
DEFAULT_MODEL = "gpt-4o-mini"


@register_agent_type(global_registry)
def research_agent(model: str = DEFAULT_MODEL, 
                 memory_system=None, 
                 workflow_id: Optional[str] = None, 
                 config_provider=None) -> Agent[AgentContext]:
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
    1. Finding and evaluating sources of information
    2. Summarizing complex topics into clear, concise explanations
    3. Identifying patterns and connections between different pieces of information
    4. Providing balanced perspectives on controversial topics
    5. Citing sources and references properly
    
    Always strive to be thorough, accurate, and objective in your research.
    Consider multiple sources and viewpoints before drawing conclusions.
    """
    
    # Define research-specific tools
    @function_tool
    def get_research_context(context, workflow_id: str, query: str) -> str:
        """Get relevant research context for a query
        
        Args:
            context: The run context wrapper
            workflow_id: The ID of the workflow
            query: The research query
            
        Returns:
            A formatted string with research context
        """
        logger.debug("Getting research context for query: %s", query)
        if not memory_system or not workflow_id:
            return "No research context available."
            
        agent_context = context.context
        
        # Get relevant context from memory
        # In a real implementation, this would gather relevant data
        return f"Research context for query: {query}"
    
    # Create and return the agent
    return Agent[AgentContext](
        name="research",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[get_research_context]
    )


@register_agent_type(global_registry)
def writing_agent(model: str = DEFAULT_MODEL, 
                memory_system=None, 
                workflow_id: Optional[str] = None,
                config_provider=None) -> Agent[AgentContext]:
    """Create a writing agent specialized in content creation and documentation.
    
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
    You are a writing agent specialized in creating high-quality content.
    
    Your capabilities include:
    1. Creating engaging and clear content in various formats and styles
    2. Adapting tone and complexity to different audiences
    3. Organizing information logically and coherently
    4. Editing and improving existing content
    5. Following style guides and formatting requirements
    
    Strive for clarity, conciseness, and impact in your writing.
    Always consider the purpose of the content and the needs of the audience.
    """
    
    # Define writing-specific tools
    @function_tool
    def get_writing_materials(context, workflow_id: str, content_type: str) -> str:
        """Get writing materials and resources for a specific content type
        
        Args:
            context: The run context wrapper
            workflow_id: The ID of the workflow
            content_type: The type of content (article, documentation, etc.)
            
        Returns:
            A formatted string with writing resources
        """
        logger.debug("Getting writing materials for content type: %s", content_type)
        if not memory_system or not workflow_id:
            return "No writing materials available."
            
        agent_context = context.context
        
        # Get relevant materials from memory
        # In a real implementation, this would gather relevant templates, guidelines, etc.
        return f"Writing materials for content type: {content_type}"
    
    # Create and return the agent
    return Agent[AgentContext](
        name="writer",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[get_writing_materials]
    )


@register_agent_type(global_registry)
def coding_agent(model: str = DEFAULT_MODEL, 
                memory_system=None, 
                workflow_id: Optional[str] = None,
                config_provider=None) -> Agent[AgentContext]:
    """Create a coding agent specialized in software development and code generation.
    
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
    model_settings = ModelSettings(temperature=0.1)
    
    if config_provider:
        config = config_provider.get_configuration('agent.coding')
        if 'model' in config:
            model = config['model']
            logger.debug("Using custom model: %s", model)
        if 'temperature' in config:
            model_settings.temperature = config['temperature']
            logger.debug("Using custom temperature: %f", model_settings.temperature)
    
    instructions = """
    You are a coding agent specialized in software development and code generation.
    
    Your capabilities include:
    1. Writing clean, efficient, and well-documented code
    2. Debugging and fixing issues in existing code
    3. Explaining complex technical concepts clearly
    4. Following best practices and coding standards
    5. Designing software architecture and data structures
    
    Always prioritize code quality, readability, and maintainability.
    Consider security, performance, and edge cases in your solutions.
    """
    
    # Define coding-specific tools
    @function_tool
    def get_code_context(context, workflow_id: str, language: str, task: str) -> str:
        """Get relevant code context for a programming task
        
        Args:
            context: The run context wrapper
            workflow_id: The ID of the workflow
            language: The programming language
            task: The coding task description
            
        Returns:
            A formatted string with code context
        """
        logger.debug("Getting code context for language '%s' and task: %s", language, task)
        if not memory_system or not workflow_id:
            return "No code context available."
            
        agent_context = context.context
        
        # Get relevant context from memory
        # In a real implementation, this would gather code snippets, documentation, etc.
        return f"Code context for {language} task: {task}"
    
    # Create and return the agent
    return Agent[AgentContext](
        name="coder",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[get_code_context]
    )


@register_agent_type(global_registry)
def data_agent(model: str = DEFAULT_MODEL, 
              memory_system=None, 
              workflow_id: Optional[str] = None,
              config_provider=None) -> Agent[AgentContext]:
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
    You are a data agent specialized in data analysis and processing.
    
    Your capabilities include:
    1. Interpreting and analyzing data sets
    2. Identifying patterns and insights from data
    3. Creating and explaining data visualizations
    4. Processing and cleaning data
    5. Designing data collection methodologies
    
    Always strive for accuracy, clarity, and objectivity in your data work.
    Consider statistical significance, data quality, and appropriate methodologies.
    """
    
    # Define data-specific tools
    @function_tool
    def get_data_context(context, workflow_id: str, data_type: str) -> str:
        """Get relevant data context for analysis
        
        Args:
            context: The run context wrapper
            workflow_id: The ID of the workflow
            data_type: The type of data to analyze
            
        Returns:
            A formatted string with data context
        """
        logger.debug("Getting data context for data type: %s", data_type)
        if not memory_system or not workflow_id:
            return "No data context available."
            
        agent_context = context.context
        
        # Get relevant context from memory
        # In a real implementation, this would gather data descriptions, schemas, etc.
        return f"Data context for {data_type}"
    
    # Create and return the agent
    return Agent[AgentContext](
        name="data_analyst",
        instructions=instructions,
        model=model,
        model_settings=model_settings,
        tools=[get_data_context]
    ) 