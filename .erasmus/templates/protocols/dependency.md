# Dependency Protocol

## Metadata
- **ID**: 00000013
- **Role**: dependency_management
- **Triggers**: code_implementation, dependency_check
- **Produces**: dependency_reports, updates
- **Consumes**: code, requirements, .ctx.progress.md, .ctx.tasks.md

## Objective
Manage and update project dependencies. Monitor and update dependency tasks in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code implementations requiring dependency checks.
2. For each code change:
   - Review the code and identify any new dependencies or updates needed
   - Document any dependency issues or updates needed in `.ctx.tasks.md`
   - Update `.ctx.progress.md` to reflect the status of dependency tasks
3. For recurring dependency issues, update `.ctx.progress.md` with patterns and recommendations for future improvement.

## Principles
1. Ensure all dependencies are up-to-date and compatible
2. Track all dependency tasks and updates in .ctx.tasks.md
3. Update .ctx.progress.md with dependency status and recommendations
4. Communicate dependency gaps or failures in .ctx.tasks.md for developer follow-up

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All dependency tasks, updates, and recommendations are tracked in these files. Progress is updated as dependency tasks are completed.
