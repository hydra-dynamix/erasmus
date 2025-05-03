# Debugging Protocol

## Metadata
- **ID**: 00000003
- **Role**: issue_diagnosis
- **Triggers**: test_failures
- **Produces**: debug_reports, fix_recommendations
- **Consumes**: implementation_code, test_results, .ctx.progress.md, .ctx.tasks.md

## Objective
Identify, diagnose, and resolve issues in the codebase, focusing on runtime errors, logical bugs, and performance bottlenecks. Document all errors and attempted solutions in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new or ongoing errors and bugs.
2. For each error or bug:
   - Reproduce the issue and document reproduction steps in `.ctx.tasks.md`
   - Isolate the problem and record diagnostic steps in `.ctx.tasks.md`
   - Formulate hypotheses and test potential fixes, tracking each attempt in `.ctx.tasks.md`
   - When a fix is found, update `.ctx.progress.md` to mark the error as resolved and summarize the solution
   - Document lessons learned and any new tests or regression checks added
3. For recurring or systemic issues, update `.ctx.progress.md` with patterns and recommendations for future prevention.

## Principles
1. Trace issues to their root cause, not just symptoms
2. Document all diagnostic steps and attempted solutions in .ctx.tasks.md
3. Update .ctx.progress.md with error status and resolution notes
4. Ensure fixes do not introduce regressions; add or update tests as needed
5. Communicate blockers or unresolved issues in .ctx.progress.md for team visibility

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All errors, diagnostic steps, and attempted solutions are tracked in these files. Progress is updated as issues are resolved or require escalation.
