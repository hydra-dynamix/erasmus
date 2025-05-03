# Style Protocol

## Metadata
- **ID**: 00000005
- **Role**: code_style_verification
- **Triggers**: code_implementation, code_changes
- **Produces**: style_reports, linting_fixes
- **Consumes**: implementation_code, .ctx.progress.md, .ctx.tasks.md

## Objective
Ensure the codebase adheres to consistent coding standards and best practices using ruff and mypy. Track style issues and linting fixes in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code changes requiring style verification.
2. For each code change:
   - Run ruff and mypy to check for linting errors and style violations
   - Document any issues found in `.ctx.tasks.md` with clear descriptions and suggested fixes
   - Update `.ctx.progress.md` to reflect the status of style verification
3. For recurring style issues, update `.ctx.progress.md` with patterns and recommendations for future prevention.

## Principles
1. Maintain consistent code style and formatting across the codebase
2. Track all style issues and fixes in .ctx.tasks.md
3. Update .ctx.progress.md with style verification status and recommendations
4. Communicate style gaps or failures in .ctx.tasks.md for developer follow-up

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All style issues, linting fixes, and recommendations are tracked in these files. Progress is updated as style verification proceeds.
