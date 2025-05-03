# Code Review Protocol

## Metadata
- **ID**: 00000007
- **Role**: code_quality_assessment
- **Triggers**: tests_passing, style_verified
- **Produces**: review_comments, approval
- **Consumes**: implementation_code, test_files, style_reports, .ctx.progress.md, .ctx.tasks.md

## Objective
Provide feedback on pull requests, commits, or diffs to ensure code quality and consistency. Track review comments and approvals in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code changes requiring review.
2. For each code change:
   - Review the code for clarity, naming, duplication, and adherence to project structure
   - Document review comments in `.ctx.tasks.md` with clear descriptions and suggestions
   - Update `.ctx.progress.md` to reflect the status of the review
3. For recurring review issues, update `.ctx.progress.md` with patterns and recommendations for future prevention.

## Principles
1. Ensure code clarity, naming, and adherence to project structure.
2. Track all review comments and approvals in .ctx.tasks.md.
3. Update .ctx.progress.md with review status and recommendations.
4. Communicate review gaps or failures in .ctx.tasks.md for developer follow-up.

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All review comments, approvals, and recommendations are tracked in these files. Progress is updated as reviews proceed.
