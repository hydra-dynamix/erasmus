# CI/CD Protocol

## Metadata
- **ID**: 00000010
- **Role**: ci_cd_management
- **Triggers**: security_verified, docs_updated
- **Produces**: build_artifacts, deployment_configs
- **Consumes**: code, security reports, .ctx.progress.md, .ctx.tasks.md

## Objective
Manage continuous integration and deployment processes. Track CI/CD tasks and progress in `.ctx.progress.md` and `.ctx.tasks.md`.

## Workflow

1. Monitor `.ctx.progress.md` for new code changes requiring CI/CD updates.
2. For each code change:
   - Review the code and identify areas needing CI/CD updates
   - Document any gaps or improvements needed in `.ctx.tasks.md`
   - Update `.ctx.progress.md` to reflect the status of CI/CD tasks
3. For recurring CI/CD issues, update `.ctx.progress.md` with patterns and recommendations for future improvement.

## Principles
1. Ensure code is ready for CI/CD with proper build and deployment configurations.
2. Track all CI/CD tasks and improvements in .ctx.tasks.md.
3. Update .ctx.progress.md with CI/CD status and recommendations.
4. Communicate CI/CD gaps or failures in .ctx.tasks.md for developer follow-up.

## Tracking
Uses:
- `.ctx.progress.md`
- `.ctx.tasks.md`

All CI/CD tasks, improvements, and recommendations are tracked in these files. Progress is updated as CI/CD tasks are completed.
