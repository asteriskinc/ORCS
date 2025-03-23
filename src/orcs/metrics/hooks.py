from typing import Any, Dict, Optional
import logging
import time
import uuid

from agents.agent import Agent
from agents.tool import Tool
from agents.run_context import RunContextWrapper
from agents.lifecycle import RunHooks, AgentHooks
from agents import get_current_trace

from orcs.metrics.context import MetricsContext

# Set up logger
logger = logging.getLogger("orcs.metrics.hooks")


class MetricsAgentHooks(AgentHooks):
    """Hooks for collecting agent metrics
    
    These hooks record events and metrics for agent lifecycle events.
    """
    
    def __init__(self, metrics_context: MetricsContext, workflow_id: str = "unknown"):
        """Initialize the agent hooks
        
        Args:
            metrics_context: The metrics context to use (default: global default)
            workflow_id: The ID of the workflow
        """
        super().__init__()
        logger.debug("Initializing MetricsAgentHooks for workflow '%s'", workflow_id)
        self.metrics = metrics_context
        self.workflow_id = workflow_id
        
    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Called when an agent starts executing
        
        Args:
            context: The run context wrapper
            agent: The agent that started
        """
        logger.info("Agent '%s' starting in workflow '%s'", 
                   agent.name, self.workflow_id)
                   
        # Start a timer for the agent
        self.metrics.start_timer("agent_execution", agent.name)
        
        # Record agent start event
        self.metrics.record_event(
            event_type="agent_start",
            resource_id=agent.name,
            metadata={
                "workflow_id": self.workflow_id,
                "agent_type": agent.__class__.__name__,
                "timestamp": time.time()
            }
        )
        
    async def on_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        """Called when an agent finishes executing
        
        Args:
            context: The run context wrapper
            agent: The agent that finished
            output: The output of the agent
        """
        logger.info("Agent '%s' completed in workflow '%s'", 
                   agent.name, self.workflow_id)
        logger.debug("Agent '%s' output length: %d characters", 
                   agent.name, len(str(output)) if output is not None else 0)
                   
        # Stop the agent timer and record duration
        duration = self.metrics.stop_timer("agent_execution", agent.name)
        
        # Get token usage information from context
        input_tokens = context.usage.input_tokens
        output_tokens = context.usage.output_tokens
        total_tokens = context.usage.total_tokens or (input_tokens + output_tokens)
        
        # Record token usage metrics
        if total_tokens > 0:
            self.metrics.record_metric(
                metric_name="agent_token_usage",
                value=total_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "workflow_id": self.workflow_id,
                    "type": "total"
                }
            )
            
        if input_tokens > 0:
            self.metrics.record_metric(
                metric_name="agent_token_usage",
                value=input_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "workflow_id": self.workflow_id,
                    "type": "input"
                }
            )
            
        if output_tokens > 0:
            self.metrics.record_metric(
                metric_name="agent_token_usage",
                value=output_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "workflow_id": self.workflow_id,
                    "type": "output"
                }
            )
        
        # Record agent completion event
        self.metrics.record_event(
            event_type="agent_end",
            resource_id=agent.name,
            metadata={
                "workflow_id": self.workflow_id,
                "duration": duration,
                "output_length": len(str(output)) if output is not None else 0,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "timestamp": time.time()
            }
        )
        
        # Record agent duration metric
        self.metrics.record_metric(
            metric_name="agent_duration",
            value=duration,
            dimensions={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id
            }
        )
        
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Called when an agent starts a tool execution
        
        Args:
            context: The run context wrapper
            agent: The agent that is executing the tool
            tool: The tool being executed
        """
        logger.info("Agent '%s' starting tool '%s' in workflow '%s'", 
                   agent.name, tool.name, self.workflow_id)
                   
        # Start a timer for the tool
        tool_id = f"{agent.name}:{tool.name}"
        self.metrics.start_timer("tool_execution", tool_id)
        
        # Record tool start event
        self.metrics.record_event(
            event_type="tool_start",
            resource_id=tool_id,
            metadata={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id,
                "tool_name": tool.name,
                "timestamp": time.time()
            }
        )
        
    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        """Called when an agent completes a tool execution
        
        Args:
            context: The run context wrapper
            agent: The agent that executed the tool
            tool: The tool that was executed
            result: The result of the tool execution
        """
        logger.info("Agent '%s' completed tool '%s' in workflow '%s'", 
                   agent.name, tool.name, self.workflow_id)
        result_preview = result[:200] + "..." if len(result) > 200 else result
        logger.debug("Tool '%s' result: %s", tool.name, result_preview)
        
        # Stop the tool timer and record duration
        tool_id = f"{agent.name}:{tool.name}"
        duration = self.metrics.stop_timer("tool_execution", tool_id)
        
        # Get token usage from context.usage or fall back to custom attributes
        # Note: Tool-specific tokens may not be directly available in usage
        tool_attr_prefix = f"tool_{tool.name}_"
        tool_input_tokens = getattr(context, f"{tool_attr_prefix}input_tokens", 0)
        tool_output_tokens = getattr(context, f"{tool_attr_prefix}output_tokens", 0)
        
        # Record tool token usage metrics if available
        if tool_input_tokens > 0:
            self.metrics.record_metric(
                metric_name="tool_token_usage",
                value=tool_input_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "workflow_id": self.workflow_id,
                    "tool_name": tool.name,
                    "type": "input"
                }
            )
            
        if tool_output_tokens > 0:
            self.metrics.record_metric(
                metric_name="tool_token_usage",
                value=tool_output_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "workflow_id": self.workflow_id,
                    "tool_name": tool.name,
                    "type": "output"
                }
            )
        
        # Record tool completion event
        self.metrics.record_event(
            event_type="tool_end",
            resource_id=tool_id,
            metadata={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id,
                "tool_name": tool.name,
                "duration": duration,
                "result_length": len(result),
                "input_tokens": tool_input_tokens,
                "output_tokens": tool_output_tokens,
                "timestamp": time.time()
            }
        )
        
        # Record tool duration metric
        self.metrics.record_metric(
            metric_name="tool_duration",
            value=duration,
            dimensions={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id,
                "tool_name": tool.name
            }
        )
        
    async def on_handoff(self, context: RunContextWrapper, agent: Agent, source: Agent) -> None:
        """Called when control is handed to this agent
        
        Args:
            context: The run context wrapper
            agent: The agent receiving control
            source: The agent handing off control
        """
        logger.info("Agent '%s' receiving handoff from '%s' in workflow '%s'", 
                   agent.name, source.name, self.workflow_id)
                   
        # Record handoff event
        self.metrics.record_event(
            event_type="agent_handoff",
            resource_id=agent.name,
            metadata={
                "workflow_id": self.workflow_id,
                "source_agent": source.name,
                "timestamp": time.time()
            }
        )
        
        # Record handoff count metric
        self.metrics.record_metric(
            metric_name="agent_handoffs",
            value=1.0,  # Increment by 1
            dimensions={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id,
                "source_agent": source.name
            }
        )


class MetricsRunHooks(RunHooks):
    """Hooks for collecting run metrics
    
    These hooks record events and metrics for run lifecycle events.
    """
    
    def __init__(self, metrics_context: MetricsContext, workflow_id: str = "unknown"):
        """Initialize the run hooks
        
        Args:
            metrics_context: The metrics context to use (default: global default)
            workflow_id: The ID of the workflow
        """
        super().__init__()
        logger.debug("Initializing MetricsRunHooks for workflow '%s'", workflow_id)
        self.metrics = metrics_context
        self.workflow_id = workflow_id
        
    async def on_run_start(self, context: RunContextWrapper) -> None:
        """Called when a run starts
        
        Args:
            context: The run context wrapper
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run '%s' starting in workflow '%s'", run_id, self.workflow_id)
        
        # Start a timer for the run
        self.metrics.start_timer("run_execution", run_id)
        
        # Record run start event
        self.metrics.record_event(
            event_type="run_start",
            resource_id=run_id,
            metadata={
                "workflow_id": self.workflow_id,
                "timestamp": time.time()
            }
        )
        
    async def on_run_end(self, context: RunContextWrapper, result: Any) -> None:
        """Called when a run ends
        
        Args:
            context: The run context wrapper
            result: The result of the run
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run '%s' completed in workflow '%s'", run_id, self.workflow_id)
        
        # Stop the run timer and record duration
        duration = self.metrics.stop_timer("run_execution", run_id)
        
        # Get token usage information from context
        input_tokens = context.usage.input_tokens
        output_tokens = context.usage.output_tokens
        total_tokens = context.usage.total_tokens or (input_tokens + output_tokens)
        
        # Record token usage metrics
        if total_tokens > 0:
            self.metrics.record_metric(
                metric_name="run_token_usage",
                value=total_tokens,
                dimensions={
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "type": "total"
                }
            )
            
        if input_tokens > 0:
            self.metrics.record_metric(
                metric_name="run_token_usage",
                value=input_tokens,
                dimensions={
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "type": "input"
                }
            )
            
        if output_tokens > 0:
            self.metrics.record_metric(
                metric_name="run_token_usage",
                value=output_tokens,
                dimensions={
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "type": "output"
                }
            )
            
        # Record run completion event
        self.metrics.record_event(
            event_type="run_end",
            resource_id=run_id,
            metadata={
                "workflow_id": self.workflow_id,
                "duration": duration,
                "result_length": len(str(result)) if result is not None else 0,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "timestamp": time.time()
            }
        )
        
        # Record run duration metric
        self.metrics.record_metric(
            metric_name="run_duration",
            value=duration,
            dimensions={
                "workflow_id": self.workflow_id
            }
        )
        
    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        """Called when an agent starts executing within a run
        
        Args:
            context: The run context wrapper
            agent: The agent that started
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run: Agent '%s' starting in run '%s', workflow '%s'", 
                   agent.name, run_id, self.workflow_id)
                   
        # Start a timer for the agent in this run
        agent_run_id = f"{run_id}:{agent.name}"
        self.metrics.start_timer("run_agent_execution", agent_run_id)
        
        # Record agent start in run event
        self.metrics.record_event(
            event_type="run_agent_start",
            resource_id=agent_run_id,
            metadata={
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "agent_id": agent.name,
                "timestamp": time.time()
            }
        )
        
    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        """Called when an agent finishes executing within a run
        
        Args:
            context: The run context wrapper
            agent: The agent that finished
            output: The output of the agent
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run: Agent '%s' completed in run '%s', workflow '%s'", 
                   agent.name, run_id, self.workflow_id)
        
        # Stop the agent timer
        agent_run_id = f"{run_id}:{agent.name}"
        duration = self.metrics.stop_timer("run_agent_execution", agent_run_id)
        
        # Get token usage information from context
        input_tokens = context.usage.input_tokens
        output_tokens = context.usage.output_tokens
        total_tokens = context.usage.total_tokens or (input_tokens + output_tokens)
        
        # Record token usage metrics for this agent
        if total_tokens > 0:
            self.metrics.record_metric(
                metric_name="agent_token_usage",
                value=total_tokens,
                dimensions={
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "agent_id": agent.name,
                    "type": "total"
                }
            )
            
        if input_tokens > 0:
            self.metrics.record_metric(
                metric_name="agent_token_usage",
                value=input_tokens,
                dimensions={
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "agent_id": agent.name,
                    "type": "input"
                }
            )
            
        if output_tokens > 0:
            self.metrics.record_metric(
                metric_name="agent_token_usage",
                value=output_tokens,
                dimensions={
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "agent_id": agent.name,
                    "type": "output"
                }
            )
        
        # Record agent completion in run event
        self.metrics.record_event(
            event_type="run_agent_end",
            resource_id=agent_run_id,
            metadata={
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "agent_id": agent.name,
                "duration": duration,
                "output_length": len(str(output)) if output is not None else 0,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "timestamp": time.time()
            }
        )
        
        # Record agent in run duration metric
        self.metrics.record_metric(
            metric_name="run_agent_duration",
            value=duration,
            dimensions={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id,
                "run_id": run_id
            }
        )
        
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        """Called when a tool starts execution within a run
        
        Args:
            context: The run context wrapper
            agent: The agent executing the tool
            tool: The tool being executed
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run: Tool '%s' starting for agent '%s' in run '%s', workflow '%s'", 
                   tool.name, agent.name, run_id, self.workflow_id)
                   
        # Start a timer for the tool in this run
        tool_run_id = f"{run_id}:{agent.name}:{tool.name}"
        self.metrics.start_timer("run_tool_execution", tool_run_id)
        
        # Record tool start in run event
        self.metrics.record_event(
            event_type="run_tool_start",
            resource_id=tool_run_id,
            metadata={
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "agent_id": agent.name,
                "tool_name": tool.name,
                "timestamp": time.time()
            }
        )
        
    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        """Called when a tool completes execution within a run
        
        Args:
            context: The run context wrapper
            agent: The agent that executed the tool
            tool: The tool that was executed
            result: The result of the tool execution
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run: Tool '%s' completed for agent '%s' in run '%s', workflow '%s'", 
                   tool.name, agent.name, run_id, self.workflow_id)
        result_preview = result[:200] + "..." if len(result) > 200 else result
        logger.debug("Tool '%s' result: %s", tool.name, result_preview)
        
        # Stop the tool timer and record duration
        tool_run_id = f"{run_id}:{agent.name}:{tool.name}"
        duration = self.metrics.stop_timer("run_tool_execution", tool_run_id)
        
        # Get token usage for the tool if available
        # Note: Tool-specific tokens may not be directly available in usage
        tool_attr_prefix = f"run_tool_{tool.name}_"
        tool_input_tokens = getattr(context, f"{tool_attr_prefix}input_tokens", 0)
        tool_output_tokens = getattr(context, f"{tool_attr_prefix}output_tokens", 0)
        tool_total_tokens = tool_input_tokens + tool_output_tokens
        
        # Record tool token usage metrics if available
        if tool_total_tokens > 0:
            self.metrics.record_metric(
                metric_name="run_tool_token_usage",
                value=tool_total_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "tool_name": tool.name,
                    "type": "total"
                }
            )
            
        if tool_input_tokens > 0:
            self.metrics.record_metric(
                metric_name="run_tool_token_usage",
                value=tool_input_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "tool_name": tool.name,
                    "type": "input"
                }
            )
            
        if tool_output_tokens > 0:
            self.metrics.record_metric(
                metric_name="run_tool_token_usage",
                value=tool_output_tokens,
                dimensions={
                    "agent_id": agent.name,
                    "run_id": run_id,
                    "workflow_id": self.workflow_id,
                    "tool_name": tool.name,
                    "type": "output"
                }
            )
        
        # Record tool completion in run event
        self.metrics.record_event(
            event_type="run_tool_end",
            resource_id=tool_run_id,
            metadata={
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "agent_id": agent.name,
                "tool_name": tool.name,
                "duration": duration,
                "result_length": len(result),
                "input_tokens": tool_input_tokens,
                "output_tokens": tool_output_tokens,
                "total_tokens": tool_total_tokens,
                "timestamp": time.time()
            }
        )
        
        # Record tool in run duration metric
        self.metrics.record_metric(
            metric_name="run_tool_duration",
            value=duration,
            dimensions={
                "agent_id": agent.name,
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "tool_name": tool.name
            }
        )
        
    async def on_handoff(self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent) -> None:
        """Called when one agent hands off to another within a run
        
        Args:
            context: The run context wrapper
            from_agent: The agent handing off control
            to_agent: The agent receiving control
        """
        trace = get_current_trace()
        run_id = trace.trace_id if trace is not None else str(uuid.uuid4())
        logger.info("Run: Handoff from agent '%s' to '%s' in run '%s', workflow '%s'", 
                   from_agent.name, to_agent.name, run_id, self.workflow_id)
                   
        # Record handoff in run event
        handoff_id = f"{run_id}:{from_agent.name}:{to_agent.name}"
        self.metrics.record_event(
            event_type="run_handoff",
            resource_id=handoff_id,
            metadata={
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "from_agent": from_agent.name,
                "to_agent": to_agent.name,
                "timestamp": time.time()
            }
        )
        
        # Record handoff in run count metric
        self.metrics.record_metric(
            metric_name="run_handoffs",
            value=1.0,  # Increment by 1
            dimensions={
                "workflow_id": self.workflow_id,
                "run_id": run_id,
                "from_agent": from_agent.name,
                "to_agent": to_agent.name
            }
        ) 