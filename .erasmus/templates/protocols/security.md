# Security Protocol

## Metadata
- **ID**: 00000008
- **Role**: security_verification
- **Triggers**: code_review_passed
- **Produces**: security_reports, vulnerability_fixes
- **Consumes**: implementation_code, .ctx.progress.md, .ctx.tasks.md

## Objective
Identify and mitigate security vulnerabilities in the codebase. Track security issues and fixes in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code changes requiring security verification.
2. For each code change:
   - Run security scans to identify vulnerabilities
   - Document any issues found in `.ctx.tasks.md` with clear descriptions and suggested fixes
   - Update `.ctx.progress.md` to reflect the status of security verification
3. For recurring security issues, update `.ctx.progress.md` with patterns and recommendations for future prevention.

## Principles
1. Ensure code is free from security vulnerabilities
2. Track all security issues and fixes in .ctx.tasks.md
3. Update .ctx.progress.md with security verification status and recommendations
4. Communicate security gaps or failures in .ctx.tasks.md for developer follow-up

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All security issues, vulnerability fixes, and recommendations are tracked in these files. Progress is updated as security verification proceeds.
