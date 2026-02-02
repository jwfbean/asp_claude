# Atlas Stream Processing - Processor Sizing Guide

## Overview

This guide explains how to predict costs and resource requirements for your Atlas Stream Processing pipelines before deployment. By understanding your pipeline complexity and using our automated analysis tools, you can accurately estimate compute tiers and associated costs.

## Core Prediction Features

### 1. Tier Selection Algorithm
Our automated tier selection algorithm analyzes your processor definition and predicts the optimal compute tier based on:
- **Code Complexity Scoring**: JavaScript operations, loop structures, and computational intensity
- **Data Volume Analysis**: Expected throughput and batch processing requirements
- **Parallelism Requirements**: Multi-threading and concurrent processing needs
- **Memory Footprint**: Object creation, data structures, and buffering requirements

### 2. Profiling-Based Projections
Use historical profiling data to predict performance characteristics:
- **Trend Analysis**: Performance patterns over time to predict scaling needs
- **Resource Utilization**: Memory, CPU, and I/O requirements under load
- **Threshold Monitoring**: Identify bottlenecks before they impact performance

## Cost Prediction Methodology

### Step 1: Pipeline Analysis

#### Analyze Your JavaScript Code
```javascript
// Example: Simple filter (Low complexity)
if (record.temperature > 95) {
    return record;
}

// Example: Complex aggregation (High complexity)
const analysis = records.reduce((acc, record) => {
    const key = `${record.location}_${Math.floor(record.timestamp / 3600)}`;
    acc[key] = (acc[key] || 0) + record.value;
    return acc;
}, {});
```

#### Complexity Scoring Factors

| Factor | Weight | Impact |
|--------|--------|---------|
| **Simple Operations** | 1x | Basic filters, field mapping |
| **Mathematical Functions** | 2x | Math operations, calculations |
| **Loops/Iterations** | 3x | Array processing, data transformation |
| **Complex Logic** | 4x | Nested conditions, algorithms |
| **Data Structures** | 5x | Objects, arrays, complex aggregations |

### Step 2: Tier Prediction

#### Automatic Tier Selection
Use the SP tool to get tier recommendations:

```bash
# Analyze processor for tier recommendation
./sp analyze-tier processors/your_processor.json

# Output example:
# Predicted Tier: SP30 (Medium)
# Confidence: 85%
# Cost Estimate: $0.12/hour
# Reasoning: Moderate complexity (score: 15), high throughput expected
```

#### Manual Tier Assessment

| Tier | Complexity Score | Use Cases | Hourly Cost Estimate |
|------|------------------|-----------|---------------------|
| **SP10 (Small)** | 0-8 | Simple filters, basic transforms | $0.04/hour |
| **SP30 (Medium)** | 9-20 | Aggregations, calculations | $0.12/hour |
| **SP50 (Large)** | 21-35 | Complex algorithms, heavy processing | $0.28/hour |
| **SP100 (XLarge)** | 36+ | Machine learning, advanced analytics | $0.64/hour |

### Step 3: Volume-Based Scaling

#### Calculate Processing Requirements

```markdown
**Formula**: Base Cost × Volume Multiplier × Runtime Hours

**Volume Multipliers**:
- Low Volume (< 1K events/min): 1.0x
- Medium Volume (1K-10K events/min): 1.2x
- High Volume (10K-100K events/min): 1.5x
- Very High Volume (> 100K events/min): 2.0x
```

#### Example Calculation
```
Pipeline: Weather alert processing
- Complexity Score: 12 (Medium tier - SP30)
- Base Cost: $0.12/hour
- Expected Volume: 5K events/minute
- Volume Multiplier: 1.2x
- Runtime: 24 hours/day

Daily Cost = $0.12 × 1.2 × 24 = $3.46/day
Monthly Cost = $3.46 × 30 = $103.80/month
```

## Sizing Workflow

### Phase 1: Pre-Deployment Analysis

1. **Create Processor Definition**
   ```bash
   # Generate tier prediction
   ./sp analyze-tier processors/my_processor.json
   ```

2. **Review Complexity Report**
   ```
   Complexity Breakdown:
   - Basic Operations: 3 points
   - Mathematical Functions: 6 points  
   - Loop Structures: 9 points
   - Total Score: 18 (SP30 recommended)
   ```

3. **Estimate Volume Impact**
   - Analyze expected data throughput
   - Consider peak vs. average loads
   - Factor in growth projections

### Phase 2: Validation with Profiling

#### Test Run with Sample Data
```bash
# Deploy with minimal tier for testing
./sp create-workspace test-sizing SP10

# Run profiling to validate predictions
./sp profile test-sizing 30m 5m

# Review actual vs. predicted performance
```

#### Profiling Validation Metrics
```
Performance Validation:
✓ CPU Utilization: 65% (within SP30 range)
✓ Memory Usage: 1.2GB (within SP30 limits)
⚠ Latency Spikes: Consider SP50 for peak loads
✓ Throughput: Meeting requirements

Recommendation: SP30 confirmed, consider auto-scaling
```

### Phase 3: Cost Optimization

#### Multi-Tier Strategy
```markdown
**Peak Hours** (8 AM - 8 PM): SP50 (High volume)
**Off-Peak Hours** (8 PM - 8 AM): SP30 (Standard processing)
**Maintenance Windows** (2 AM - 4 AM): SP10 (Minimal processing)

**Cost Optimization**:
- Peak: $0.28 × 12 hours = $3.36
- Standard: $0.12 × 10 hours = $1.20  
- Minimal: $0.04 × 2 hours = $0.08
- **Daily Total**: $4.64 (vs $6.72 fixed SP50)
- **Monthly Savings**: $62.40
```

## Advanced Sizing Scenarios

### Scenario 1: Machine Learning Pipeline
```javascript
// High complexity: ML inference pipeline
const model_prediction = records.map(record => {
    const features = extractFeatures(record);
    const prediction = runInference(model, features);
    return enrichRecord(record, prediction);
});
```
**Predicted Tier**: SP100 (XLarge) - $0.64/hour
**Reasoning**: Complex ML operations, high memory requirements

### Scenario 2: Real-time Analytics
```javascript
// Medium complexity: Time-window aggregations  
const windowStats = processTimeWindow(records, {
    window: '5m',
    functions: ['avg', 'max', 'count']
});
```
**Predicted Tier**: SP30 (Medium) - $0.12/hour
**Reasoning**: Moderate aggregation complexity, time-based processing

### Scenario 3: Simple Data Routing
```javascript
// Low complexity: Conditional routing
if (record.priority === 'high') {
    emit('urgent_topic', record);
} else {
    emit('standard_topic', record);
}
```
**Predicted Tier**: SP10 (Small) - $0.04/hour
**Reasoning**: Simple conditional logic, minimal processing

## Monitoring and Adjustment

### Continuous Cost Optimization

1. **Set Up Continuous Profiling**
   ```bash
   ./sp profile-continuous my-workspace --threshold-memory 80 --threshold-cpu 75
   ```

2. **Monitor Cost Trends**
   - Review monthly usage reports
   - Identify optimization opportunities
   - Adjust tiers based on actual performance

3. **Automated Scaling Triggers**
   ```bash
   # Configure auto-scaling based on metrics
   ./sp configure-autoscale my-workspace \
     --scale-up-cpu 80 \
     --scale-down-cpu 40 \
     --scale-up-memory 75 \
     --scale-down-memory 30
   ```

### Cost Alerts and Budgets

```bash
# Set cost monitoring alerts
./sp set-cost-alert my-workspace \
  --monthly-budget 500 \
  --alert-threshold 80 \
  --notification-email admin@company.com
```

## Best Practices

### 1. Start Small, Scale Up
- Begin with lower tiers (SP10/SP30)
- Use profiling data to validate requirements
- Scale up based on actual performance needs

### 2. Optimize Code First
- Simplify JavaScript logic where possible
- Reduce unnecessary computations
- Optimize data structures and algorithms

### 3. Plan for Peak Loads
- Factor in traffic spikes and seasonal variations
- Consider auto-scaling for variable workloads
- Budget for 20-30% overhead for unexpected growth

### 4. Regular Performance Reviews
- Monthly cost and performance analysis
- Quarterly tier optimization reviews
- Annual capacity planning sessions

## Summary

Accurate cost prediction for Atlas Stream Processing requires:

1. **Understanding Pipeline Complexity** - Use our tier selection algorithm for initial estimates
2. **Validating with Profiling** - Test assumptions with real data and performance monitoring
3. **Optimizing Continuously** - Adjust tiers and configurations based on actual usage patterns

By following this sizing guide, you can confidently predict and optimize costs for your stream processing workloads while ensuring optimal performance for your applications.

## Quick Reference

| Complexity Level | Typical Operations | Recommended Tier | Est. Cost/Hour |
|------------------|-------------------|------------------|----------------|
| **Low** | Filters, routing, simple transforms | SP10 | $0.04 |
| **Medium** | Aggregations, calculations, joins | SP30 | $0.12 |
| **High** | Complex analytics, algorithms | SP50 | $0.28 |
| **Very High** | ML inference, advanced processing | SP100 | $0.64 |

*Note: Cost estimates are approximate and may vary based on region and specific usage patterns.*