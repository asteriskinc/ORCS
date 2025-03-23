from .agent_context import AgentContext
from .metrics_context import MetricsAgentContext

# Default context instance
_default_context = None

def get_default_context() -> AgentContext:
    """Get the default context
    
    Returns:
        The default context
    """
    global _default_context
    if _default_context is None:
        _default_context = MetricsAgentContext()
    return _default_context

def set_default_context(context: AgentContext) -> None:
    """Set the default context
    
    Args:
        context: The context to set as default
    """
    global _default_context
    _default_context = context

__all__ = [
    "AgentContext",
    "MetricsAgentContext",
    "get_default_context",
    "set_default_context"
] 