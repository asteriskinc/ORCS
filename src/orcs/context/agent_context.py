from typing import Dict, Any, Optional
import logging
from uuid import uuid4

# Set up logger
logger = logging.getLogger("orcs.context.agent_context")

class AgentContext:
    """Base class for agent contexts
    
    This provides a standardized base context that can be used as the user context
    in RunContextWrapper. All specific context implementations should extend this.
    """
    
    def __init__(self, agent_id: Optional[str] = None, workflow_id: Optional[str] = None):
        """Initialize the agent context
        
        Args:
            agent_id: ID of the agent (defaults to generated UUID)
            workflow_id: ID of the workflow (defaults to generated UUID)
        """
        self.agent_id = agent_id or str(uuid4())
        self.workflow_id = workflow_id or str(uuid4())
        self.metadata: Dict[str, Any] = {}
        logger.debug("Initialized AgentContext for agent '%s' in workflow '%s'", 
                    self.agent_id, self.workflow_id)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value
        
        Args:
            key: Metadata key
            default: Default value if key doesn't exist
            
        Returns:
            The metadata value or default
        """
        if key is None:
            return self.metadata.copy()
        return self.metadata.get(key, default)
    
    def has_metadata(self, key: str) -> bool:
        """Check if a metadata key exists
        
        Args:
            key: Metadata key
            
        Returns:
            True if the key exists
        """
        return key in self.metadata
    
    def remove_metadata(self, key: str) -> None:
        """Remove a metadata value
        
        Args:
            key: Metadata key
        """
        if key in self.metadata:
            del self.metadata[key] 