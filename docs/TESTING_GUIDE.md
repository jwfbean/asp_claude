# Atlas Stream Processing - Testing Guide

## Connection Testing Framework

This guide covers the comprehensive Python-based testing framework for verifying Atlas Stream Processing connections with optional MongoDB native driver verification.

## Quick Start

### Basic Test (Stream Processing Only)

To test your current connections using Stream Processing only:

```bash
cd /path/to/ASP_base
source venv/bin/activate  # if using virtual environment
python3 test/test_connection.py
```

### Enhanced Test (with MongoDB Native Driver Verification)

For authoritative verification using MongoDB native driver:

```bash
# Set your MongoDB connection string
export MONGODB_CONNECTION_STRING='mongodb+srv://<username>:<password>@kgshardedcluster01.mongodb.net/'

# Run the enhanced test
./test_with_verification.sh
```

## MongoDB Native Driver Verification

The enhanced testing framework now includes **authoritative verification** using the MongoDB native Python driver (pymongo). This provides definitive proof that:

1. Data was successfully written to your Atlas cluster
2. The connection configuration is working correctly
3. Your Stream Processing setup can read and write data

### Setting Up MongoDB Verification

1. **Get your MongoDB connection string** from Atlas:
   - Go to your Atlas cluster
   - Click "Connect" → "Connect your application"
   - Copy the connection string
   - Replace `<username>` and `<password>` with your credentials

2. **Set the environment variable**:
   ```bash
   export MONGODB_CONNECTION_STRING='mongodb+srv://user:pass@kgshardedcluster01.mongodb.net/'
   ```

3. **Run the enhanced test**:
   ```bash
   ./test_with_verification.sh
   ```

### What MongoDB Verification Provides

- **Direct Connection**: Connects directly to your Atlas cluster using native MongoDB driver
- **Document Counts**: Shows exact number of documents in each test collection
- **Sample Data**: Displays sample documents to verify data structure
- **Authoritative Results**: Provides definitive proof of connection success
- **Error Details**: Shows specific connection or permission issues

## What the Test Does

The connection test performs a complete round-trip verification:

1. **Write Test**: Creates a processor that writes test data to your Atlas cluster
2. **Read Test**: Creates a processor that reads from your cluster and writes to a verification collection
3. **Verification**: Creates a summary processor that validates the connection is working

### Test Data Flow

```
Stream Processor → Atlas Cluster (test.connection_verification)
     ↓
Atlas Cluster → Stream Processor → Atlas Cluster (test.connection_test_results)
     ↓
Summary Generator → Atlas Cluster (test.connection_test_summary)
```

## Test Results

After running the test, check your Atlas cluster for these collections in the `test` database:

- `connection_verification` - Raw test data written by the first processor
- `connection_test_results` - Round-trip data proving read/write capability
- `connection_test_summary` - Summary of the connection test

## Test Components

### Test Directory Structure

```
test/
├── test_connection.py           # Main testing framework
├── connection_test_writer.json  # Processor that writes test data
├── connection_test_reader.json  # Processor that reads and transforms data
└── connection_test_verify.json  # Processor that creates test summary
```

### StreamProcessingTester Class

The Python testing framework includes:

- **Processor Lifecycle Management**: Create, start, stop, delete processors
- **Temporary File Handling**: Automatically manages test processor files
- **Error Recovery**: Cleans up failed test artifacts
- **Real-time Feedback**: Provides detailed progress updates

## Customizing Tests

### Adding New Test Processors

1. Create a new JSON processor definition in the `test/` directory
2. Add the processor to the test flow in `test_connection.py`
3. Update the cleanup routine to handle your new processor

### Testing Different Connections

The test uses the active connection from `connections/connections.json`. To test a different connection:

1. Update your connections.json file with the target connection
2. Run the test - it will automatically use the first connection in the file

## Troubleshooting

### Common Issues

**"Processor creation failed"**
- Check that your connection is active and accessible
- Verify your Atlas cluster allows the configured database role
- Ensure the processor JSON files are valid

**"No data found in verification collections"**
- The processors may need more time to process data
- Check Atlas cluster connectivity
- Verify your database permissions allow writes to the `test` database

**"SP command not found"**
- Ensure you're running from the ASP_base directory
- The test looks for the `sp` tool in `tools/sp`

### Manual Verification

If automated verification fails, you can manually check:

1. Log into Atlas and navigate to your cluster
2. Browse to the `test` database
3. Check the verification collections for test data
4. If data exists, your connection is working correctly

## Integration with CI/CD

The test script returns proper exit codes:
- `0` for successful connection test
- `1` for failed connection test

This makes it suitable for automated testing pipelines.

## Best Practices

1. **Run tests on a dedicated test cluster** to avoid interfering with production data
2. **Clean up test data regularly** - the test collections can accumulate over time
3. **Monitor test execution time** - slow tests may indicate connection issues
4. **Use descriptive test data** - makes manual verification easier

## Advanced Usage

### Running Individual Test Steps

You can modify `test_connection.py` to run individual test components:

```python
tester = StreamProcessingTester()
tester.create_processor("connection_test_writer.json")
tester.start_processor("connection_test_writer")
# ... manual verification
tester.cleanup()
```

### Custom Test Data

Modify the processor JSON files to test with your specific data patterns and requirements.
