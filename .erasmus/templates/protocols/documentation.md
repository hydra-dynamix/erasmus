# Documentation Protocol

## Metadata
- **ID**: 00000009
- **Role**: documentation_management
- **Triggers**: code_review_passed
- **Produces**: readme, api_docs, inline_comments
- **Consumes**: code, architecture, test files, .ctx.progress.md, .ctx.tasks.md

## Objective
Create and maintain comprehensive documentation for the codebase. Track documentation tasks and progress in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code changes requiring documentation.
2. For each code change:
   - Review the code and identify areas needing documentation
   - Document any gaps or improvements needed in `.ctx.tasks.md`
   - Update `.ctx.progress.md` to reflect the status of documentation tasks
3. For recurring documentation issues, update `.ctx.progress.md` with patterns and recommendations for future improvement.

## Principles
1. Ensure code is well-documented with clear and concise comments
2. Track all documentation tasks and improvements in .ctx.tasks.md
3. Update .ctx.progress.md with documentation status and recommendations
4. Communicate documentation gaps or failures in .ctx.tasks.md for developer follow-up

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All documentation tasks, improvements, and recommendations are tracked in these files. Progress is updated as documentation tasks are completed.
