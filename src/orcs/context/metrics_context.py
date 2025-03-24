from typing import Dict, Any, Optional, List
import logging
import time
from datetime import datetime

from orcs.context.agent_context import AgentContext
from orcs.metrics.context import MetricsContext, BasicMetricsContext

# Set up logger
logger = logging.getLogger("orcs.context.metrics_context")

class MetricsAgentContext(AgentContext):
    """Agent context with metrics capabilities
    
    This extends the base AgentContext to add metrics functionality.
    It implements the full MetricsContext API by delegating to a
    wrapped metrics implementation.
    """
    
    def __init__(self, 
                metrics_context: MetricsContext,
                agent_id: str,
                workflow_id: str):
        """Initialize the metrics agent context
        
        Args:
            metrics_context: The metrics implementation to use
            agent_id: ID of the agent
            workflow_id: ID of the workflow
        """
        super().__init__(agent_id=agent_id, workflow_id=workflow_id)
        
        # Use the provided metrics implementation
        self.metrics = metrics_context
        logger.debug("Initialized MetricsAgentContext with metrics implementation %s", 
                    self.metrics.__class__.__name__)
    
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event with metadata
        
        Args:
            event_type: Type of event (e.g., 'agent_start', 'tool_execution')
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        # Add agent and workflow IDs to metadata if not present
        enriched_metadata = self._enrich_metadata(metadata)
        self.metrics.record_event(event_type, resource_id, enriched_metadata)
    
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        # Add agent and workflow dimensions if not present
        enriched_dimensions = self._enrich_dimensions(dimensions)
        self.metrics.record_metric(metric_name, value, enriched_dimensions)
    
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start a timer for measuring duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        self.metrics.start_timer(timer_name, resource_id)
    
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop a timer and return the duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Duration in seconds
        """
        return self.metrics.stop_timer(timer_name, resource_id)
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events
        
        Args:
            event_type: Optional filter for event type
            
        Returns:
            List of recorded events
        """
        return self.metrics.get_events(event_type)
    
    def get_metrics(self, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics
        
        Args:
            metric_name: Optional filter for metric name
            
        Returns:
            List of recorded metrics
        """
        return self.metrics.get_metrics(metric_name)
        
    def _enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich metadata with agent and workflow IDs
        
        Args:
            metadata: Original metadata dictionary
            
        Returns:
            Enriched metadata dictionary
        """
        enriched = metadata.copy()
        if "agent_id" not in enriched:
            enriched["agent_id"] = self.agent_id
        if "workflow_id" not in enriched:
            enriched["workflow_id"] = self.workflow_id
        return enriched
        
    def _enrich_dimensions(self, dimensions: Dict[str, str]) -> Dict[str, str]:
        """Enrich dimensions with agent and workflow IDs
        
        Args:
            dimensions: Original dimensions dictionary
            
        Returns:
            Enriched dimensions dictionary
        """
        enriched = dimensions.copy()
        if "agent_id" not in enriched:
            enriched["agent_id"] = self.agent_id
        if "workflow_id" not in enriched:
            enriched["workflow_id"] = self.workflow_id
        return enriched

    @classmethod
    def create_with_basic_metrics(cls, agent_id: str, workflow_id: str) -> "MetricsAgentContext":
        """Create a MetricsAgentContext with a BasicMetricsContext
        
        Factory method for creating a context with the default metrics implementation.
        Makes the default choice explicit rather than implicit.
        
        Args:
            agent_id: ID of the agent
            workflow_id: ID of the workflow
            
        Returns:
            MetricsAgentContext with BasicMetricsContext
        """
        return cls(metrics_context=BasicMetricsContext(), 
                  agent_id=agent_id, 
                  workflow_id=workflow_id) 