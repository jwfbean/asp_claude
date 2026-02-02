# AI Assistant Guide for MongoDB Atlas Stream Processing

This document provides AI systems with comprehensive guidance for using this repository to build MongoDB Atlas Stream Processing applications. This repository serves as a production-ready starter kit with working examples and complete tooling.

## Repository Purpose

This is a **complete starter template** for MongoDB Atlas Stream Processing that AI systems should use to:

1. **Generate functional stream processors** based on user requirements
2. **Create proper JSON pipeline definitions** following MongoDB best practices
3. **Set up connections** to external data sources and sinks
4. **Provide working management tools** for deployment and monitoring

## Essential Reference Materials

### Official MongoDB Documentation
Always reference the most current documentation at:
- **Main Docs**: https://www.mongodb.com/docs/atlas/atlas-stream-processing/overview/
- **Pipeline Stages**: https://www.mongodb.com/docs/atlas/atlas-stream-processing/pipeline-stages/
- **Connection Types**: https://www.mongodb.com/docs/atlas/atlas-stream-processing/connections/

### MongoDB Example Repository
Reference the official examples at:
- **ASP Examples**: https://github.com/mongodb/asp_example
- **Code Snippets**: https://github.com/mongodb/asp_example/tree/main/code_snipplets
- **Example Processors**: https://github.com/mongodb/asp_example/tree/main/example_processors

> **Important**: Always check these repositories for the latest patterns and best practices as they are maintained by the MongoDB product team.

## Stream Processing Workspace Management

### Onboarding Workflow for New Users

**NEW USER ASSUMPTION**: Users have only an Atlas account and API keys. They may not have a Stream Processing workspace yet.

1. **Initial Setup** (API Keys + Project ID)
```bash
# User needs only these in config.txt initially:
PUBLIC_KEY=your_atlas_public_key
PRIVATE_KEY=your_atlas_private_key  
PROJECT_ID=your_atlas_project_id
```

2. **Instance Discovery and Creation**
```bash
# Check existing workspaces
./sp workspaces list

# Create new workspace if needed
./sp workspaces create my-stream-workspace --cloud-provider AWS --region US_EAST_1

# Add to config.txt after creation
SP_WORKSPACE_NAME=my-stream-workspace
```

3. **Proceed with Standard Workflow**
- Deploy connections: `./sp workspaces connections create`
- Deploy processors: `./sp processors create`
- Start processing: `./sp processors start`
- Monitor performance: `./sp processors stats`

### Workspace Management Commands

The `sp` utility now supports full workspace lifecycle management:

```bash
# List workspaces  
./sp workspaces list

# Create workspace
./sp workspaces create <name> [--cloud-provider AWS] [--region US_EAST_1]

# Get workspace details
./sp workspaces details <name>

# Delete workspace
./sp workspaces delete <name>
```

### Configuration Requirements

- **For workspace management**: Only `PUBLIC_KEY`, `PRIVATE_KEY`, `PROJECT_ID` required
- **For processor/connection operations**: Must also have `SP_WORKSPACE_NAME` in config.txt

### AI Implementation Guidelines

When helping users:

1. **Check if they have a workspace**: Start with `./sp workspaces list`
2. **Guide workspace creation**: If no workspace exists, use `./sp workspaces create`
3. **Update configuration**: Ensure `SP_WORKSPACE_NAME` is added to config.txt
4. **Proceed with standard workflow**: Connections → Processors → Start → Monitor

## Repository Architecture Understanding

### Core Components

1. **`config.txt`** - Atlas API credentials and project configuration
2. **`connections/`** - External service connection definitions
3. **`processors/`** - JSON-based stream processor pipeline definitions
4. **`tools/sp/sp`** - **PRIMARY MANAGEMENT TOOL** - Unified CLI for all stream processing operations

### The `sp` Utility - Your Primary Tool

The `sp` utility located in `tools/sp/sp` is the **main command-line interface** for all stream processing operations. **Always use this tool** for creating, managing, and deploying stream processors and connections.

**Key Features:**

- **Location**: `tools/sp/sp` (executable Python script)
- **Auto-config detection**: Automatically finds `config.txt` in project
- **Unified operations**: Single tool for all stream processing tasks
- **JSON output**: Structured responses for AI processing
- **Error handling**: Comprehensive error reporting and validation

### Key Design Principles

1. **JSON-First**: All processors are defined in pure JSON format (not JavaScript)
2. **Declarative**: Configuration-driven approach with minimal code
3. **Tooling-Integrated**: Complete lifecycle management through CLI
4. **Production-Ready**: Includes error handling, DLQ, and monitoring

## Stream Processor JSON Format

### Required Structure
```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "data_source_connection",
        "timeField": {"$dateFromString": {"dateString": "$timestamp"}}
      }
    },
    // ... processing stages ...
    {
      "$merge": {
        "into": {
          "connectionName": "destination_connection",
          "db": "database_name",
          "coll": "collection_name"
        }
      }
    }
  ],
  "options": {
    "dlq": {
      "connectionName": "error_connection",
      "db": "errors",
      "coll": "processor_errors"
    }
  }
}
```

### Pipeline Stage Categories

1. **Source Stage** (Required first stage)
   - `$source`: Data input from connections
   - Must specify `connectionName`
   - Include `timeField` for time-based processing

2. **Processing Stages** (Stateless operations)
   - `$match`: Filter documents
   - `$addFields`: Add/modify fields
   - `$project`: Shape output
   - `$lookup`: Join with Atlas collections
   - `$https`: Call external APIs

3. **Window Stages** (Stateful operations)
   - `$tumblingWindow`: Fixed-time windows
   - `$hoppingWindow`: Overlapping windows
   - Contains aggregation operations like `$group`, `$avg`, `$sum`

4. **Output Stage** (Required final stage)
   - `$merge`: Write to Atlas collections
   - `$emit`: Send to streaming platforms

### Critical JSON Requirements

1. **Quoted Keys**: All MongoDB operators must be in quotes: `"$match"`, `"$addFields"`
2. **Proper Types**: Use correct JSON types (numbers, not strings for numeric values)
3. **Valid Operators**: Reference official docs for supported aggregation operators
4. **Connection References**: All `connectionName` fields must reference defined connections

## 🔗 Connection Definitions

### Standard Connection Types

1. **Atlas Cluster**
```json
{
  "name": "my_cluster",
  "type": "Cluster",
  "clusterName": "MyAtlasCluster"
}
```

2. **HTTPS API**
```json
{
  "name": "external_api",
  "type": "Https",
  "url": "https://api.example.com"
}
```

3. **Kafka**
```json
{
  "name": "kafka_source",
  "type": "Kafka",
  "bootstrapServers": "broker1:9092,broker2:9092",
  "config": {
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms": "PLAIN"
  }
}
```

4. **Sample Data** (built-in, no configuration needed)

Atlas Stream Processing provides built-in sample streams like `sample_stream_solar` that are automatically available. These don't need to be defined in connections.json:

- `sample_stream_solar` - Solar energy data for testing
- Other sample streams may be available (check with `./tools/sp/sp processors list`)

### Variable Substitution

Use `${VARIABLE_NAME}` to reference values from `config.txt`:

```json
{
  "config": {
    "baseUrl": "${API_BASE_URL}",
    "headers": {
      "Authorization": "Bearer ${API_TOKEN}"
    }
  }
}
```

## AI Code Generation Guidelines

### When Creating Processors

1. **Always use JSON format** - Not JavaScript
2. **Include error handling** - Add DLQ configuration
3. **Add meaningful field names** - Use descriptive names for added fields
4. **Include timestamps** - Add processing timestamps for debugging
5. **Reference existing connections** - Use connection names from `connections/`

### Common Pipeline Patterns

#### Data Ingestion
```json
{
  "$source": {
    "connectionName": "sample_stream_solar",
    "timeField": {"$dateFromString": {"dateString": "$timestamp"}}
  }
},
{
  "$addFields": {
    "processing_time": "$$NOW",
    "processor_name": "data_ingestion"
  }
},
{
  "$merge": {
    "into": {
      "connectionName": "my_cluster",
      "db": "raw_data",
      "coll": "ingested_records"
    }
  }
}
```

#### Real-time Alerting
```json
{
  "$match": {
    "value": {"$gt": 90}
  }
},
{
  "$addFields": {
    "alert_type": "HIGH_TEMPERATURE",
    "alert_timestamp": "$$NOW",
    "alert_message": {
      "$concat": ["Temperature ", {"$toString": "$value"}, " exceeds threshold"]
    }
  }
}
```

#### Time-based Aggregation
```json
{
  "$tumblingWindow": {
    "interval": {"size": 5, "unit": "minute"},
    "pipeline": [
      {
        "$group": {
          "_id": "$sensor_id",
          "avg_value": {"$avg": "$value"},
          "max_value": {"$max": "$value"},
          "count": {"$sum": 1}
        }
      }
    ]
  }
}
```

### Error Handling Best Practices

1. **Always include DLQ** in processor options
2. **Use descriptive error messages** in custom validation
3. **Add processing metadata** for debugging
4. **Include source tracking** for data lineage

## The `sp` Utility - Complete Command Reference

### Tool Location and Usage

**Location**: `tools/sp/sp` (executable Python script in the tools directory)
**Working Directory**: Always run from `tools/` directory or use full path

```bash
cd tools/
./sp --help
```

### Core Commands Overview

The `sp` utility provides unified management for all stream processing operations:

#### Connection Management

```bash
# Create all connections from connections.json files
./sp workspaces connections create

# Lists existing connections (via processor status)
./sp processors list
```

#### Processor Management

```bash
# Create all processors from processors/ directory
./sp processors create

# List all processors with status
./sp processors list

# Show detailed processor statistics  
./sp processors stats

# Show statistics for specific processor
./sp processors stats --processor processor_name
```

#### Processor Lifecycle Operations

```bash
# Start all stopped processors
./sp processors start

# Stop all running processors  
./sp processors stop

# Restart all processors (stop then start)
./sp processors restart

# Delete a specific processor
./sp processors drop processor_name

# Delete ALL processors (use with caution)
./sp processors drop --all
./sp drop --all
```

#### Configuration Options

```bash
# Use custom config file (default: ../config.txt)
./sp --config /path/to/config.txt list

# The tool automatically searches for config.txt in:
# 1. ../config.txt (default)
# 2. ./config.txt 
# 3. config.txt
```

### AI Usage Instructions

**When user says "create a processor":**

1. **Create the JSON file** in `processors/` directory
2. **Run**: `cd tools/sp && ./sp create processors`
3. **Verify**: `./sp list` to check status
4. **Start if needed**: `./sp start`

**When user says "deploy" or "create connections":**

1. **Update** `connections/connections.json`
2. **Run**: `cd tools/sp && ./sp create connections`
3. **Verify**: `./sp list` to see connection status

**For monitoring and management:**

- Use `./sp list` for current status
- Use `./sp stats` for performance metrics
- Use `./sp start/stop/restart` for lifecycle management

### Output Format

All `sp` commands return structured JSON output for easy AI processing:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "operation": "create_processors", 
  "summary": {
    "total": 2,
    "success": 2,
    "failed": 0
  },
  "processors": [
    {
      "name": "my_processor",
      "status": "created",
      "message": "Processor created successfully"
    }
  ]
}
```

## Management Workflow

### Standard Development Flow

**Always use the `sp` utility for all operations:**

1. **Define connections** in `connections/connections.json`
2. **Create processor JSON** in `processors/your_processor.json`
3. **Deploy connections**: `cd tools/sp && ./sp create connections`
4. **Deploy processors**: `cd tools/sp && ./sp create processors`
5. **Monitor status**: `./sp list`
6. **View statistics**: `./sp stats`
7. **Manage lifecycle**: `./sp start/stop/restart`

### CLI Commands Reference

```bash
# Navigate to tools directory first
cd tools/

# Connection management
./sp create connections

# Processor management  
./sp create processors
./sp list
./sp stats
./sp start
./sp stop
./sp restart
./sp drop processor_name
./sp drop --all

# Custom configuration
./sp --config custom.txt list
```

## 🧠 AI Assistant Instructions

### When User Requests Stream Processor

1. **Identify the use case** (IoT, analytics, alerting, etc.)
2. **Determine data sources** (APIs, Kafka, Atlas change streams)
3. **Define processing logic** (filtering, transformation, aggregation)
4. **Choose output destination** (Atlas collections, Kafka topics)
5. **Generate JSON processor definition** and save in `processors/`
6. **Create/update connection definitions** in `connections/connections.json` if needed
7. **Deploy using sp utility**:

   ```bash
   cd tools
   ./sp create connections  # if new connections added
   ./sp create processors   # deploy the new processor
   ./sp list               # verify deployment
   ```

### When User Requests Modifications

1. **Analyze existing processor JSON**
2. **Identify the specific stages to modify**
3. **Maintain JSON structure and syntax**
4. **Preserve error handling and DLQ configuration**
5. **Update relevant connections if needed**
6. **Redeploy using sp utility**:

   ```bash
   cd tools
   ./sp create processors   # update modified processors
   ./sp restart            # restart if needed
   ./sp stats              # check performance
   ```

### Mandatory Use of `sp` Utility

**CRITICAL**: Always use the `sp` utility for ALL stream processing operations:

- **DO**: `cd tools/sp && ./sp create processors`
- **DON'T**: Manual API calls or other deployment methods
- **DO**: `./sp list` for status checking
- **DON'T**: Direct Atlas API status queries
- **DO**: `./sp stats` for monitoring
- **DON'T**: Custom monitoring scripts

**The `sp` utility provides:**

- Automatic error handling and validation
- Structured JSON responses for AI processing
- Consistent deployment patterns
- Built-in retry logic and connection management

### Quality Checklist

Before providing any stream processor code:

- [ ] JSON syntax is valid
- [ ] All MongoDB operators are quoted
- [ ] Connection names are referenced correctly
- [ ] DLQ configuration is included
- [ ] Processing timestamps are added
- [ ] Error handling is appropriate
- [ ] Pipeline stages are in correct order
- [ ] Field names are descriptive

## Keeping Current

### Regular Reference Points

1. **Check MongoDB docs** for new pipeline stages and operators
2. **Review ASP examples** for latest patterns and best practices
3. **Monitor this repository** for tool updates and new features
4. **Follow MongoDB changelog** for Stream Processing updates

### Version Compatibility

Always generate code compatible with:
- **Atlas Stream Processing**: Latest stable version
- **MongoDB Query Language**: Version 6.0+ aggregation features
- **JSON Format**: Standard RFC 7159 compliant JSON

## Additional Resources

- **MongoDB University**: Stream Processing courses and certifications
- **MongoDB Blog**: Latest announcements and tutorials
- **Community Forums**: Real-world use cases and solutions
- **GitHub Issues**: This repository's issue tracker for bugs and features

This guide ensures AI systems can effectively use this repository to generate production-ready MongoDB Atlas Stream Processing applications with proper architecture, error handling, and deployment tooling.
