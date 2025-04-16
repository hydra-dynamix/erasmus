Integration Plan: CLI for Humans, MCP for Agents
1. CLI for Human Operations
Continue to use the existing Erasmus CLI for all human-initiated actions (add/update tasks, manage context, etc.).
CLI commands will trigger the sync logic to update GitHub Projects as the source of truth.
2. MCP (Machine Control Protocol) for Agent Operations
Implement an MCP server/module that exposes the same operations as the CLI, but via an API (HTTP, gRPC, or even a simple socket protocol).
Agents (models, automations, other services) interact with Erasmus exclusively through the MCP interface.
The MCP server will call the same internal logic as the CLI, ensuring all actions (human or agent) are mirrored and consistent.
3. Unified Sync Logic
Both the CLI and MCP routes call a shared backend/service layer that handles:
Local context file updates (if needed)
GitHub Projects sync (source of truth)
Summary/context injection for the model
4. Benefits
Separation of concerns: Humans use CLI, agents use MCP.
Consistency: All operations, regardless of origin, are reflected in GitHub Projects.
Extensibility: You can add more agent types or automation without changing the human workflow.
Implementation Steps
Refactor Erasmus core logic so that both CLI and MCP routes call the same functions for task/context management.
Implement the MCP server (could be Flask/FastAPI for HTTP, or a lightweight socket server).
Add authentication/authorization to MCP if needed (to prevent rogue agents).
Document the MCP API so agents know how to interact with it.
Test: Ensure that actions via CLI and MCP both update GitHub Projects and local context as expected.