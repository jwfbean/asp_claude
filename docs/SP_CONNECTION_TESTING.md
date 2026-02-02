# SP Tool - Connection Testing

The `sp` tool now includes **authoritative connection testing** with MongoDB native driver verification.

## New Command: `sp workspaces connections test`

### Purpose
Tests your Stream Processing connections with **authoritative verification** using the MongoDB native Python driver. This ensures your connections actually work by:

1. Creating test stream processors
2. Writing test data to your Atlas cluster
3. Reading test data back through Stream Processing
4. **Verifying the data exists using MongoDB native driver**

### Requirements

**MongoDB Connection String REQUIRED**: The test requires a MongoDB connection string to perform authoritative verification.

```bash
export MONGODB_CONNECTION_STRING='mongodb+srv://username:password@your-cluster.mongodb.net/'
```

### Usage

```bash
# Test connections with required MongoDB verification
./sp workspaces connections test

# Check help
./sp workspaces connections test --help
```

### Example Output

```
 Launching Atlas Stream Processing Connection Test
 MongoDB Native Driver Verification: REQUIRED
============================================================

 Starting Atlas Stream Processing Connection Test
 MongoDB Native Driver Verification: REQUIRED
==================================================
 MongoDB native driver verification enabled - proceeding with test

 Step 1: Testing write capability...
 Processor connection_test_writer created successfully
 Processor connection_test_writer started successfully
 Waiting 20 seconds for connection_test_writer to process data...

 Step 2: Testing read capability...
 Processor connection_test_reader created successfully
 Processor connection_test_reader started successfully
 Waiting 15 seconds for connection_test_reader to process data...

 Step 3: Creating verification summary...
 Processor connection_test_verify created successfully

 Step 4: Authoritative verification with MongoDB native driver...
 Connecting to MongoDB cluster: KGShardedCluster01
 MongoDB connection successful!

 Verifying test data in database: test
 connection_verification: 15 documents found
 connection_test_results: 8 documents found  
 connection_test_summary: 1 documents found

 VERIFICATION SUCCESSFUL: Data confirmed in Atlas cluster!
 Your Stream Processing connection is working correctly!
```

### Why MongoDB Verification is Required

- **Authoritative Proof**: Directly verifies data exists in your Atlas cluster
- **No Guesswork**: Eliminates uncertainty about whether Stream Processing actually worked
- **Production Confidence**: Ensures your connection configuration will work in production
- **Debugging Aid**: Shows exactly what data was written and where

### Integration

This command integrates seamlessly with the existing `sp` tool structure:

```
sp workspaces
├── list
├── create
├── delete
├── details
└── connections
    ├── create
    ├── list
    ├── delete
    └── test ← NEW: Authoritative testing
```

### Error Handling

The command will fail with clear error messages if:

- MongoDB connection string is not set
- MongoDB connection fails
- No data is found in test collections
- Stream Processing connections are misconfigured

This ensures you only get success when your connection is **actually working**.
