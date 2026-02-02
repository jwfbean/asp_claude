# Stream Processor Output Patterns - Understanding Low/Zero Output Scenarios

## Document Date
Dec 11, 2025

## Overview

Not all stream processors are designed to produce high output volumes. Many processors are specifically designed as **filters, alerting systems, or anomaly detectors** where low or zero output is actually a sign of healthy operation. This document helps distinguish between problematic processors and those performing their intended function.

## Common Low/Zero Output Patterns

### 1. **Alert/Anomaly Detection Processors**
These processors monitor for rare events and should produce minimal output under normal conditions.

#### Examples:
- **Lightning Detection**: `lightning_alert_processor`
  - **Expected Behavior**: Zero output when no lightning detected
  - **Good Sign**: No lightning storms = no alerts needed
  - **Red Flag**: High output (many lightning events)

- **Fraud Detection**: `fraud_detection_processor`
  - **Expected Behavior**: Very low output under normal conditions
  - **Good Sign**: Low fraud rate = healthy system
  - **Red Flag**: High output (fraud spike)

- **Security Monitoring**: `security_alert_processor`
  - **Expected Behavior**: Minimal output during normal operations
  - **Good Sign**: Few security incidents
  - **Red Flag**: Continuous alerts

### 2. **Quality Filters**
Processors that filter out bad/invalid data should have variable output based on data quality.

#### Examples:
- **Data Validation**: `data_quality_filter`
  - **Expected Behavior**: Output depends on input data quality
  - **Good Sign**: High-quality data = high pass-through rate
  - **Variable**: Poor data quality = low output (expected)

- **Temperature Range Filter**: `temperature_bounds_check`
  - **Expected Behavior**: Only pass readings within valid ranges
  - **Normal**: Output varies with environmental conditions

### 3. **Threshold-Based Processors**
Processors that only act when certain conditions are met.

#### Examples:
- **High Usage Alerts**: `resource_usage_monitor`
  - **Expected Behavior**: Only output when thresholds exceeded
  - **Good Sign**: Low output = resources within normal limits

- **Performance Degradation**: `latency_spike_detector`
  - **Expected Behavior**: Silence during good performance periods

## Decision Framework for Processor Analysis

### 🔍 **Before Stopping a Low-Output Processor, Ask:**

#### 1. **What is the processor's purpose?**
- [ ] Anomaly/alert detection → Low output may be normal
- [ ] Data transformation → Should have ~1:1 input/output ratio
- [ ] Enrichment → Should maintain or increase output volume
- [ ] Filtering → Variable output depending on filter criteria

#### 2. **What does zero/low output indicate for this specific use case?**
- [ ] **Alert processors**: No alerts = good (system healthy)
- [ ] **Filter processors**: Low output = poor data quality OR overly strict filters
- [ ] **Transform processors**: Low output = likely a problem
- [ ] **Routing processors**: Low output = routing rules may be too restrictive

#### 3. **Check the processor configuration:**
```json
// Example: Lightning alert processor
{
  "$match": {
    "weather.lightning_detected": true,
    "weather.lightning_intensity": { "$gt": 5 }
  }
}
// Zero output = No high-intensity lightning (GOOD!)
```

#### 4. **Review recent environmental conditions:**
- **Lightning detector**: Check weather reports - was lightning expected?
- **Fraud detector**: Is this a typically low-fraud period?
- **Error detector**: Have systems been stable recently?

### ⚠️ **Red Flags - When Low Output IS a Problem:**

1. **Transform/Processing Pipelines**
   - Expected to modify and pass through most input data
   - Should maintain reasonable input/output ratios

2. **Data Movement Pipelines**
   - Designed to move data from source to destination
   - Should have high pass-through rates

3. **Enrichment Pipelines**
   - Add fields or lookup additional data
   - Should output equal or more records than input

### ✅ **Green Flags - When Low Output is Expected:**

1. **Filter Conditions Met**
   ```json
   // This SHOULD filter out most data
   {
     "$match": {
       "temperature": { "$gt": 100, "$lt": -50 } // Extreme temps only
     }
   }
   ```

2. **Alert Conditions Not Met**
   ```json
   // This should only output during emergencies
   {
     "$match": {
       "emergency_level": { "$gte": 8 }
     }
   }
   ```

3. **Quality Thresholds**
   ```json
   // This should reject poor quality data
   {
     "$match": {
       "data_quality_score": { "$gte": 0.95 }
     }
   }
   ```

## Monitoring Best Practices

### 1. **Document Processor Intent**
Always document in your processor files what the expected output behavior should be:

```json
{
  "name": "lightning_alert_processor",
  "_metadata": {
    "purpose": "Alert on lightning detection",
    "expected_output": "Low/zero during normal weather (GOOD)",
    "concern_threshold": "High output indicates storm activity",
    "monitor_type": "alert_system"
  },
  "pipeline": [...]
}
```

### 2. **Use Different Metrics for Different Processor Types**

#### For Alert Systems:
- **Monitor**: Alert frequency trends
- **Metric**: Alerts per day/hour
- **Threshold**: Sudden spikes may indicate issues

#### For Data Processing:
- **Monitor**: Input/output ratios
- **Metric**: Percentage of data passed through
- **Threshold**: Sudden drops in pass-through rate

#### For Quality Filters:
- **Monitor**: Data quality trends
- **Metric**: Quality score distributions
- **Threshold**: Sudden changes in quality patterns

### 3. **Contextual Monitoring**
Consider external factors when evaluating processor performance:

- **Weather processors**: Check weather forecasts
- **Business processors**: Consider business hours, seasonality
- **Security processors**: Correlate with security events
- **IoT processors**: Consider device maintenance schedules

## Processor Classification Examples

### **Alert/Monitoring Processors** (Low output expected)
```bash
lightning_alert_processor          # Weather alerts
fraud_detection_processor          # Financial monitoring  
security_breach_detector          # Security monitoring
system_failure_alert             # Infrastructure monitoring
temperature_spike_detector       # Environmental alerts
```

### **Data Processing Processors** (High output expected)
```bash
data_transformation_processor     # Format conversion
enrichment_processor             # Data augmentation
routing_processor               # Data distribution
aggregation_processor          # Data summarization
```

### **Quality/Filter Processors** (Variable output expected)
```bash
data_quality_filter            # Remove invalid data
range_validator               # Boundary checking
duplicate_remover            # Deduplication
schema_validator            # Format validation
```

## Recommended Actions

### Before Stopping a Processor:

1. **Check processor classification** (alert vs. processing vs. filtering)
2. **Review configuration** for expected filtering behavior
3. **Consider external context** (weather, business conditions, etc.)
4. **Look at trends over time** rather than point-in-time snapshots
5. **Verify input data quality** and patterns

### When to Stop:

- **Processing pipelines** with unexpectedly low output
- **Data movement** pipelines not moving data
- **Enrichment** pipelines not enriching
- **Alert systems** that should be alerting but aren't (during known events)

### When to Keep Running:

- **Alert systems** during normal conditions (zero output = good)
- **Quality filters** during poor data quality periods  
- **Anomaly detectors** during normal operations
- **Threshold monitors** when thresholds aren't exceeded

## Summary

**The key insight**: A stream processor's output volume must be evaluated in the context of its intended function and current environmental conditions. Low or zero output can be either a sign of excellent performance (for alert systems) or a critical failure (for data processing systems). Always consider the processor's design purpose before making operational decisions.