# Stream Processing Pipeline Patterns

This document provides AI systems with proven patterns for building MongoDB Atlas Stream Processing pipelines. Use these patterns as building blocks for generating custom stream processors.

## Deploying Patterns with `sp` Utility

**ESSENTIAL**: All pipeline patterns must be deployed using the `sp` utility:

```bash
# Navigate to tools directory
cd tools/

# Create processor JSON files in processors/ directory
# Then deploy with:
./sp create processors

# Monitor deployment:
./sp list
./sp stats
```

## Reference Sources

Before implementing any pattern, consult the latest documentation:

- **Pipeline Stages Reference**: [MongoDB Atlas Stream Processing Pipeline Stages](https://www.mongodb.com/docs/atlas/atlas-stream-processing/pipeline-stages/)
- **Official Examples**: [MongoDB ASP Example Repository](https://github.com/mongodb/asp_example)
- **Aggregation Operators**: [MongoDB Manual Aggregation](https://www.mongodb.com/docs/manual/reference/operator/aggregation/)

> Always check these sources for the most current syntax and available operators.

## Common Pipeline Patterns

### 1. Basic Data Ingestion with Filtering

**Use Case**: Simple data collection with basic filtering to remove inactive or invalid records

```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "data_source",
        "timeField": {"$dateFromString": {"dateString": "$timestamp"}}
      }
    },
    {
      "$match": {
        "status": {"$ne": "inactive"},
        "temperature": {"$gt": 0}
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "atlas_cluster",
          "db": "raw_data",
          "coll": "ingested_records"
        }
      }
    }
  ]
}
```

### 2. Real-time Filtering and Alerting

**Use Case**: Monitor data streams for specific conditions and generate alerts

```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "sensor_stream",
        "timeField": {"$dateFromString": {"dateString": "$timestamp"}}
      }
    },
    {
      "$match": {
        "$or": [
          {"temperature": {"$gt": 80}},
          {"humidity": {"$lt": 20}},
          {"pressure": {"$not": {"$gte": 1000, "$lte": 1100}}}
        ]
      }
    },
    {
      "$addFields": {
        "alert_type": {
          "$switch": {
            "branches": [
              {"case": {"$gt": ["$temperature", 80]}, "then": "HIGH_TEMPERATURE"},
              {"case": {"$lt": ["$humidity", 20]}, "then": "LOW_HUMIDITY"},
              {"case": {"$not": {"$and": [{"$gte": ["$pressure", 1000]}, {"$lte": ["$pressure", 1100]}]}}, "then": "PRESSURE_ANOMALY"}
            ],
            "default": "UNKNOWN"
          }
        },
        "alert_severity": {
          "$switch": {
            "branches": [
              {"case": {"$gt": ["$temperature", 90]}, "then": "CRITICAL"},
              {"case": {"$lt": ["$humidity", 10]}, "then": "CRITICAL"}
            ],
            "default": "WARNING"
          }
        },
        "alert_timestamp": "$$NOW",
        "alert_message": {
          "$concat": [
            "Alert: ",
            "$alert_type",
            " detected. Value: ",
            {"$toString": "$value"}
          ]
        }
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "atlas_cluster",
          "db": "alerts",
          "coll": "realtime_alerts"
        }
      }
    }
  ]
}
```

### 3. Time-based Aggregation

**Use Case**: Create periodic summaries and statistics from streaming data

```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "metrics_stream",
        "timeField": {"$dateFromString": {"dateString": "$timestamp"}}
      }
    },
    {
      "$tumblingWindow": {
        "interval": {"size": 5, "unit": "minute"},
        "pipeline": [
          {
            "$group": {
              "_id": {
                "sensor_id": "$sensor_id",
                "location": "$location"
              },
              "avg_value": {"$avg": "$value"},
              "min_value": {"$min": "$value"},
              "max_value": {"$max": "$value"},
              "count": {"$sum": 1},
              "stddev": {"$stdDevPop": "$value"},
              "first_timestamp": {"$min": "$timestamp"},
              "last_timestamp": {"$max": "$timestamp"}
            }
          },
          {
            "$addFields": {
              "window_start": "$_stream_meta.window.start",
              "window_end": "$_stream_meta.window.end",
              "aggregation_timestamp": "$$NOW",
              "variance": {"$pow": ["$stddev", 2]}
            }
          }
        ]
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "atlas_cluster",
          "db": "analytics",
          "coll": "five_minute_summaries"
        }
      }
    }
  ]
}
```

### 4. API Enrichment Pattern

**Use Case**: Enrich streaming data with external API calls

```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "events_stream"
      }
    },
    {
      "$match": {
        "user_id": {"$exists": true}
      }
    },
    {
      "$https": {
        "connectionName": "user_profile_api",
        "method": "GET",
        "path": {
          "$concat": ["/users/", {"$toString": "$user_id"}]
        },
        "as": "user_profile"
      }
    },
    {
      "$addFields": {
        "enriched_data": {
          "user_name": "$user_profile.name",
          "user_tier": "$user_profile.tier",
          "user_location": "$user_profile.location"
        },
        "enrichment_timestamp": "$$NOW"
      }
    },
    {
      "$project": {
        "user_profile": 0
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "atlas_cluster",
          "db": "enriched_events",
          "coll": "user_events"
        }
      }
    }
  ]
}
```

### 5. Complex Event Processing

**Use Case**: Detect patterns across multiple events in a time window

```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "transaction_stream",
        "timeField": {"$dateFromString": {"dateString": "$timestamp"}}
      }
    },
    {
      "$tumblingWindow": {
        "interval": {"size": 10, "unit": "minute"},
        "pipeline": [
          {
            "$group": {
              "_id": "$account_id",
              "transactions": {
                "$push": {
                  "amount": "$amount",
                  "timestamp": "$timestamp",
                  "type": "$transaction_type",
                  "merchant": "$merchant"
                }
              },
              "total_amount": {"$sum": "$amount"},
              "transaction_count": {"$sum": 1},
              "unique_merchants": {"$addToSet": "$merchant"}
            }
          },
          {
            "$addFields": {
              "fraud_score": {
                "$let": {
                  "vars": {
                    "high_amount_count": {
                      "$size": {
                        "$filter": {
                          "input": "$transactions",
                          "cond": {"$gt": ["$$this.amount", 1000]}
                        }
                      }
                    },
                    "merchant_count": {"$size": "$unique_merchants"}
                  },
                  "in": {
                    "$add": [
                      {"$multiply": ["$$high_amount_count", 30]},
                      {"$multiply": ["$$merchant_count", 10]},
                      {"$multiply": ["$transaction_count", 5]}
                    ]
                  }
                }
              }
            }
          },
          {
            "$match": {
              "$or": [
                {"fraud_score": {"$gte": 80}},
                {"transaction_count": {"$gte": 20}},
                {"total_amount": {"$gte": 10000}}
              ]
            }
          }
        ]
      }
    },
    {
      "$addFields": {
        "alert_type": "FRAUD_DETECTION",
        "risk_level": {
          "$switch": {
            "branches": [
              {"case": {"$gte": ["$fraud_score", 90]}, "then": "HIGH"},
              {"case": {"$gte": ["$fraud_score", 70]}, "then": "MEDIUM"}
            ],
            "default": "LOW"
          }
        },
        "investigation_required": {"$gte": ["$fraud_score", 80]}
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "atlas_cluster",
          "db": "security",
          "coll": "fraud_alerts"
        }
      }
    }
  ]
}
```

### 6. Data Transformation and Normalization

**Use Case**: Clean, transform, and standardize incoming data

```json
{
  "pipeline": [
    {
      "$source": {
        "connectionName": "mixed_format_stream"
      }
    },
    {
      "$addFields": {
        "normalized_timestamp": {
          "$switch": {
            "branches": [
              {
                "case": {"$type": ["$timestamp", "string"]},
                "then": {"$dateFromString": {"dateString": "$timestamp"}}
              },
              {
                "case": {"$type": ["$timestamp", "long"]},
                "then": {"$toDate": "$timestamp"}
              }
            ],
            "default": "$$NOW"
          }
        },
        "normalized_value": {
          "$switch": {
            "branches": [
              {
                "case": {"$type": ["$value", "string"]},
                "then": {"$toDouble": "$value"}
              }
            ],
            "default": "$value"
          }
        },
        "clean_location": {
          "$trim": {
            "input": {"$toUpper": "$location"},
            "chars": " \t\n\r"
          }
        }
      }
    },
    {
      "$match": {
        "normalized_value": {"$type": "number"},
        "clean_location": {"$ne": ""}
      }
    },
    {
      "$project": {
        "timestamp": "$normalized_timestamp",
        "value": "$normalized_value",
        "location": "$clean_location",
        "source_system": 1,
        "processing_timestamp": "$$NOW",
        "data_quality_score": {
          "$add": [
            {"$cond": [{"$ne": ["$timestamp", null]}, 25, 0]},
            {"$cond": [{"$type": ["$normalized_value", "number"]}, 25, 0]},
            {"$cond": [{"$ne": ["$clean_location", ""]}, 25, 0]},
            {"$cond": [{"$ne": ["$source_system", null]}, 25, 0]}
          ]
        }
      }
    },
    {
      "$merge": {
        "into": {
          "connectionName": "atlas_cluster",
          "db": "clean_data",
          "coll": "normalized_records"
        }
      }
    }
  ]
}
```

## Error Handling Patterns

### Standard DLQ Configuration

Always include dead letter queue configuration:

```json
{
  "options": {
    "dlq": {
      "connectionName": "atlas_cluster",
      "db": "errors",
      "coll": "processor_dlq"
    }
  }
}
```

### Graceful Degradation

Handle missing fields and data quality issues:

```json
{
  "$addFields": {
    "processed_value": {
      "$ifNull": [
        "$value",
        {"$ifNull": ["$backup_value", 0]}
      ]
    },
    "data_completeness": {
      "$divide": [
        {"$add": [
          {"$cond": [{"$ne": ["$field1", null]}, 1, 0]},
          {"$cond": [{"$ne": ["$field2", null]}, 1, 0]},
          {"$cond": [{"$ne": ["$field3", null]}, 1, 0]}
        ]},
        3
      ]
    }
  }
}
```

## Performance Optimization Patterns

### Efficient Filtering

Place `$match` stages early in the pipeline:

```json
{
  "pipeline": [
    {"$source": {"connectionName": "high_volume_stream"}},
    {
      "$match": {
        "timestamp": {"$gte": {"$subtract": ["$$NOW", 86400000]}},
        "active": true
      }
    },
    // ... rest of pipeline
  ]
}
```

### Selective Field Projection

Use `$project` to reduce data volume:

```json
{
  "$project": {
    "essential_field1": 1,
    "essential_field2": 1,
    "computed_field": {"$add": ["$field1", "$field2"]},
    "_id": 0,
    "large_unused_field": 0
  }
}
```

## Window Processing Best Practices

### Tumbling Windows for Regular Aggregations

```json
{
  "$tumblingWindow": {
    "interval": {"size": 1, "unit": "hour"},
    "allowedLateness": {"size": 5, "unit": "minute"},
    "pipeline": [
      {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
  }
}
```

### Hopping Windows for Sliding Calculations

```json
{
  "$hoppingWindow": {
    "interval": {"size": 1, "unit": "hour"},
    "hop": {"size": 15, "unit": "minute"},
    "allowedLateness": {"size": 2, "unit": "minute"},
    "pipeline": [
      {"$group": {"_id": null, "moving_average": {"$avg": "$value"}}}
    ]
  }
}
```

## AI Implementation Guidelines

When generating stream processors:

1. **Start with the use case** - Identify whether it's ingestion, alerting, aggregation, or enrichment
2. **Choose the appropriate pattern** - Use these patterns as templates
3. **Customize the logic** - Modify field names, conditions, and transformations
4. **Add error handling** - Include DLQ and graceful degradation
5. **Optimize for performance** - Order stages efficiently and project only needed fields
6. **Test incrementally** - Verify each stage works before adding complexity

Always refer to the official MongoDB documentation for the latest pipeline stage syntax and available operators.

## Pattern Implementation Workflow

When implementing any pattern from this guide:

### Step 1: Create Processor JSON

```json
{
  "name": "my_processor_name",
  "pipeline": [
    // Use pattern from above sections
  ],
  "options": {
    "dlq": {
      "connectionName": "atlas_cluster",
      "db": "errors", 
      "coll": "dlq"
    }
  }
}
```

### Step 2: Deploy with `sp` Utility

```bash
# Navigate to tools directory
cd tools/

# Save JSON file to processors/ directory first
# Then deploy:
./sp create processors

# Verify deployment:
./sp list

# Start if needed:
./sp start

# Monitor performance:
./sp stats
```

### Step 3: Validate and Monitor

- Check processor status with `./sp list`
- Monitor performance with `./sp stats`
- Verify output data in destination collections
- Check DLQ collections for any errors
- Use `./sp restart` if configuration changes are needed

**Remember**: Always use the `sp` utility for all processor operations. Never deploy processors manually or with other tools.
