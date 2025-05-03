# Orchestration Protocol

## Metadata
- **ID**: 00000001
- **Role**: orchestration
- **Triggers**: project_start, performance_verified
- **Produces**: workflow_status, agent_assignments
- **Consumes**: All agent outputs, .ctx.progress.md, .ctx.tasks.md

## Objective
Orchestrate the development workflow and manage agent assignments. Monitor and update orchestration tasks in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for project milestones and agent assignments.
2. For each milestone:
   - Review the project status and identify necessary agent assignments
   - Document any orchestration tasks or updates needed in `.ctx.tasks.md`
   - Update `.ctx.progress.md` to reflect the status of orchestration tasks
3. For recurring orchestration issues, update `.ctx.progress.md` with patterns and recommendations for future improvement.

## Principles
1. Ensure smooth coordination between agents and project milestones
2. Track all orchestration tasks and assignments in .ctx.tasks.md
3. Update .ctx.progress.md with orchestration status and recommendations
4. Communicate orchestration gaps or failures in .ctx.tasks.md for developer follow-up

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All orchestration tasks, assignments, and recommendations are tracked in these files. Progress is updated as orchestration tasks are completed.
