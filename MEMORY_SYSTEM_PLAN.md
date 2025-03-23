# ORCS Memory System Enhancement Plan

> **Note**: Implementation of this plan has moved forward with Memory v2, which is now the recommended memory system. See `docs/MEMORY_V1_TO_V2_MIGRATION.md` for migration guidance.

## Current State

The current ORCS memory system functions primarily as a system log, capturing:
- Agent lifecycle events (start/end timestamps)
- Tool execution records
- Handoffs between agents
- Truncated outputs (limited to 1000 characters)

While this provides good operational visibility, it falls short of being a true knowledge repository that enables sophisticated agent reasoning across time and between agents.

## Vision

Transform the ORCS memory system from a system logger to a knowledge repository that enables:
1. Cumulative knowledge building across agent interactions
2. Contextual awareness between agents
3. Semantic retrieval of relevant information
4. Intelligent memory management as context scales
5. Persistent storage across sessions with multiple backend options

## Architecture Evolution

### Phase 1: Enhanced Memory Content

Move from storing system events to storing knowledge:

| Current Storage | Enhanced Storage |
|-----------------|------------------|
| Agent started/ended | Key insights and conclusions |
| Tool was called | Important context for future reasoning |
| Output was truncated | Structured knowledge representations |
| Handoff occurred | Decision rationales and reasoning chains |

### Phase 2: Memory Retrieval Mechanisms

Enhance how agents interact with memory:

1. **Semantic Search**
   - Implement vector embeddings for memory content
   - Enable similarity-based retrieval across the knowledge base
   - Support natural language queries against memory

2. **Memory Context Integration**
   - Automatically include relevant memories in agent prompts
   - Create memory digests that fit within context windows
   - Support hierarchical memory summarization

3. **Agent-directed Memory Access**
   - Allow agents to query memories based on relevance
   - Support cross-agent memory sharing
   - Enable memory exploration beyond predefined tools

### Phase 3: Active Memory Management

Build sophisticated memory management capabilities:

1. **Memory Reflection**
   - Enable agents to reflect on their memories
   - Support importance-based memory prioritization
   - Allow agents to tag memories for future reference

2. **Forgetting Mechanisms**
   - Implement principled approaches to memory pruning
   - Support memory consolidation (combining related memories)
   - Enable intelligent forgetting of low-value information

3. **Memory Structures**
   - Support different memory types (episodic, semantic, procedural)
   - Implement memory schemas for different knowledge categories
   - Enable relational connections between memories

### Phase 4: Storage Backends and Persistence

Create a flexible persistence layer:

1. **Storage Provider Interface**
   - Abstract storage operations behind a provider interface
   - Support multiple backend implementations (in-memory, file-based, databases)
   - Enable seamless switching between storage providers

2. **Tiered Memory Storage**
   - Differentiate between short-term and long-term memory
   - Implement auto-archiving to persistent storage
   - Support memory lifecycle policies by scope

3. **User-Specific Persistent Memory**
   - Enable persistent user-scoped memory across sessions
   - Support privacy and isolation between user memory spaces
   - Implement secure access patterns for user memory

## Implementation Roadmap

### Immediate Next Steps

1. **Enhanced Memory Storage**
   - Extend the `MemorySystem` class to support:
     - Richer content formats (beyond key-value)
     - Metadata tagging for better retrieval
     - Vector representations of memory content

2. **Agent Memory Tools**
   - Create tools for agents to:
     - Store insights and conclusions
     - Mark information as important for future reference
     - Request relevant context from memory

3. **SearchableMemory Interface**
   - Implement semantic search functionality using embeddings
   - Build retrieval functions based on relevance to queries
   - Support filtering by metadata and memory types

4. **Storage Provider Abstraction**
   - Define storage provider interfaces
   - Implement reference providers for in-memory and file-based storage
   - Create migration utilities between storage backends

### Medium-term Goals

1. **Automatic Memory Integration**
   - Build memory context providers for agent prompts
   - Implement memory summarization for context windows
   - Create memory injection hooks for agent execution

2. **Memory Reflection Tools**
   - Develop tools for agents to reflect on past memories
   - Enable agents to connect and synthesize memories
   - Support explicit reasoning about memory content

3. **Cross-agent Memory Sharing**
   - Implement controlled memory sharing patterns
   - Enable "teaching" between agents through memory
   - Support collaborative memory building

4. **Database Storage Backends**
   - Implement DynamoDB provider
   - Add support for SQL/NoSQL databases
   - Create vector database integration for embeddings

### Long-term Vision

1. **Cognitive Architecture Integration**
   - Align memory system with cognitive architecture patterns
   - Support different memory types with specialized retrieval
   - Enable procedural memory for learned behaviors

2. **Memory-Driven Agent Improvement**
   - Support agents learning from past experiences
   - Enable preferences and knowledge to accumulate over time
   - Build episodic memory for experiential learning

3. **Multi-agent Knowledge Building**
   - Create shared knowledge repositories across agent teams
   - Support specialized memory roles (curator, teacher, etc.)
   - Enable collective intelligence through memory

4. **Enterprise-Grade Memory Infrastructure**
   - Implement sharding and partitioning for large memory stores
   - Enable multi-region replication for high availability
   - Support compliance and governance requirements

## Technical Implementation Details

### Memory Content Model

```python
class MemoryContent:
    """Rich content model for agent memories"""
    
    def __init__(self, 
                 content: Any,
                 importance: float = 0.5,
                 memory_type: str = "knowledge",
                 tags: List[str] = None,
                 metadata: Dict[str, Any] = None):
        self.content = content
        self.importance = importance
        self.memory_type = memory_type  # "knowledge", "insight", "procedure", etc.
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.embedding = None  # To be populated by vector embedding
```

### Enhanced AgentContext Interface

```python
class EnhancedAgentContext:
    """Enhanced context for agent memory interactions"""
    
    # Existing methods...
    
    def remember_insight(self, insight: str, importance: float = 0.5) -> None:
        """Store an important insight from the agent's reasoning"""
        content = MemoryContent(
            content=insight,
            importance=importance,
            memory_type="insight"
        )
        self.memory.store_content(f"insight:{uuid.uuid4()}", content, self.scope)
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[MemoryContent]:
        """Retrieve memories relevant to a specific query"""
        return self.memory.search(query, self.scope, limit=limit)
    
    def remember_for_agent(self, target_agent_id: str, content: str, 
                          importance: float = 0.5) -> None:
        """Store memory specifically for another agent to access"""
        memory_content = MemoryContent(
            content=content,
            importance=importance,
            memory_type="shared",
            metadata={"target_agent": target_agent_id}
        )
        share_scope = f"workflow:{self.workflow_id}:agent:{target_agent_id}:shared"
        self.memory.store_content(f"shared:{uuid.uuid4()}", memory_content, share_scope)
```

### Vector Search Implementation

```python
class SearchableMemorySystem(MemorySystem):
    """Memory system with semantic search capabilities"""
    
    def __init__(self, embedding_provider=None, **kwargs):
        super().__init__(**kwargs)
        self.embedding_provider = embedding_provider or DefaultEmbeddingProvider()
        self.vector_index = {}  # Map keys to vector representations
    
    def store_content(self, key: str, content: MemoryContent, scope: str = "global") -> None:
        """Store content with vector embedding for search"""
        # Generate embedding for the content
        if isinstance(content.content, str):
            content.embedding = self.embedding_provider.embed(content.content)
            self.vector_index[key] = content.embedding
        
        # Store with parent implementation
        self.store(key, content, scope)
    
    def search(self, query: str, scope: str, limit: int = 5) -> List[MemoryContent]:
        """Search for memories semantically relevant to query"""
        # Generate query embedding
        query_embedding = self.embedding_provider.embed(query)
        
        # Find accessible keys for this scope
        accessible_keys = self._get_accessible_keys(scope)
        
        # Calculate similarity scores
        scores = []
        for key in accessible_keys:
            if key in self.vector_index:
                similarity = cosine_similarity(query_embedding, self.vector_index[key])
                scores.append((key, similarity))
        
        # Sort by similarity and take top results
        scores.sort(key=lambda x: x[1], reverse=True)
        top_keys = [key for key, _ in scores[:limit]]
        
        # Retrieve content for top keys
        results = []
        for key in top_keys:
            try:
                content = self.retrieve(key, scope)
                if isinstance(content, MemoryContent):
                    results.append(content)
            except (KeyError, PermissionError):
                continue
                
        return results
```

### Storage Provider Interface

```python
class MemoryStorageProvider(ABC):
    """Abstract interface for memory storage providers"""
    
    @abstractmethod
    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        """Store a value with optional metadata"""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Any:
        """Retrieve a value by key"""
        pass
    
    @abstractmethod
    def list_keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key-value pair"""
        pass
    
    @abstractmethod
    def has_key(self, key: str) -> bool:
        """Check if a key exists"""
        pass
    
    @abstractmethod
    def store_binary(self, key: str, data: bytes, metadata: Dict[str, Any] = None) -> None:
        """Store binary data"""
        pass
    
    @abstractmethod
    def retrieve_binary(self, key: str) -> bytes:
        """Retrieve binary data"""
        pass


class InMemoryStorageProvider(MemoryStorageProvider):
    """In-memory implementation of storage provider"""
    
    def __init__(self):
        self.data = {}
        self.metadata = {}
    
    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        self.data[key] = value
        if metadata:
            self.metadata[key] = metadata
    
    def retrieve(self, key: str) -> Any:
        if key not in self.data:
            raise KeyError(f"Key '{key}' not found")
        return self.data[key]
    
    # ... other implementation methods


class FileStorageProvider(MemoryStorageProvider):
    """File-based implementation of storage provider"""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.index_file = os.path.join(storage_dir, "memory_index.json")
        self.metadata = self._load_metadata()
        os.makedirs(storage_dir, exist_ok=True)
    
    def _load_metadata(self) -> Dict:
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self) -> None:
        with open(self.index_file, 'w') as f:
            json.dump(self.metadata, f)
    
    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        # Create a file path for this key
        file_path = os.path.join(self.storage_dir, f"{slugify(key)}.pickle")
        
        # Store the value
        with open(file_path, 'wb') as f:
            pickle.dump(value, f)
        
        # Update metadata
        self.metadata[key] = {
            'file_path': file_path,
            'created_at': datetime.now().isoformat(),
            'custom': metadata or {}
        }
        self._save_metadata()
    
    # ... other implementation methods


class DynamoDBStorageProvider(MemoryStorageProvider):
    """DynamoDB implementation of storage provider"""
    
    def __init__(self, table_name: str, region: str = 'us-west-2'):
        self.table_name = table_name
        self.client = boto3.client('dynamodb', region_name=region)
        self._ensure_table_exists()
    
    def _ensure_table_exists(self) -> None:
        """Create the table if it doesn't exist"""
        try:
            self.client.describe_table(TableName=self.table_name)
        except self.client.exceptions.ResourceNotFoundException:
            self.client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'key', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'key', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            # Wait for table to be created
            waiter = self.client.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
    
    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        # Serialize the value
        serialized = pickle.dumps(value)
        encoded = base64.b64encode(serialized).decode('utf-8')
        
        # Store in DynamoDB
        item = {
            'key': {'S': key},
            'value': {'S': encoded},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        if metadata:
            item['metadata'] = {'S': json.dumps(metadata)}
            
        self.client.put_item(
            TableName=self.table_name,
            Item=item
        )
    
    # ... other implementation methods
```

## Success Criteria

The memory system enhancement will be successful when:

1. Agents can recall relevant information from past interactions without explicit programming
2. Information discovered by one agent can be effectively utilized by another
3. The system builds cumulative knowledge over time rather than starting fresh each time
4. Memory retrieval is contextually relevant rather than just chronological
5. The system can handle scaling memory without degrading performance
6. Memory persists across sessions and system restarts
7. User-specific knowledge can be maintained long-term

This approach transforms memory from a passive log to an active knowledge system that enhances agent capabilities across time and interactions. 