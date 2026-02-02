# MongoDB Atlas Stream Processing Development Workflow

This guide provides AI systems with step-by-step workflows for developing, testing, and deploying stream processing solutions using this repository.

## The `sp` Utility - Essential Tool

**CRITICAL**: All stream processing operations must use the `sp` utility located in `tools/sp/sp`. This is the **primary and preferred tool** for all stream processing management.

### Quick Start with `sp`

```bash
# Always start by navigating to tools/sp directory
cd tools/sp/

# Essential commands:
./sp workspaces connections create    # Deploy connections
./sp processors create             # Deploy processors  
./sp processors list               # Check status
./sp processors stats              # Monitor performance
./sp processors start             # Start processors
./sp processors stop              # Stop processors
./sp restart                       # Restart processors
```

**AI Usage Rule**: When any user requests processor creation, deployment, monitoring, or management, **always use the `sp` utility commands** as shown above.

## Reference Sources

For the most current information on Stream Processing workflows:

- **Atlas Stream Processing Documentation**: [MongoDB Atlas Stream Processing](https://www.mongodb.com/docs/atlas/atlas-stream-processing/)
- **Best Practices Guide**: [MongoDB Stream Processing Best Practices](https://www.mongodb.com/docs/atlas/atlas-stream-processing/overview/#best-practices)
- **Troubleshooting Guide**: [MongoDB Atlas Stream Processing Troubleshooting](https://www.mongodb.com/docs/atlas/atlas-stream-processing/troubleshooting/)

## Development Workflow

### Phase 1: Project Setup and Configuration

#### 1.1 Initialize Configuration

```bash
# Set up basic Atlas credentials in config.txt
# Minimum required configuration:
# PUBLIC_KEY=your_atlas_public_key
# PRIVATE_KEY=your_atlas_private_key  
# PROJECT_ID=your_atlas_project_id
```

#### 1.2 Create Stream Processing Workspace

```bash
# Navigate to tools/sp directory
cd tools/sp/

# List existing workspaces (if any)
./sp workspaces list

# Create new workspace if needed
./sp workspaces create my-stream-workspace

# Add workspace name to config.txt
# SP_WORKSPACE_NAME=my-stream-workspace
```

#### 1.3 Verify Environment

```bash
# Test API connectivity and workspace access
./sp processors list

# Expected output: JSON list of processors (may be empty for new workspace)
```

**Note**: The `sp` utility is located in `tools/sp/sp` and is the **primary tool** for all stream processing operations. Always run it from the `tools/sp/` directory.

### Phase 2: Connection Development

#### 2.1 Design Connections

1. **Identify data sources** - APIs, databases, streams, sample data
2. **Choose connection types** - HTTP, Kafka, Cluster, Sample, EventBridge
3. **Plan authentication** - API keys, tokens, certificates
4. **Configure variables** - Use `{{VARIABLE_NAME}}` for sensitive data

#### 2.2 Create Connection Definitions

```bash
# Edit connections/connections.json
# Add new connection objects following patterns in CONNECTION_GUIDE.md

# Example structure:
{
  "connections": [
    {
      "name": "my_api_connection",
      "type": "HTTP",
      "config": {
        "baseUrl": "{{API_BASE_URL}}",
        "headers": {
          "Authorization": "Bearer {{API_TOKEN}}"
        }
      }
    }
  ]
}
```

#### 2.3 Deploy Connections

```bash
# Navigate to tools/sp directory
cd tools/sp/

# Deploy all connections from connections/*.json files
./sp workspaces connections create

# Expected output: JSON summary of connection creation attempts
```

### Phase 3: Processor Development

#### 3.1 Design Processing Logic

1. **Define use case** - Ingestion, transformation, alerting, aggregation
2. **Choose pipeline pattern** - Reference PIPELINE_PATTERNS.md
3. **Plan data flow** - Source → transformations → destination
4. **Design error handling** - DLQ configuration, graceful degradation

#### 3.2 Create Processor Definition

```bash
# Create new JSON file in processors/ directory
# Follow MongoDB aggregation pipeline syntax
# Example: processors/my_processor.json

{
  "name": "my_processor",
  "pipeline": [
    {
      "$source": {
        "connectionName": "my_source_connection"
      }
    },
    {
      "$match": {
        "status": "active"
      }
    },
    {
      "$addFields": {
        "processing_timestamp": "$$NOW"
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "my_cluster_connection",
          "db": "processed_data",
          "coll": "events"
        }
      }
    }
  ],
  "options": {
    "dlq": {
      "connectionName": "my_cluster_connection",
      "db": "errors",
      "coll": "dlq"
    }
  }
}
```

#### 3.3 Deploy and Test Processor

```bash
# Navigate to tools/sp directory
cd tools/sp/

# Create the processor
./sp processors create

# Check deployment
./sp processors list

# Start all processors
./sp processors start

# Monitor performance
./sp processors stats

# Monitor specific processor
./sp processors stats --processor my_processor
```

### Phase 4: Testing and Validation

#### 4.1 Development Testing

```bash
# Use sample data for initial testing
# Create test connection with Sample type
{
  "name": "test_sample",
  "type": "Sample",
  "config": {
    "interval": {"size": 1, "unit": "second"},
    "format": "sampleiot"
  }
}

# Point processor $source to test_sample connection
# Verify data flow through pipeline stages
```

#### 4.2 Integration Testing

```bash
# Test with real data sources
# Navigate to tools/sp directory first
cd tools/sp/

# Monitor processor performance
./sp processors stats

# Check overall status
./sp processors list

# Check data quality in destination
# Verify error handling via DLQ
```

#### 4.3 Performance Testing

```bash
# Monitor processor metrics
./sp processors stats

# For specific processor monitoring:
./sp processors stats --processor processor_name

# Key metrics to monitor:
# - Input rate
# - Output rate
# - Error rate
# - Processing latency
```

### Phase 5: Production Deployment

#### 5.1 Pre-deployment Checklist

- [ ] All connections tested and validated
- [ ] Processor logic thoroughly tested
- [ ] Error handling configured (DLQ)
- [ ] Performance requirements met
- [ ] Security variables properly configured
- [ ] Documentation updated

#### 5.2 Deployment Process

```bash
# Navigate to tools/sp directory
cd tools/sp/

# Stop existing processor (if updating)
./sp processors stop

# Deploy new/updated processor
./sp processors create

# Start processor
./sp processors start

# Verify startup
./sp processors list
```

#### 5.3 Post-deployment Monitoring

```bash
# Navigate to tools/sp directory  
cd tools/sp/

# Monitor processor health
./sp stats

# Monitor specific processor
./sp stats --processor processor_name

# Check overall status
./sp list

# Check for processing errors
# Monitor destination data quality
# Verify alert mechanisms working
```

## Debugging Workflow

### Common Issues and Resolution

#### 1. Connection Failures

```bash
# Navigate to tools/sp directory
cd tools/sp/

# Check connection status via processor list
./sp list

# Verify authentication variables in config.txt
# Test API endpoints manually
# Check network connectivity
```

#### 2. Processor Startup Failures

```bash
# Check processor definition syntax
# Validate JSON format
# Verify connection references exist
# Check pipeline stage syntax
```

#### 3. Processing Errors

```bash
# Check DLQ for error details
# Review processor stats for error patterns
# Validate data format expectations
# Check field mappings and transformations
```

#### 4. Performance Issues

```bash
# Navigate to tools/sp directory
cd tools/sp/

# Monitor processing rates
./sp stats

# For specific processor:
./sp stats --processor processor_name

# Check for bottlenecks in pipeline stages
# Optimize $match stages (move early in pipeline)
# Consider windowing configuration
# Review index strategy for $merge operations
```

## Iterative Development Process

### Rapid Prototyping

1. **Start with sample data** - Use Sample connections for quick iteration
2. **Build incrementally** - Add pipeline stages one at a time
3. **Test frequently** - Verify each stage before adding complexity
4. **Use simple outputs** - Start with basic $merge before complex logic

### Pipeline Development Pattern

```bash
# 1. Basic ingestion
{
  "pipeline": [
    {"$source": {"connectionName": "sample_stream"}},
    {"$merge": {"into": {"connectionName": "cluster", "db": "test", "coll": "raw"}}}
  ]
}

# 2. Add filtering
{
  "pipeline": [
    {"$source": {"connectionName": "sample_stream"}},
    {"$match": {"status": "active"}},
    {"$merge": {"into": {"connectionName": "cluster", "db": "test", "coll": "filtered"}}}
  ]
}

# 3. Add transformations
{
  "pipeline": [
    {"$source": {"connectionName": "sample_stream"}},
    {"$match": {"status": "active"}},
    {"$addFields": {"processed_at": "$$NOW"}},
    {"$merge": {"into": {"connectionName": "cluster", "db": "test", "coll": "processed"}}}
  ]
}

# 4. Add error handling and optimization
```

## Monitoring and Maintenance

### Regular Health Checks

```bash
# Navigate to tools/sp directory
cd tools/sp/

# Daily processor health check  
./sp list

# Weekly performance review
./sp stats

# For specific processor monitoring:
./sp stats --processor processor_name

# Monthly capacity planning
# Review processing volumes and trends
```

### Scaling Considerations

- **Horizontal scaling**: Create multiple processors for different data partitions
- **Vertical scaling**: Optimize pipeline stages for better performance
- **Load balancing**: Distribute processing across multiple workspaces
- **Resource monitoring**: Track memory and CPU usage patterns

## AI Development Guidelines

When implementing stream processing solutions:

### 1. Start Simple
- Begin with basic ingestion and storage
- Add complexity incrementally
- Test each addition thoroughly

### 2. Follow Patterns
- Use established patterns from PIPELINE_PATTERNS.md
- Adapt patterns to specific use cases
- Don't reinvent common solutions

### 3. Plan for Failure
- Always include DLQ configuration
- Handle missing or malformed data gracefully
- Implement appropriate retry logic

### 4. Optimize Iteratively
- Start with working solution
- Profile and identify bottlenecks
- Optimize based on actual performance data

### 5. Document Decisions
- Record design choices and trade-offs
- Maintain processor documentation
- Update connection inventories

### Example Development Session

```bash
# Navigate to tools/sp directory
cd tools/sp/

# 1. Create connection
./sp create connections

# 2. Create initial processor
./sp create processors

# 3. Start and test
./sp start
./sp stats

# 4. Iterate on processor logic
# Edit processors/weather_ingestion.json

# 5. Update and restart
./sp stop
./sp create processors

This workflow ensures reliable, maintainable stream processing solutions that follow MongoDB best practices and leverage the full capabilities of Atlas Stream Processing.
