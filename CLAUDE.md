# MongoDB Atlas Stream Processing (ASP) Implementation & Development Guide

## 1. Logic Guardrails & Architectural Rules (CRITICAL)
Claude must strictly adhere to these constraints when generating or editing JSON in the `processors/` directory.

### The "Linear" Rule
* **One Source, One Sink:** Every pipeline MUST start with exactly one `$source` stage and end with exactly one sink stage (`$emit` or `$merge`).
* **No Branching:** `$facet` is NOT supported. ASP pipelines are linear.
* **Side Outputs:** To achieve "side outputs" or parallel processing paths, you must define **multiple separate processor files** reading from the same source.
* **Prohibited Stages:** Never suggest `$out`, `$graphLookup`, or `$indexStats`.
* **Bounded Sort:** `$sort` is only permitted inside a `$window` stage to ensure operations are bounded by time or count.

### Enrichment Strategy
* **Multiple Lookups:** While only one `$source` (the trigger) is allowed, a pipeline can contain multiple `$lookup` or `$cachedLookup` stages for data enrichment.
* **Lookup Choice:** Use `$lookup` for real-time accuracy; use `$cachedLookup` for high-performance reference data (requires SP30+ tier).

---

## 2. Flink to ASP Translation Mapping
When users describe streaming patterns in SQL or Flink terminology, translate to ASP-native stages:

| Flink/SQL Concept | ASP Equivalent (The Pivot) |
| :--- | :--- |
| **`MATCH_RECOGNIZE`** | Use native **`$match`** or **`$window`**. |
| **`Watermarks`** | Use **`idleTimeout`** and **`expireAfter`** within **`$window`**. |
| **`KeyBy` / `Partition By`** | Use **`partitionBy`** within the **`$window`** stage. |
| **`Side Outputs`** | Create a **separate processor file** in `/processors`. |
| **`UDF`** | Use **`$function`** (JS) or **`$externalFunction`** (Lambda). |

---

## 3. Tier-Aware Recommendations
When starting a processor, recommend or select a tier based on this logic:
* **SP2 / SP5:** Basic filtering (`$match`), transformation (`$project`), or prototyping.
* **SP10:** Production ETL and standard **`$lookup`**.
* **SP30:** Required for **`$cachedLookup`**, heavy stateful **`$window`** operations.
* **SP50:** Required for **JavaScript `$function`**, ultra-high throughput, or parallelism > 16.

---

## 4. Operational Setup & Directory Structure
This repository follows a **"processors are files"** philosophy.

### Directory Structure

- **CLAUDE.md**: This file (Project instructions and rules)
- **config.txt.example**: Template for Atlas API credentials
- **.claude-plugin/**: Claude Code plugin manifest and metadata
- **tools/sp/**: Core CLI toolkit (sp, atlas_api.py, sp-schema.json)
- **processors/**: Store processor JSON files here (*.json)
- **connections/**: Connection configurations (connections.json)
- **skills/**: Domain-specific Claude skills
- **docs/**: Detailed technical documentation

### Setup
1. **Configure credentials** - Copy `config.txt.example` to `config.txt` and fill in API keys.
2. **Install dependencies**: `pip install -r tools/sp/requirements.txt`
3. **Make sp executable**: `chmod +x tools/sp/sp`

---

## 5. Core CLI Commands

### Workspace & Connection Management
```bash
# Workspaces
./tools/sp/sp workspaces list
./tools/sp/sp workspaces create <name> --cloud-provider AWS --region US_EAST_1

# Connections
./tools/sp/sp instances connections create   # From connections.json
./tools/sp/sp instances connections list
./tools/sp/sp instances connections test     # Verifies connectivity
```
### Processor Management
```bash
# Create and Start
./tools/sp/sp processors create -p <name>    # Creates from processors/<name>.json
./tools/sp/sp processors start -p <name> --auto

# Monitor and Troubleshoot
./tools/sp/sp processors list
./tools/sp/sp processors stats -p <name>
./tools/sp/sp processors profile -p <name> --duration 300
./tools/sp/sp processors tier-advise -p <name>

# Lifecycle
./tools/sp/sp processors stop -p <name>
./tools/sp/sp processors drop -p <name>
```

## 6. Example Pipeline (Multi-source enrichment)
```
{
  "name": "enriched_order_stream",
  "pipeline": [
    { "$source": { "connectionName": "kafka_orders" } },
    {
      "$lookup": {
        "from": { "connectionName": "atlas_cluster", "db": "crm", "coll": "users" },
        "localField": "userId", "foreignField": "_id", "as": "user"
      }
    },
    {
      "$window": {
        "type": "tumbling",
        "interval": { "size": 1, "unit": "hour" },
        "pipeline": [
          { "$group": { "_id": "$userId", "total": { "$sum": "$amount" } } }
        ]
      }
    },
    { "$merge": { "into": { "connectionName": "atlas_cluster", "db": "reports", "coll": "hourly" } } }
  ]
}
```
