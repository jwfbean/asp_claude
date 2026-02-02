# Atlas Stream Processing - Understanding Parallelism

## Document Date
Dec 11, 2025

Atlas Stream Processing uses parallelism to scale your data processing workloads. Each stream processor tier supports a maximum degree of parallelism, which determines how many parallel copies of your pipeline stages can run simultaneously.

## HOW PARALLELISM WORKS

You can add as many operators as you need to your pipeline. The number of operators does not count against your parallelism limit or affect your costs.

Every stage in your pipeline runs with a default parallelism of 1. This base level of parallelism is included in your stream processor tier at no additional cost.

**Scale Individual stages as needed:** When you need higher throughput for specific stages, you can increase their parallelism beyond 1. For example, you might set parallelism to 4 on a merge stage to handle higher data volumes.

**Only parallelism values greater than 1 count toward your tier's maximum.** Stages running at the default parallelism of 1 do not consume any of your parallelism budget.

## CALCULATING YOUR PARALLELISM

To determine if your pipeline fits within a tier's limits, sum the parallelism values for all stages where parallelism is greater than 1.

### Example Pipeline:

```
- Source stage:       parallelism = 1  (does not count)
- Transform stage:    parallelism = 1  (does not count)  
- Lookup stage:       parallelism = 4  (counts as 3, first is free)
- Merge stage:        parallelism = 4  (counts as 3, first is free)
- Sink stage:         parallelism = 1  (does not count)

Total Parallelism = 3 + 3 = 6
```

This pipeline requires a tier with a maximum parallelism of at least 6, such as SP10 or higher.

## STREAM PROCESSOR TIERS

Choose the tier that matches your parallelism requirements and workload size (AWS):

| Tier | Max Parallelism | vCPU | RAM    | Bandwidth  | Kafka Partitions |
|------|-----------------|------|--------|------------|-------------------|
| SP2  | 1               | 0.25 | 512 MB | 50 Mbps    | 32               |
| SP5  | 2               | 0.5  | 1 GB   | 125 Mbps   | 64               |
| SP10 | 8               | 1    | 2 GB   | 200 Mbps   | Unlimited        |
| SP30 | 16              | 2    | 8 GB   | 750 Mbps   | Unlimited        |
| SP50 | 64              | 8    | 32 GB  | 2500 Mbps  | Unlimited        |

Each tier provides dedicated compute, memory, and network resources. State storage is included at no additional cost.

## BILLING

You are charged per hour for each stream processor, but only while it is running. Billing is calculated per second, so you pay only for the exact time your processors are active.

### What's Included
- Compute resources (vCPU and RAM)
- Storage for your stream processor
- Base parallelism (parallelism = 1 for all stages)

### Additional Costs
- **Data Transfer:** Charged based on egress volume, cloud provider, and transfer type (intra-region, inter-region, or internet)
- **VPC Peering:** Available for AWS and Google Cloud workspaces
- **Private Link:** Secure connectivity for Kafka sources and sinks

## PARALLELISM CALCULATION RULES FOR AUTO-TIER SELECTION

### Key Principles:
1. **Only parallelism > 1 counts** toward tier limits
2. **Sum all parallelism values > 1** across all pipeline stages
3. **Default parallelism of 1 is free** and doesn't count

### Tier Selection Algorithm:
```
Total Parallelism = Sum of (parallelism - 1) for all stages where parallelism > 1

If Total Parallelism > 48:  → SP50 (max 64)
If Total Parallelism > 8:   → SP30 (max 16) 
If Total Parallelism > 1:   → SP10 (max 8)
If Total Parallelism = 1:   → SP5  (max 2)
If Total Parallelism = 0:   → SP2  (max 1)
```

### Example Calculations:

**Simple Pipeline (all parallelism = 1):**
- Total Parallelism = 0
- Required Tier: **SP2**

**Medium Pipeline:**
- Merge stage: parallelism = 4 (counts as 3, first is free)
- All other stages: parallelism = 1 (count as 0)
- Total Parallelism = 3
- Required Tier: **SP10**

**Complex Pipeline:**
- Lookup stage: parallelism = 6 (counts as 5, first is free)
- Merge stage: parallelism = 8 (counts as 7, first is free) 
- Total Parallelism = 12
- Required Tier: **SP30**

## API ERROR MESSAGES

When tier specification fails due to parallelism limits, the API returns:

```json
{
  "error": 400,
  "detail": "Operator parallelism requested exceeds limit for this tier. (Requested: X, Limit: Y). Minimum tier for this workload: SPxx or larger.",
  "errorCode": "STREAM_PROCESSOR_GENERIC_ERROR"
}
```

The auto-tier system parses these errors and automatically retries with the suggested tier.

---

For complete pricing details and the latest information, visit:
https://www.mongodb.com/docs/atlas/billing/stream-processing-costs/