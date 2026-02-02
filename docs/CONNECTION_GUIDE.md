# Connection Types and Configuration Guide

This document helps AI systems understand and configure different connection types for MongoDB Atlas Stream Processing. Use this as a reference when generating connection configurations.

## Prerequisites and Setup

**ESSENTIAL**: Ensure you have a Stream Processing workspace before deploying connections:

```bash
# Navigate to tools directory
cd tools/sp/

# Check if you have a workspace
./sp workspace list

# Create workspace if needed
./sp workspace create my-stream-workspace

# Add workspace name to config.txt:
# SP_WORKSPACE_NAME=my-stream-workspace
```

## The `sp` Utility for Connection Management

**IMPORTANT**: Always use the `sp` utility located in `tools/sp/sp` for deploying and managing connections:

```bash
# Navigate to tools directory
cd tools/sp/

# Deploy all connections from connections.json
./sp workspace connections create

# List existing connections on workspace
./sp workspace connections list

# Check connection status via processor list
./sp list
```

## Reference Sources

Always consult the latest MongoDB documentation for connection specifications:

- **Connection Types Reference**: [MongoDB Atlas Stream Processing Connections](https://www.mongodb.com/docs/atlas/atlas-stream-processing/manage-connections/)
- **Configuration Examples**: [MongoDB ASP Example Repository](https://github.com/mongodb/asp_example)
- **Security Configuration**: [MongoDB Atlas Security Best Practices](https://www.mongodb.com/docs/atlas/security/)

> These sources contain the most current connection options and security requirements.

## Core Connection Types

### 1. MongoDB Atlas Cluster

**Purpose**: Connect to Atlas clusters for data storage and retrieval

```json
{
  "name": "atlas_cluster",
  "type": "Cluster",
  "config": {
    "clusterName": "{{CLUSTER_NAME}}",
    "readPreference": "primaryPreferred",
    "ssl": true
  }
}
```

**Configuration Variables**:
- `CLUSTER_NAME`: Name of your Atlas cluster
- Read preferences: `primary`, `primaryPreferred`, `secondary`, `secondaryPreferred`, `nearest`

### 2. Sample Stream Connection

**Purpose**: Use for testing and development with generated sample data

```json
{
  "name": "sample_stream",
  "type": "Sample",
  "config": {
    "interval": {"size": 1, "unit": "second"},
    "format": "samplestock"
  }
}
```

**Available Formats**:
- `samplestock`: Financial market data
- `sampleweather`: Weather sensor data
- `sampleiot`: IoT device telemetry
- `samplelog`: Application log entries
- `samplecommerce`: E-commerce events

### 3. HTTP/HTTPS Connection

**Purpose**: Connect to external REST APIs for data enrichment

```json
{
  "name": "external_api",
  "type": "HTTP",
  "config": {
    "baseUrl": "{{API_BASE_URL}}",
    "headers": {
      "Authorization": "Bearer {{API_TOKEN}}",
      "Content-Type": "application/json",
      "User-Agent": "StreamProcessor/1.0"
    },
    "timeoutMs": 30000,
    "maxRetries": 3
  }
}
```

**Configuration Options**:
- `baseUrl`: Base URL for API endpoints
- `headers`: Authentication and content headers
- `timeoutMs`: Request timeout in milliseconds
- `maxRetries`: Number of retry attempts for failed requests

### 4. Kafka Connection

**Purpose**: Connect to Apache Kafka for streaming data ingestion

```json
{
  "name": "kafka_stream",
  "type": "Kafka",
  "config": {
    "bootstrapServers": "{{KAFKA_BOOTSTRAP_SERVERS}}",
    "topics": ["{{KAFKA_TOPIC}}"],
    "groupId": "{{CONSUMER_GROUP_ID}}",
    "securityProtocol": "SASL_SSL",
    "saslMechanism": "PLAIN",
    "saslUsername": "{{KAFKA_USERNAME}}",
    "saslPassword": "{{KAFKA_PASSWORD}}"
  }
}
```

**Security Protocols**:
- `PLAINTEXT`: No encryption or authentication
- `SSL`: SSL encryption only
- `SASL_PLAINTEXT`: SASL authentication only
- `SASL_SSL`: Both SSL encryption and SASL authentication

### 5. EventBridge Connection

**Purpose**: Connect to AWS EventBridge for cloud-native event processing

```json
{
  "name": "eventbridge_source",
  "type": "EventBridge",
  "config": {
    "region": "{{AWS_REGION}}",
    "eventSourceName": "{{EVENT_SOURCE_NAME}}",
    "accessKeyId": "{{AWS_ACCESS_KEY_ID}}",
    "secretAccessKey": "{{AWS_SECRET_ACCESS_KEY}}"
  }
}
```

**Configuration Requirements**:
- AWS region where EventBridge is configured
- Valid AWS credentials with EventBridge permissions
- Event source name for routing

## Security and Authentication Patterns

### API Key Authentication

```json
{
  "headers": {
    "X-API-Key": "{{API_KEY}}",
    "Content-Type": "application/json"
  }
}
```

### Bearer Token Authentication

```json
{
  "headers": {
    "Authorization": "Bearer {{ACCESS_TOKEN}}",
    "Content-Type": "application/json"
  }
}
```

### Basic Authentication

```json
{
  "headers": {
    "Authorization": "Basic {{BASE64_CREDENTIALS}}",
    "Content-Type": "application/json"
  }
}
```

### OAuth 2.0 (when supported)

```json
{
  "oauth": {
    "clientId": "{{OAUTH_CLIENT_ID}}",
    "clientSecret": "{{OAUTH_CLIENT_SECRET}}",
    "tokenUrl": "{{OAUTH_TOKEN_URL}}",
    "scope": "{{OAUTH_SCOPE}}"
  }
}
```

## External API Integration Examples

### RESTful Weather API

```json
{
  "name": "weather_api",
  "type": "HTTP",
  "config": {
    "baseUrl": "https://api.weatherservice.com/v1",
    "headers": {
      "Authorization": "Bearer {{WEATHER_API_TOKEN}}",
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    "timeoutMs": 15000,
    "maxRetries": 2
  }
}
```

### Financial Data Provider

```json
{
  "name": "market_data_api",
  "type": "HTTP",
  "config": {
    "baseUrl": "https://api.marketdata.com/v2",
    "headers": {
      "X-API-Key": "{{MARKET_DATA_KEY}}",
      "Content-Type": "application/json"
    },
    "timeoutMs": 5000,
    "maxRetries": 1
  }
}
```

### IoT Device Management API

```json
{
  "name": "iot_management_api",
  "type": "HTTP",
  "config": {
    "baseUrl": "https://iot.platform.com/api/v3",
    "headers": {
      "Authorization": "ApiKey {{IOT_API_KEY}}",
      "Content-Type": "application/json",
      "X-Device-Type": "sensor"
    },
    "timeoutMs": 20000,
    "maxRetries": 3
  }
}
```

## Performance and Reliability Configurations

### High-Throughput Kafka Setup

```json
{
  "name": "high_volume_kafka",
  "type": "Kafka",
  "config": {
    "bootstrapServers": "{{KAFKA_CLUSTER}}",
    "topics": ["high-volume-topic"],
    "groupId": "stream-processor-group",
    "autoOffsetReset": "latest",
    "maxPollRecords": 500,
    "fetchMinBytes": 1024,
    "fetchMaxWaitMs": 500,
    "sessionTimeoutMs": 30000,
    "heartbeatIntervalMs": 3000
  }
}
```

### Resilient HTTP Configuration

```json
{
  "name": "resilient_api",
  "type": "HTTP",
  "config": {
    "baseUrl": "{{API_ENDPOINT}}",
    "headers": {
      "Authorization": "Bearer {{API_TOKEN}}"
    },
    "timeoutMs": 10000,
    "maxRetries": 5,
    "retryDelayMs": 1000,
    "circuitBreakerThreshold": 10,
    "circuitBreakerTimeoutMs": 60000
  }
}
```

## Variable Substitution Patterns

All connection configurations support variable substitution using the `{{VARIABLE_NAME}}` syntax. Variables are resolved from:

1. **Environment variables** in the Atlas project
2. **App Services values** (for sensitive data)
3. **Build-time configuration** (for deployment-specific values)

### Common Variable Patterns

```json
{
  "database_connection": {
    "clusterName": "{{ENVIRONMENT}}-cluster",
    "database": "{{APP_NAME}}_{{ENVIRONMENT}}"
  },
  "api_connection": {
    "baseUrl": "{{API_BASE_URL}}/{{API_VERSION}}",
    "headers": {
      "Authorization": "Bearer {{API_TOKEN_SECRET}}",
      "X-Environment": "{{DEPLOYMENT_ENVIRONMENT}}"
    }
  }
}
```

## Development and Testing Configurations

### Local Development

```json
{
  "name": "local_cluster",
  "type": "Cluster",
  "config": {
    "clusterName": "{{DEV_CLUSTER_NAME}}",
    "readPreference": "primary"
  }
}
```

### Testing with Sample Data

```json
{
  "name": "test_stream",
  "type": "Sample",
  "config": {
    "interval": {"size": 100, "unit": "millisecond"},
    "format": "sampleiot",
    "seed": 12345
  }
}
```

### Mock API for Testing

```json
{
  "name": "mock_api",
  "type": "HTTP",
  "config": {
    "baseUrl": "{{MOCK_API_URL}}",
    "headers": {
      "Content-Type": "application/json"
    },
    "timeoutMs": 1000,
    "maxRetries": 1
  }
}
```

## AI Configuration Guidelines

When generating connection configurations:

1. **Identify the data source type** - Determine if it's a database, API, stream, or sample data
2. **Choose appropriate connection type** - Match the source to the correct connection type
3. **Configure authentication** - Use the proper authentication method for the source
4. **Set appropriate timeouts** - Balance responsiveness with reliability
5. **Use variable substitution** - Keep sensitive data in variables, not hardcoded
6. **Consider environment differences** - Use variables for environment-specific values
7. **Plan for failure scenarios** - Configure retries and circuit breakers appropriately

### Connection Naming Conventions

- Use descriptive names: `user_profile_api`, `orders_kafka_stream`, `analytics_cluster`
- Include environment when needed: `prod_orders_cluster`, `dev_sample_stream`
- Be consistent across related processors: `weather_api` + `weather_data_cluster`

### Security Best Practices

- Never hardcode credentials in connection configurations
- Use App Services values for sensitive data like API keys and passwords
- Implement appropriate timeout values to prevent hanging connections
- Configure retry policies to handle transient failures
- Use SSL/TLS encryption when available

Always verify connection configurations against the latest MongoDB Atlas Stream Processing documentation before deployment.
