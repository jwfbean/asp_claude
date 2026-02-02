# SP - Atlas Stream Processing CLI User Manual

## Overview

SP (Stream Processors) is a comprehensive command-line tool for managing MongoDB Atlas Stream Processing workloads. It provides declarative configuration management, performance profiling, tier optimization, and complete lifecycle management for stream processing pipelines.

## Table of Contents

- [Installation & Setup](#installation--setup)
- [Quick Start](#quick-start)
- [Workspace Management](#workspace-management)
- [Connection Management](#connection-management)
- [Processor Management](#processor-management)
- [Performance Analysis](#performance-analysis)
- [Configuration Files](#configuration-files)
- [Advanced Features](#advanced-features)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Installation & Setup

### Prerequisites
- Python 3.7+
- MongoDB Atlas account with Stream Processing enabled
- Atlas API credentials

### Setup Configuration
1. Copy the example configuration:
   ```bash
   cp config.txt.example config.txt
   ```

2. Edit `config.txt` with your Atlas credentials:
   ```
   PUBLIC_KEY=your_atlas_public_key
   PRIVATE_KEY=your_atlas_private_key
   PROJECT_ID=your_project_id
   ```

3. Make the SP tool executable:
   ```bash
   chmod +x tools/sp
   ```

## Quick Start

### Basic Commands
```bash
# List all stream processing workspaces
./sp workspaces list

# List all processors
./sp processors list

# Get processor statistics
./sp processors stats

# Create and start a processor
./sp processors create -p solar_simple_processor
./sp processors start -p solar_simple_processor --auto
```

## Workspace Management

### List Workspaces
```bash
./sp workspaces list
```

### Create Workspace
```bash
./sp workspaces create my-workspace --cloud-provider AWS --region US_EAST_1
```

### Delete Workspace
```bash
./sp workspaces delete my-workspace
```

### Get Workspace Details
```bash
./sp workspaces details my-workspace
```

## Connection Management

### Create Connections
```bash
# Create all connections from JSON files
./sp workspaces connections create
```

### List Connections
```bash
./sp workspaces connections list
```

### Test Connections
```bash
# Test all connections with MongoDB verification
./sp workspaces connections test

# Test specific connection
./sp workspaces connections test --connection my-connection
```

### Delete Connection
```bash
./sp workspaces connections delete connection-name
```

## Processor Management

### Creating Processors

#### From JSON Files
```bash
# Create all processors from processors/ directory
./sp processors create

# Create specific processor
./sp processors create -p solar_simple_processor
```

#### Processor Configuration Format
Processors are defined as JSON files in the `processors/` directory:

```json
{
    "name": "my_processor",
    "pipeline": [
        {
            "$source": {
                "connectionName": "my_connection",
                "timeField": { "$dateFromString": { "dateString": "$timestamp" }}
            }
        },
        {
            "$addFields": {
                "processed_field": "$field * 2"
            }
        },
        {
            "$merge": {
                "into": {
                    "connectionName": "output_connection",
                    "db": "mydb",
                    "coll": "processed_data"
                }
            }
        }
    ]
}
```

### Starting Processors

#### Basic Start
```bash
./sp processors start -p my_processor
```

#### With Specific Tier
```bash
./sp processors start -p my_processor -t SP10
```

#### Auto Tier Selection
```bash
# Automatically select optimal tier based on complexity
./sp processors start -p my_processor --auto
```

#### Start All Processors
```bash
./sp processors start --auto
```

### Managing Processor Lifecycle

#### Stop Processors
```bash
./sp processors stop -p my_processor
./sp processors stop  # Stop all processors
```

#### Restart Processors
```bash
./sp processors restart -p my_processor --auto
./sp processors restart --all-tier SP30
```

#### Delete Processors
```bash
./sp processors drop -p my_processor
./sp processors drop --all  # Delete all processors
```

### Processor Statistics

#### Basic Stats
```bash
./sp processors stats -p my_processor
```

#### Verbose Stats (with operator details)
```bash
./sp processors stats -p my_processor --verbose
```

#### All Processor Stats
```bash
./sp processors stats --verbose
```

## Performance Analysis

### Tier Analysis

#### Get Tier Recommendations
```bash
# Analyze specific processor
./sp processors tier-advise -p my_processor

# Analyze all processors
./sp processors tier-advise --all
```

### Performance Profiling

#### Time-Limited Profiling
```bash
# Profile for 5 minutes with 30-second intervals
./sp processors profile -p my_processor --duration 300 --interval 30
```

#### Continuous Monitoring
```bash
# Monitor until interrupted (Ctrl+C)
./sp processors profile -p my_processor --continuous --interval 15
```

#### Multi-Processor Profiling
```bash
# Profile all running processors
./sp processors profile --all --duration 120 --interval 10
```

#### Advanced Profiling Options
```bash
# Profile with custom metrics and output file
./sp processors profile -p my_processor \
  --duration 300 \
  --interval 15 \
  --metrics memory,latency,throughput \
  --output results.json

# Profile with threshold alerting
./sp processors profile -p my_processor \
  --continuous \
  --thresholds thresholds.json
```

#### Threshold Configuration
Create `thresholds.json` for alerting:
```json
{
  "memory_mb": 500,
  "latency_p99_ms": 100,
  "throughput_min": 10
}
```

### Performance Comparison

#### Compare Different Tiers
```bash
# Test on SP10
./sp processors start -p my_processor -t SP10
./sp processors profile -p my_processor --duration 120 --output sp10_results.json

# Test on SP30  
./sp processors restart -p my_processor -t SP30
./sp processors profile -p my_processor --duration 120 --output sp30_results.json
```

## Configuration Files

### Processor Definitions
- **Location**: `processors/*.json`
- **Format**: Atlas Stream Processing pipeline JSON
- **Features**: Supports parallelism, custom functions, multiple stages

### Connection Definitions
- **Location**: `connections/*.json` or `connections.json`
- **Format**: Atlas connection configuration JSON

### Configuration Examples

#### Sample Processor (`processors/analytics.json`)
```json
{
    "name": "analytics_processor",
    "pipeline": [
        {
            "$source": {
                "connectionName": "data_stream",
                "timeField": { "$dateFromString": { "dateString": "$ts" }}
            }
        },
        {
            "$addFields": {
                "calculated_value": {
                    "$function": {
                        "body": "function(value) { return value * 1.5; }",
                        "args": ["$raw_value"],
                        "lang": "js"
                    }
                }
            }
        },
        {
            "$merge": {
                "into": {
                    "connectionName": "analytics_db",
                    "db": "analytics",
                    "coll": "processed_data"
                },
                "parallelism": 8
            }
        }
    ]
}
```

## Advanced Features

### Parallelism Configuration

#### Add Parallelism to Stages
```json
{
    "$merge": {
        "into": {
            "connectionName": "output_db",
            "db": "mydb", 
            "coll": "results"
        },
        "parallelism": 12
    }
}
```

### Custom JavaScript Functions
```json
{
    "$addFields": {
        "complex_calculation": {
            "$function": {
                "body": "function(input) { return Math.sqrt(input.value) * 2.5; }",
                "args": ["$data"],
                "lang": "js"
            }
        }
    }
}
```

### Testing and Validation

#### Test Processor Configuration
```bash
./sp processors test -p my_processor
```

#### Validate All Processors
```bash
./sp processors test --all
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Stream Processing CI/CD
on:
  push:
    branches: [main]
    paths: ['processors/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Config
        env:
          ATLAS_PUBLIC_KEY: ${{ secrets.ATLAS_PUBLIC_KEY }}
          ATLAS_PRIVATE_KEY: ${{ secrets.ATLAS_PRIVATE_KEY }}
          PROJECT_ID: ${{ secrets.PROJECT_ID }}
        run: |
          echo "PUBLIC_KEY=$ATLAS_PUBLIC_KEY" > config.txt
          echo "PRIVATE_KEY=$ATLAS_PRIVATE_KEY" >> config.txt  
          echo "PROJECT_ID=$PROJECT_ID" >> config.txt
      
      - name: Test Configurations
        run: |
          cd tools
          ./sp processors test --all
          ./sp processors tier-advise --all
      
      - name: Deploy Processors
        run: |
          cd tools
          ./sp processors create --all
          ./sp processors start --auto
      
      - name: Validate Deployment
        run: |
          cd tools
          ./sp processors profile --all --duration 60 --output metrics.json
```

### GitOps Workflow
1. **Development**: Create/modify processor JSON files
2. **Testing**: Use `sp processors test` for validation
3. **Commit**: Push changes to Git repository  
4. **Automation**: GitHub Actions deploys changes
5. **Monitoring**: Continuous profiling and alerting

## Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Verify configuration
cat config.txt

# Test basic connection
./sp workspaces list
```

#### Processor Start Failures
```bash
# Check processor definition
./sp processors test -p my_processor

# Verify connections
./sp workspaces connections test

# Check tier requirements
./sp processors tier-advise -p my_processor
```

#### Performance Issues
```bash
# Profile processor performance
./sp processors profile -p my_processor --duration 60

# Check for configuration drift
./sp processors stats -p my_processor --verbose

# Analyze tier utilization
./sp processors tier-advise -p my_processor
```

### Debug Mode
For detailed error information, examine the raw API responses by checking the verbose output of any command.

### Log Files
SP tool outputs structured JSON for all operations, making it easy to integrate with logging and monitoring systems.

## Best Practices

### Processor Design
- Use descriptive processor names
- Implement proper error handling in JavaScript functions
- Consider parallelism for I/O-bound operations
- Test configurations before deployment

### Performance Optimization
- Use `--auto` tier selection for optimal resource allocation
- Monitor processor performance with regular profiling
- Implement threshold-based alerting
- Compare performance across different tiers

### Configuration Management
- Version control all processor and connection definitions
- Use environment-specific configuration branches
- Implement automated testing in CI/CD pipelines
- Document processor purpose and expected throughput

### Security
- Keep `config.txt` out of version control
- Use environment variables for sensitive credentials in CI/CD
- Regularly rotate Atlas API keys
- Implement proper access controls for production deployments

## Support

For additional support:
- Check the comprehensive documentation in the `docs/` directory
- Review example configurations in `processors/` and `connections/`
- Examine test cases in the `test/` directory

## Version Information

This manual covers SP tool functionality as of the latest version. For the most current features and updates, refer to the Git repository history and release notes.