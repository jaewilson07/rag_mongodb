# Server Maintenance - Agent Guide

## Scope
Maintenance scripts intended for server/runtime operations and admin tasks.

## Touch Points
- server/maintenance/init_indexes.py

## Conventions
- Keep scripts idempotent.
- Use structured logging from `mdrag.logging.service_logging`.
- Avoid destructive operations unless explicitly documented.

## Run Examples
- uv run python server/maintenance/init_indexes.py
