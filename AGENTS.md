# MergeLens agent instructions

These instructions apply to the whole repository.

## Allowed work

- Make scoped code changes, tests, and documentation that are required by the active task.
- Run local verification with the checked-in development dependencies.
- Inspect public project files and committed, privacy-minimized snapshot data.

## Required conduct

- Preserve unrelated work and inspect the diff before staging.
- Keep tests deterministic. No network calls in tests.
- Treat model-metric changes as reviewable product changes: no silent model-metric changes.
- Use the public project interfaces when reporting metrics, and require evidence before completion.
- State whether evidence is local or from CI; do not imply that an unrun environment passed.

## Prohibited conduct

- No secret access beyond a credential explicitly supplied for an in-scope operation, and no
  secret output in logs, files, tests, documentation, or messages.
- No unsupported production claims, including availability, deployment, performance, or quality
  claims without current evidence.
- Never add author or developer scoring, rankings, or identity-level performance inference.
- No destructive Git commands such as `git reset --hard`, history rewriting, or deletion of
  unrelated work.
- No deployment without an explicit in-scope request.
- Do not refresh or replace the committed snapshot unless the active task explicitly requires it.
