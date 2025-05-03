# Performance Protocol

## Metadata
- **ID**: 00000011
- **Role**: performance_optimization
- **Triggers**: deployment_ready
- **Produces**: performance_reports, optimization_recommendations
- **Consumes**: build_artifacts, .ctx.progress.md, .ctx.tasks.md

## Objective
Optimize code performance and track performance improvements. Monitor and update performance tasks in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code changes requiring performance optimization.
2. For each code change:
   - Review the code and identify areas needing performance improvements
   - Document any performance issues or improvements needed in `.ctx.tasks.md`
   - Update `.ctx.progress.md` to reflect the status of performance tasks
3. For recurring performance issues, update `.ctx.progress.md` with patterns and recommendations for future improvement.

## Principles
1. Ensure code is optimized for performance with proper profiling and benchmarking
2. Track all performance tasks and improvements in .ctx.tasks.md
3. Update .ctx.progress.md with performance status and recommendations
4. Communicate performance gaps or failures in .ctx.tasks.md for developer follow-up

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All performance tasks, improvements, and recommendations are tracked in these files. Progress is updated as performance tasks are completed.
