# Pre-commit Hooks

This project uses pre-commit hooks for automated linting, formatting, and security scanning before commits.

## Setup

Pre-commit hooks are automatically installed when you run `uv sync --group development`. To manually install:

```bash
# Install dependencies
uv sync --group development

# Install pre-commit hooks
uv run pre-commit install
```

## Hooks Configured

### General File Checks
- **trailing-whitespace**: Remove trailing whitespace (excludes .md, .txt)
- **end-of-file-fixer**: Ensure files end with a newline
- **check-yaml**: Validate YAML syntax
- **check-json**: Validate JSON syntax
- **check-toml**: Validate TOML syntax
- **check-added-large-files**: Prevent commits of files >1MB
- **check-merge-conflict**: Detect merge conflict markers
- **check-case-conflict**: Detect case-insensitive filename conflicts
- **detect-private-key**: Prevent committing private keys
- **mixed-line-ending**: Normalize line endings to LF

### Python Tools
- **black**: Code formatter (line length: 100)
- **ruff**: Fast Python linter with auto-fix
- **ruff-format**: Additional formatting via ruff
- **bandit**: Security vulnerability scanner (excludes tests/, examples/, sample/)

### Security
- **detect-secrets**: Scan for accidentally committed secrets
- **bandit**: Static security analysis for Python code

### Other
- **hadolint**: Dockerfile linting
- **yamllint**: YAML file linting

## Running Hooks

### Automatic (on commit)
Pre-commit hooks run automatically when you commit:

```bash
git add .
git commit -m "Your message"
# Hooks run automatically and may modify files
# If files are modified, stage them and commit again
```

### Manual Execution

Run on all files:
```bash
uv run pre-commit run --all-files
```

Run on specific files:
```bash
uv run pre-commit run --files src/myfile.py tests/test_myfile.py
```

Run specific hook:
```bash
uv run pre-commit run black --all-files
uv run pre-commit run ruff --all-files
uv run pre-commit run bandit --all-files
```

## Bypassing Hooks (Not Recommended)

In rare cases where you need to bypass hooks:

```bash
git commit --no-verify -m "Your message"
```

**Warning**: Only bypass hooks if absolutely necessary and you understand the implications.

## Configuration Files

- **`.pre-commit-config.yaml`**: Pre-commit hook configuration
- **`.secrets.baseline`**: Baseline for detect-secrets (known false positives)
- **`pyproject.toml`**: Contains tool configurations for:
  - `[tool.ruff]`: Ruff linter settings
  - `[tool.black]`: Black formatter settings
  - `[tool.bandit]`: Bandit security scanner settings

## Updating Hooks

Update to the latest versions:

```bash
uv run pre-commit autoupdate
```

## Troubleshooting

### Hooks fail on first run
Run hooks manually to see detailed output:
```bash
uv run pre-commit run --all-files
```

### Clear hook cache
```bash
rm -rf ~/.cache/pre-commit/
uv run pre-commit install --install-hooks
```

### Secrets detected
If detect-secrets flags a false positive:
1. Run: `uv run detect-secrets scan --update .secrets.baseline`
2. Review changes in `.secrets.baseline`
3. Commit the updated baseline

### Ruff auto-fixes break code
Review the changes made by ruff:
```bash
git diff
```
If incorrect, adjust the ruff configuration in `pyproject.toml` under `[tool.ruff.lint]`.

## Security Best Practices

1. **Never bypass security hooks** (bandit, detect-secrets) without review
2. **Review all hook changes** before committing
3. **Keep hooks updated** regularly with `pre-commit autoupdate`
4. **Add sensitive files to `.gitignore`** (never rely solely on hooks)

## CI/CD Integration

Pre-commit can run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run pre-commit
  run: |
    uv sync --group development
    uv run pre-commit run --all-files
```

This ensures all code meets standards before merging.
