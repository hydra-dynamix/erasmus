# Testing Protocol

## Metadata
- **ID**: 00000004
- **Role**: test_development
- **Triggers**: code_implementation, code_changes
- **Produces**: test_files, test_results
- **Consumes**: implementation_code, .ctx.tasks.md, .ctx.architecture.md, .ctx.progress.md

## Objective
Design, implement, and evaluate tests that guide and validate development. Use `.ctx.tasks.md` to track test requirements and coverage for each development task.

## Workflow

1. For every new task in `.ctx.tasks.md`:
   - Review `.ctx.architecture.md` and `.ctx.progress.md` for context and requirements
   - Write failing tests that define success for the task, documenting test intent in `.ctx.tasks.md`
   - Place test files in the appropriate structure and update `.ctx.tasks.md` with test status

2. During development:
   - Review updated code and re-run tests using `uv run pytest`
   - Update `.ctx.tasks.md` with test results and any issues found

3. After a task is marked complete:
   - Validate edge cases, error handling, and regressions
   - Suggest improvements in test coverage or code logic, recording suggestions in `.ctx.tasks.md`
   - Flag any missing assertions or untested paths in `.ctx.tasks.md`

## Principles
1. Write tests before implementing functionality (TDD)
2. Track all test requirements and results in .ctx.tasks.md
3. Ensure comprehensive coverage for each task and milestone
4. Communicate test gaps or failures in .ctx.tasks.md for developer follow-up
5. Use timeout mechanisms for tests that might hang or take too long to execute

## Best Practices

### Timeout Mechanism
Implement a timeout decorator for tests that might hang or take too long to execute.

```python
import signal
from functools import wraps

def timeout(seconds=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f"Test timed out after {seconds} seconds")
            
            # Set the timeout handler
            original_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Restore the original handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
        return wrapper
    return decorator

# Usage example:
@timeout(5)
def test_example():
    # Test code here
    pass
```

#### Usage
1. Import the timeout decorator in your test file
2. Apply the decorator to tests that might hang or take too long
3. Set an appropriate timeout value based on the expected execution time
4. Handle TimeoutError in your test framework if needed

#### Benefits
- Prevents tests from hanging indefinitely
- Provides clear error messages when tests time out
- Helps identify performance issues in tests
- Improves CI/CD pipeline reliability

## Tracking
Uses:
- `.ctx.tasks.md`
- `.ctx.progress.md`

All test requirements, coverage, and results are tracked in these files. Each task's test status is updated as work proceeds.
