# Memory System v2 Examples

This directory contains example implementations showing how to use and extend the Memory System v2.

## Examples

### Agent Tools Example

The `agent_tools_example.py` file demonstrates how to create agent-specific tools using the memory system. It shows:

- How to extract agent scope from context
- How to create function tools for basic memory operations
- How to implement rich content memory tools
- How to build semantic search tools

These examples are not meant to be used directly, but rather serve as templates you can adapt to your specific agent framework and requirements.

## Creating Your Own Extensions

The examples show common patterns for extending the memory system. When creating your own extensions:

1. **Start with the core abstractions**: `MemorySystem`, `StorageProvider`, etc.
2. **Choose the right level of extension**: Decide whether you need to extend the system itself or just build tools on top of it
3. **Keep it focused**: Each extension should do one thing well
4. **Document assumptions**: Be clear about what your extension expects from its environment

Remember that the memory system is designed to be non-opinionated, so you can integrate it into your project in whatever way makes the most sense for your needs. 