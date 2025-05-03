# Agent Workflow Protocol

## Description
Defines the workflow and dependencies between different agent roles in the development process.

## Triggers
- New Project
- Architecture Complete
- Code Ready
- Verification Complete
- Review Passed
- Documentation & Security Verified
- Deployment Ready
- Performance Verified
- Test Failures
- Linting Issues
- Review Issues
- Security Vulnerabilities
- Performance Problems

## Produces
- Workflow Status
- Agent Assignments
- Development Artifacts

## Consumes
- Project Requirements
- Code Changes
- Test Results
- Review Comments

## Workflow

### 1. Project Initiation
Orchestrator initiates the project and hands off to Product Owner
- Orchestrator evaluates project requirements
- Orchestrator assigns Product Owner Agent

### 2. Architecture & Planning
Product Owner creates architecture and sprint plan
- Product Owner creates .architecture.md
- Product Owner creates .progress.md
- Product Owner hands off to Developer Agent

### 3. Code Implementation
Developer implements code and breaks down tasks
- Developer creates .tasks.md
- Developer implements code
- Developer hands off to Testing and Style Agents

### 4. Code Verification
Testing and Style Agents verify code quality
- Testing Agent creates and runs tests using `uv run pytest`
- Style Agent checks code style
- If issues found, hand off to Debug Agent or Developer
- If verified, hand off to Code Review Agent

### 5. Code Review
Code Review Agent assesses code quality
- Code Review Agent reviews code
- If issues found, hand off to Developer
- If approved, hand off to Documentation and Security Agents

### 6. Documentation & Security
Documentation and Security Agents complete their checks
- Documentation Agent updates documentation
- Security Agent scans for vulnerabilities
- If issues found, hand off to Developer
- If verified, hand off to CI/CD Agent

### 7. CI/CD
CI/CD Agent handles build and deployment
- CI/CD Agent builds the application
- CI/CD Agent prepares deployment
- CI/CD Agent hands off to Performance Agent

### 8. Performance Testing
Performance Agent tests and optimizes
- Performance Agent runs performance tests
- If issues found, hand off to Developer
- If verified, hand off to Orchestrator

## Agents

### Orchestrator Agent
- **Description**: Initiates project workflows and coordinates agents
- **Receives From**: Performance Agent (final verification)
- **Hands Off To**: Product Owner Agent (project initiation)

### Product Owner Agent
- **Description**: Handles project planning and requirements definition
- **Receives From**: Orchestrator Agent (project initiation)
- **Hands Off To**: Developer Agent (architecture and sprint plan)
- **Produces**: .architecture.md, .progress.md

### Developer Agent
- **Description**: Implements code and breaks down tasks
- **Receives From**: Product Owner Agent (architecture and sprint plan)
- **Hands Off To**: Testing Agent, Style Agent (code ready for verification)
- **Produces**: .tasks.md, implementation code

### Testing Agent
- **Description**: Creates and executes tests
- **Receives From**: Developer Agent (code to test)
- **Hands Off To**: Code Review Agent (tests passing) or Debug Agent (test failures)
- **Produces**: Test files, test results

### Style Agent
- **Description**: Verifies code style and quality
- **Receives From**: Developer Agent (code to analyze)
- **Hands Off To**: Code Review Agent (style verified) or Developer Agent (linting issues)
- **Produces**: Style reports, linting fixes

### Code Review Agent
- **Description**: Assesses code quality
- **Receives From**: Testing Agent, Style Agent (verified code)
- **Hands Off To**: Documentation Agent, Security Agent (review passed) or Developer Agent (review issues)
- **Produces**: Review comments, approval

### Security Agent
- **Description**: Scans for security vulnerabilities
- **Receives From**: Code Review Agent (code to scan)
- **Hands Off To**: CI/CD Agent (security verified) or Developer Agent (security issues)
- **Produces**: Security reports, vulnerability fixes

### Documentation Agent
- **Description**: Updates documentation
- **Receives From**: Code Review Agent (code to document)
- **Hands Off To**: CI/CD Agent (docs updated)
- **Produces**: README, API docs, inline comments

### CI/CD Agent
- **Description**: Handles build and deployment processes
- **Receives From**: Security Agent, Documentation Agent (verified code and docs)
- **Hands Off To**: Performance Agent (deployment ready)
- **Produces**: Build artifacts, deployment configurations

### Performance Agent
- **Description**: Tests and optimizes performance
- **Receives From**: CI/CD Agent (deployed code)
- **Hands Off To**: Orchestrator Agent (performance verified) or Developer Agent (performance issues)
- **Produces**: Performance reports, optimization recommendations

### Debug Agent
- **Description**: Diagnoses and resolves issues
- **Receives From**: Testing Agent (test failures)
- **Hands Off To**: Developer Agent (issues identified)
- **Produces**: Debug reports, fix recommendations

## Error Handling

### Test Failures
Flow: Testing → Debug → Developer

### Linting Issues
Flow: Style Agent → Developer

### Review Issues
Flow: Code Review → Developer

### Security Vulnerabilities
Flow: Security → Developer

## Principles

### Continuous Flow
Maintain a continuous flow of work through the agent pipeline
