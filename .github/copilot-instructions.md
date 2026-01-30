# GitHub Copilot Instructions

> Note: This is a summarized version. See [AGENTS.md](../AGENTS.md) as source of truth.

## Workflow
- Use feature branches for new work; avoid committing directly to main.
- Open a PR for any new feature or multi-file change.

## Safety
- Never run destructive commands without explicit confirmation.
- Do not attempt to create Atlas Vector/Search indexes programmatically.
- Never log or commit secrets (.env contents).

## Style
- Keep edits small and targeted; avoid unrelated refactors.
- Prefer existing patterns in src/ before introducing new ones.
