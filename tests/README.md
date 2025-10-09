# MyAgent Manager Tests

Comprehensive test suite for the MyAgent WebSocket Management System.

## Test Structure

```
tests/
├── conftest.py                    # Root pytest configuration
├── manager/                       # Manager system tests
│   ├── fixtures/                  # Test fixtures and helpers
│   │   ├── conftest.py           # Manager-specific fixtures
│   │   └── helpers.py            # Test utility functions
│   ├── unit/                     # Unit tests
│   │   ├── test_service_registry.py
│   │   ├── test_connection_router.py
│   │   ├── test_health_monitor.py
│   │   └── test_api_server.py
│   └── integration/              # Integration tests
│       └── test_e2e_lifecycle.py
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Module
```bash
pytest tests/manager/unit/test_service_registry.py
```

### Run Tests by Marker
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run with Coverage
```bash
pytest --cov=myagent --cov-report=html
```

## Test Categories

### Unit Tests (P0)
Core functionality tests that run quickly without external dependencies:
- `test_service_registry.py` - Service registration, start, stop, restart
- `test_connection_router.py` - Connection routing and load balancing
- `test_health_monitor.py` - Health checking and monitoring
- `test_api_server.py` - API endpoint tests

### Integration Tests (P1)
End-to-end tests that verify component interactions:
- `test_e2e_lifecycle.py` - Complete service lifecycle workflows
- `test_e2e_routing.py` - Connection routing with real services (TODO)
- `test_e2e_auto_restart.py` - Auto-restart mechanism (TODO)

### Stress Tests (P2)
Performance and load tests:
- Many services registration (50+)
- Many concurrent connections (100+)
- High message throughput

## Test Fixtures

### Common Fixtures (`conftest.py`)
- `temp_dir` - Temporary directory for test files
- `temp_db_path` - Temporary SQLite database
- `sample_agent_file` - Sample agent factory file
- `event_loop` - Async event loop for tests

### Manager Fixtures (`manager/fixtures/conftest.py`)
- `repository` - ServiceRepository instance
- `service_registry` - ServiceRegistry instance
- `connection_router` - ConnectionRouter instance
- `health_monitor` - HealthMonitor instance
- `agent_manager` - AgentManager instance
- `sample_service` - Sample AgentService
- `multiple_services` - List of multiple services
- `mock_websocket` - Mock WebSocket connection
- `mock_process` - Mock subprocess.Popen

### Helper Utilities (`manager/fixtures/helpers.py`)
- `find_free_port()` - Find available port
- `create_test_agent_file()` - Create test agent file
- `wait_for_condition()` - Wait for async condition
- `assert_service_equals()` - Compare service objects
- `MockWebSocketServer` - Mock WebSocket server
- `ServiceBuilder` - Builder for test services

## Test Markers

```python
@pytest.mark.unit         # Unit test
@pytest.mark.integration  # Integration test
@pytest.mark.slow         # Slow running test
@pytest.mark.asyncio      # Async test (required for async functions)
```

## Writing Tests

### Unit Test Example
```python
import pytest

@pytest.mark.unit
class TestMyComponent:
    @pytest.mark.asyncio
    async def test_my_feature(self, my_fixture):
        """Test my feature."""
        result = await my_component.do_something()
        assert result == expected
```

### Integration Test Example
```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
class TestE2EFlow:
    @pytest.mark.asyncio
    async def test_complete_flow(self, agent_manager):
        """Test end-to-end flow."""
        # Setup
        service = await agent_manager.register_service(...)

        # Execute
        await agent_manager.start_service(service.service_id)

        # Verify
        assert service.status == ServiceStatus.RUNNING

        # Cleanup
        await agent_manager.stop_service(service.service_id)
```

## Coverage Goals

- **Unit tests**: > 80% code coverage
- **Integration tests**: Cover all major workflows
- **P0 tests**: 100% passing (required)
- **P1 tests**: 100% passing (important)
- **P2 tests**: Best effort (nice to have)

## TODO

### High Priority
- [ ] Complete API server tests with TestClient
- [ ] Add WebSocket proxy server tests
- [ ] Implement storage/repository tests
- [ ] Add data persistence tests

### Medium Priority
- [ ] Complete integration tests
- [ ] Add stress/performance tests
- [ ] Implement fault tolerance tests
- [ ] Add security/auth tests

### Low Priority
- [ ] Add property-based tests (hypothesis)
- [ ] Performance benchmarking
- [ ] Memory leak detection
- [ ] Docker-based integration tests

## Continuous Integration

Tests should be run in CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest tests/ --cov=myagent --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Debugging Tests

### Run with verbose output
```bash
pytest -vv tests/
```

### Run with print statements
```bash
pytest -s tests/
```

### Run specific test
```bash
pytest tests/manager/unit/test_service_registry.py::TestServiceRegistry::test_register_service_success
```

### Debug with pdb
```python
import pytest

def test_something():
    pytest.set_trace()  # Breakpoint
    # ...
```

## References

- [Test Plan](../../MANAGER_TEST_PLAN.md) - Complete test plan with all test cases
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
