# Pre-commit Quick Start

## First Time Setup
```bash
# Already done during uv sync --group development
uv run pre-commit install
```

## Daily Usage

### Before Committing
```bash
# Check what will be scanned
git status

# Optional: Run manually to preview changes
uv run pre-commit run --files $(git diff --cached --name-only)

# Commit normally - hooks run automatically
git add .
git commit -m "Your message"

# If hooks make changes, review and commit again
git diff
git add .
git commit -m "Your message"
```

### Manual Runs
```bash
# Run on all files
uv run pre-commit run --all-files

# Run on specific files
uv run pre-commit run --files src/myfile.py

# Run specific hook
uv run pre-commit run black
uv run pre-commit run ruff --all-files
```

## What Gets Checked

✅ **Auto-fixed**:
- Trailing whitespace
- File endings
- Import sorting (ruff)
- Code formatting (black, ruff-format)
- Line endings

⚠️ **Must fix manually**:
- Syntax errors
- Type errors
- Security issues (bandit)
- Complex linting issues (ruff)

## Common Issues

### "Detect secrets" fails
False positive? Update baseline:
```bash
uv run detect-secrets scan --update .secrets.baseline
git add .secrets.baseline
```

### Ruff/Black conflicts
Both tools coordinate via pyproject.toml. If issues persist:
```bash
uv run black src/
uv run ruff check --fix src/
```

### Large file warning
File >1MB? Check if it should be in git:
- If yes: Use Git LFS
- If no: Add to .gitignore

## Emergency Bypass
```bash
# ⚠️ Only if absolutely necessary
git commit --no-verify -m "Emergency fix"
```

## More Info
See: `docs/pre-commit-hooks.md`
