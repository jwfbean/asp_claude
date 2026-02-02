# SP Utility Summary for AI Assistants

This document summarizes the `sp` utility usage for AI systems working with MongoDB Atlas Stream Processing.

## The `sp` Utility - Primary Tool

**Location**: `tools/sp` (executable Python script)
**Working Directory**: Always run from `tools/` directory

## Essential Commands for AI Use

### Basic Workflow
```bash
# Navigate to tools directory FIRST
cd tools/

# Test processors before deployment
./sp processors test                    # Test all processors
./sp processors test -p processor_name  # Test specific processor

# Deploy connections (if new/updated)
./sp workspaces connections create

# Deploy processors 
./sp processors create

# Check status
./sp processors list

# Monitor performance
./sp processors stats

# Lifecycle management
./sp processors start    # Start all processors
./sp processors stop     # Stop all processors  
./sp processors restart  # Restart all processors
```

### Individual Processor Management
```bash
# Drop specific processor
./sp processors drop processor_name

# Drop ALL processors (careful!)
./sp processors drop --all

# Stats for specific processor
./sp processors stats --processor processor_name
```

### Testing and Validation
```bash
# Test all processor configurations
./sp processors test

# Test specific processor
./sp processors test -p solar_simple_processor

# Returns JSON output with validation results
# Always test before deploying to catch issues early
```

### Configuration Options
```bash
# Use custom config file
./sp --config /path/to/config.txt list

# Auto-detection searches:
# 1. ../config.txt (default)
# 2. ./config.txt
# 3. config.txt
```

## AI Assistant Rules

### When User Says "Create a Processor"
1. Generate JSON file in `processors/` directory
2. Run: `cd tools && ./sp processors create`
3. Verify: `./sp processors list`
4. Start if needed: `./sp processors start`

### When User Says "Deploy" or "Create Connections"  
1. Update `connections/connections.json`
2. Run: `cd tools && ./sp workspaces connections create`
3. Verify: `./sp processors list`

### For Monitoring and Status
- Use `./sp processors list` for current status
- Use `./sp processors stats` for performance metrics
- Use `./sp processors start/stop/restart` for lifecycle management

## Mandatory Usage

**CRITICAL**: Always use the `sp` utility for ALL stream processing operations:

**DO**: `cd tools && ./sp create processors`
**DON'T**: Manual API calls or other deployment methods

**DO**: `./sp list` for status checking  
**DON'T**: Direct Atlas API status queries

**DO**: `./sp stats` for monitoring
**DON'T**: Custom monitoring scripts

## Output Format

All `sp` commands return structured JSON for AI processing:

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

## File Structure for AI

```
project_root/
├── config.txt (Atlas credentials)
├── connections/
│   └── connections.json (connection definitions)
├── processors/
│   ├── processor1.json
│   └── processor2.json  
└── tools/
    └── sp (PRIMARY TOOL - use this!)
```

## Quick Reference

| User Request | AI Action |
|-------------|-----------|
| "Test processors" | `cd tools && ./sp test` |
| "Test specific processor" | `cd tools && ./sp test -p processor_name` |
| "Create a processor" | 1. Generate JSON in `processors/`<br>2. `cd tools && ./sp test`<br>3. `cd tools && ./sp create processors`<br>4. `./sp list` |
| "Deploy connections" | 1. Update `connections.json`<br>2. `cd tools && ./sp create connections` |
| "Check status" | `cd tools && ./sp list` |
| "Monitor performance" | `cd tools && ./sp stats` |
| "Start processors" | `cd tools && ./sp start` |
| "Stop processors" | `cd tools && ./sp stop` |

Remember: The `sp` utility is the **single source of truth** for all stream processing operations in this repository.
