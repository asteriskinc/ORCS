from typing import Any, Dict, List, Optional
import logging
from abc import ABC, abstractmethod
import time
from datetime import datetime

# Set up logger
logger = logging.getLogger("orcs.metrics.context")

class MetricsContext(ABC):
    """Abstract base class for metrics collection
    
    This provides a standardized interface for collecting metrics
    across different parts of the application.
    """
    
    @abstractmethod
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event with metadata
        
        Args:
            event_type: Type of event (e.g., 'agent_start', 'tool_execution')
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        pass
    
    @abstractmethod
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        pass
    
    @abstractmethod
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start a timer for measuring duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        pass
    
    @abstractmethod
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop a timer and return the duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Duration in seconds
        """
        pass
    
    @abstractmethod
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events
        
        Args:
            event_type: Optional filter for event type
            
        Returns:
            List of recorded events
        """
        pass
    
    @abstractmethod
    def get_metrics(self, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics
        
        Args:
            metric_name: Optional filter for metric name
            
        Returns:
            List of recorded metrics
        """
        pass


class BasicMetricsContext(MetricsContext):
    """Simple in-memory implementation of MetricsContext
    
    Stores events and metrics in memory. Useful for testing and
    development environments.
    """
    
    def __init__(self):
        self.events = []
        self.metrics = []
        self.timers = {}
        logger.info("Initialized BasicMetricsContext")
    
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event with metadata
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        event = {
            "event_type": event_type,
            "resource_id": resource_id,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        self.events.append(event)
        logger.debug("Recorded event: %s for resource %s", event_type, resource_id)
    
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        metric = {
            "metric_name": metric_name,
            "value": value,
            "dimensions": dimensions,
            "timestamp": datetime.now().isoformat()
        }
        self.metrics.append(metric)
        logger.debug("Recorded metric: %s = %f", metric_name, value)
    
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start a timer for measuring duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        timer_key = f"{timer_name}:{resource_id}"
        self.timers[timer_key] = time.time()
        logger.debug("Started timer: %s for resource %s", timer_name, resource_id)
    
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop a timer and return the duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Duration in seconds
        """
        timer_key = f"{timer_name}:{resource_id}"
        if timer_key not in self.timers:
            logger.warning("Timer %s for resource %s not found", timer_name, resource_id)
            return 0.0
        
        start_time = self.timers.pop(timer_key)
        duration = time.time() - start_time
        
        logger.debug("Stopped timer: %s for resource %s, duration: %f seconds", 
                    timer_name, resource_id, duration)
        return duration
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events
        
        Args:
            event_type: Optional filter for event type
            
        Returns:
            List of recorded events
        """
        if event_type:
            return [e for e in self.events if e["event_type"] == event_type]
        return self.events.copy()
    
    def get_metrics(self, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics
        
        Args:
            metric_name: Optional filter for metric name
            
        Returns:
            List of recorded metrics
        """
        if metric_name:
            return [m for m in self.metrics if m["metric_name"] == metric_name]
        return self.metrics.copy()


class CompositeMetricsContext(MetricsContext):
    """Composite implementation that delegates to multiple metric contexts
    
    Allows for sending metrics to multiple systems simultaneously.
    """
    
    def __init__(self, contexts: List[MetricsContext]):
        self.contexts = contexts
        logger.info("Initialized CompositeMetricsContext with %d contexts", len(contexts))
    
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an event with metadata in all contexts
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        for context in self.contexts:
            context.record_event(event_type, resource_id, metadata)
    
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record a metric value in all contexts
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        for context in self.contexts:
            context.record_metric(metric_name, value, dimensions)
    
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start a timer in all contexts
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        for context in self.contexts:
            context.start_timer(timer_name, resource_id)
    
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop a timer in all contexts and return the average duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Average duration in seconds across all contexts
        """
        durations = [context.stop_timer(timer_name, resource_id) for context in self.contexts]
        return sum(durations) / len(durations) if durations else 0.0
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events from all contexts
        
        For composite contexts, this returns events from the first context only.
        Use this method with caution in composite contexts.
        
        Args:
            event_type: Optional filter for event type
            
        Returns:
            List of recorded events from the first context
        """
        if not self.contexts:
            return []
        return self.contexts[0].get_events(event_type)
    
    def get_metrics(self, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics from all contexts
        
        For composite contexts, this returns metrics from the first context only.
        Use this method with caution in composite contexts.
        
        Args:
            metric_name: Optional filter for metric name
            
        Returns:
            List of recorded metrics from the first context
        """
        if not self.contexts:
            return []
        return self.contexts[0].get_metrics(metric_name)


class WorkflowMetricsContext(MetricsContext):
    """Specialized metrics context for workflows
    
    Automatically adds workflow and task dimensions to all metrics.
    """
    
    def __init__(self, base_context: MetricsContext, workflow_id: str):
        """Initialize workflow metrics context
        
        Args:
            base_context: Base metrics context to delegate to
            workflow_id: Workflow ID to associate with metrics
        """
        self.base_context = base_context
        self.workflow_id = workflow_id
        logger.info("Initialized WorkflowMetricsContext for workflow %s", workflow_id)
    
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record a workflow event
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        # Add workflow ID to metadata
        enriched_metadata = metadata.copy()
        enriched_metadata["workflow_id"] = self.workflow_id
        
        self.base_context.record_event(event_type, resource_id, enriched_metadata)
    
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record a workflow metric
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        # Add workflow dimension
        enriched_dimensions = dimensions.copy()
        enriched_dimensions["workflow_id"] = self.workflow_id
        
        self.base_context.record_metric(metric_name, value, enriched_dimensions)
    
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start a workflow timer
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        self.base_context.start_timer(timer_name, resource_id)
    
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop a workflow timer
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Duration in seconds
        """
        return self.base_context.stop_timer(timer_name, resource_id)
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded events
        
        Args:
            event_type: Optional filter for event type
            
        Returns:
            List of recorded events
        """
        events = self.base_context.get_events(event_type)
        if event_type is None:
            # If not filtering by event type, we can filter by workflow ID
            return [e for e in events if e.get("metadata", {}).get("workflow_id") == self.workflow_id]
        return events
    
    def get_metrics(self, metric_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics
        
        Args:
            metric_name: Optional filter for metric name
            
        Returns:
            List of recorded metrics
        """
        metrics = self.base_context.get_metrics(metric_name)
        if metric_name is None:
            # If not filtering by metric name, we can filter by workflow ID
            return [m for m in metrics if m.get("dimensions", {}).get("workflow_id") == self.workflow_id]
        return metrics


class AgentMetricsContext(MetricsContext):
    """Specialized metrics context for agents
    
    Automatically adds agent and workflow dimensions to all metrics.
    """
    
    def __init__(self, base_context: MetricsContext, agent_id: str, workflow_id: str):
        """Initialize agent metrics context
        
        Args:
            base_context: Base metrics context to delegate to
            agent_id: Agent ID to associate with metrics
            workflow_id: Workflow ID to associate with metrics
        """
        self.base_context = base_context
        self.agent_id = agent_id
        self.workflow_id = workflow_id
        logger.info("Initialized AgentMetricsContext for agent %s in workflow %s", 
                   agent_id, workflow_id)
    
    def record_event(self, event_type: str, resource_id: str, metadata: Dict[str, Any]) -> None:
        """Record an agent event
        
        Args:
            event_type: Type of event
            resource_id: ID of the resource associated with the event
            metadata: Additional data about the event
        """
        # Add agent and workflow IDs to metadata
        enriched_metadata = metadata.copy()
        enriched_metadata["agent_id"] = self.agent_id
        enriched_metadata["workflow_id"] = self.workflow_id
        
        self.base_context.record_event(event_type, resource_id, enriched_metadata)
    
    def record_metric(self, metric_name: str, value: float, dimensions: Dict[str, str]) -> None:
        """Record an agent metric
        
        Args:
            metric_name: Name of the metric
            value: Numeric value of the metric
            dimensions: Dimensions for categorizing the metric
        """
        # Add agent and workflow dimensions
        enriched_dimensions = dimensions.copy()
        enriched_dimensions["agent_id"] = self.agent_id
        enriched_dimensions["workflow_id"] = self.workflow_id
        
        self.base_context.record_metric(metric_name, value, enriched_dimensions)
    
    def start_timer(self, timer_name: str, resource_id: str) -> None:
        """Start an agent timer
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
        """
        # Add agent prefix to timer name
        agent_timer_name = f"agent:{self.agent_id}:{timer_name}"
        self.base_context.start_timer(agent_timer_name, resource_id)
    
    def stop_timer(self, timer_name: str, resource_id: str) -> float:
        """Stop an agent timer and return the duration
        
        Args:
            timer_name: Name of the timer
            resource_id: ID of the resource being timed
            
        Returns:
            Duration in seconds
        """
        # Add agent prefix to timer name (same as in start_timer)
        agent_timer_name = f"agent:{self.agent_id}:{timer_name}"
        duration = self.base_context.stop_timer(agent_timer_name, resource_id)
        
        # Also record this as a metric automatically
        self.record_metric(
            metric_name=f"{timer_name}_duration",
            value=duration,
            dimensions={
                "resource_id": resource_id
            }
        )
        
        return duration