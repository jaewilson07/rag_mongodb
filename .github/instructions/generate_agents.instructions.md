# Generate AGENTS.md Hierarchical Documentation

**Purpose**: Automated generation of hierarchical AGENTS.md documentation that serves as behavioral guides for AI coding assistants across multiple editors (Cursor, GitHub Copilot, and others).

## Core Principles

### Multi-Editor Compatibility
- **Universal Standard**: AGENTS.md files work with Cursor, GitHub Copilot, and other AI tools
- **Nearest-Wins Hierarchy**: Sub-folder rules override parent rules (compositional rule system)
- **Single Source of Truth**: AGENTS.md is authoritative; editor configs reference it

### Document Design Philosophy
- **JIT Indexing**: Provide paths/globs instead of dumping full content into context
- **Token Efficiency**: High-density constraints over verbose prose (target: 150-250 lines for root)
- **Behavior over Syntax**: Define *how* agents think, not just *what* to write
- **Actionable Instructions**: Every rule should be verifiable and testable

### Project Organization Standards
- **Clean Root Directory**: Use designated folders (`.github/`, `.cursor/`, `docs/`, `sample/`, `scripts/`, `setup/`, `test/`, `temp/`)
- **Composition Architecture**: Inner classes for multi-concern services (`Service.Component`)
- **Protocol-First Design**: ABC base classes and Protocols for type safety

## Generation Process

### Phase 1: Repository Analysis

Analyze codebase structure and create a **Structured Map**:

**1. Repository Overview**
- Type: Monorepo, Polyrepo, or Hybrid
- Languages: Primary and secondary languages with versions
- Frameworks: Key frameworks with versions
- Build System: Package manager and build tools

**2. Architecture Domains**
Identify major components:
- Stack-based structure (e.g., `00-infrastructure/`, `01-data/`, `02-compute/`)
- Application layer (e.g., `apps/`, `services/`)
- Shared code (e.g., `packages/`, `libs/`)

**3. Testing Strategy**
- Testing frameworks: Jest, Pytest, Playwright, etc.
- Test locations: Unit tests, integration tests, E2E tests
- Test commands: How to run different test suites

**4. Agent Gotchas**
Document patterns that confuse AI:
- Legacy vs modern code sections
- Custom patterns (non-standard API wrappers, state managers)
- Deprecated patterns still in codebase
- Cross-stack dependencies
- Build quirks or timing issues

### Phase 2: Generate Root AGENTS.md

**Target Length**: 150-250 lines (quality over quantity)

**Required Sections:**

#### 1. Agent Behavioral Protocols
Define problem-solving approach:
```markdown
## Agent Behavioral Protocols

### Thinking Process
1. **Explore Context First**: Search for existing patterns before creating
2. **Verify DRY**: Check if similar functionality exists
3. **Plan Before Execute**: Outline approach for multi-file changes
4. **Drift Check**: If doc contradicts code, trust codebase and flag discrepancy

### Safety Constraints
- **Never run destructive commands** without explicit confirmation:
  - `rm -rf` (especially root/system directories)
  - `DROP TABLE` or database schema deletions
  - `docker system prune -a` or volume deletions
- **No blind retries**: If fix fails, stop, analyze logs, propose new strategy
- **Environment awareness**: Distinguish dev/staging/prod environments
```

#### 2. Token Economy & Output
```markdown
## Token Economy & Output
- Use `sed` or patch-style replacements for small edits
- Output changed code only (use `// ... existing code ...` for context)
- Do not repeat user's prompt verbatim
- Reference files by path when possible: `startLine:endLine:filepath`
```

#### 3. Universal Tech Stack
```markdown
## Universal Tech Stack

### Repository Type
- [Monorepo/Polyrepo] with [describe organization]
- Orchestration: [describe if applicable]

### Core Commands
```bash
# Build
[build command]

# Test
[test command]

# Lint
[lint command]
```

### Code Style Standards
- **Language 1**: [Standards, formatters, linters]
- **Language 2**: [Standards, formatters, linters]
```

#### 4. Architecture Overview
```markdown
## Architecture Overview

### Component Organization
[Describe major stacks/layers]

### Service Composition Pattern
- Use inner classes for multi-concern services: `Service.Component`
- Base classes with ABC and Protocol for type safety
- Parent reference via `self._parent` in components

### Network/Communication
[How services communicate]
```

#### 5. File Organization Standards
```markdown
## File Organization & Root Directory Standards

**Do not create new root-level files or directories.** Use designated locations:

- **`.github/`** - GitHub-specific configs
- **`.cursor/`** - Cursor-specific configs  
- **`.venv/`** - Python virtual environment (always use `uv`)
- **`docs/`** - Project documentation
- **`sample/`** - User-facing sample code
- **`scripts/`** - Maintenance scripts (agents: do not modify)
- **`setup/`** - Installation scripts
- **`test/`** - Test files
- **`temp/`** - Temporary files (gitignored)
- [List project-specific directories]
```

#### 6. Common Patterns
Document key patterns with examples:
```markdown
## Common Patterns

### Pattern Name
**When**: [When to use]
**Example**: [File path and brief example]
**Anti-pattern**: [What to avoid]
```

#### 7. JIT Index (Component Map)
```markdown
## JIT Index (Component Map)

For detailed component rules, see:

### Stack-Level Documentation
- **[Stack Name AGENTS.md]** - [Brief description]
- **[Stack Name AGENTS.md]** - [Brief description]

### Component-Level Documentation
- **[Component AGENTS.md]** - [Brief description]
- **[Component AGENTS.md]** - [Brief description]
```

#### 8. Search Hints
```markdown
## Search Hints

```bash
# Find pattern X
rg -n "pattern" --type [language]

# Find service definitions
rg -n "class.*Service" --type python

# Find API endpoints
rg -n "@router\.(get|post)" --type python
```
```

#### 9. Error Handling Protocol
```markdown
## Error Handling Protocol

1. **Container failures**: `docker logs <container>`
2. **Network issues**: `docker network inspect [network]`
3. **Dependency errors**: [Specific commands]
4. [Project-specific error handling]
```

### Phase 3: Generate Sub-Folder AGENTS.md Files

For each major component, create component-specific documentation:

**Required Sections:**

#### 1. Component Identity
```markdown
# [Component Name] - [Brief Description]

## Technical Stack
- **Framework**: [Name] [Version]
- **Language**: [Language] [Version]
- **Key Dependencies**:
  - [Dependency]: [Version] - [Purpose]
  - [Dependency]: [Version] - [Purpose]
```

#### 2. Architecture & Patterns
```markdown
## Architecture & Patterns

### File Organization
- `[path]/` - [Purpose]
- `[path]/` - [Purpose]

### Code Examples

✅ **DO**: Use this pattern
```[language]
[Real example from codebase with file path]
```

❌ **DON'T**: Avoid this anti-pattern
```[language]
[What not to do]
```

### Domain Dictionary
- **Term 1**: [Definition in this context]
- **Term 2**: [Definition in this context]
```

#### 3. Service Composition (if applicable)
```markdown
## Service Composition

### When to Apply
- Multi-concern services
- Shared parent functionality
- Single entry point needed

### Pattern
```python
class Service:
    class Component:
        def __init__(self, parent: "Service"):
            self._parent = parent

        def method(self):
            # Access parent via self._parent
            pass
```

### Examples in Codebase
- `[file path]` - [Description]
```

#### 4. Key Files & Search Hints
```markdown
## Key Files & JIT Search

### Touch Points
- **[Feature]**: `[file path]`
- **[Feature]**: `[file path]`

### Search Commands
```bash
# Find [X]
rg -n 'pattern' [path]

# Find [Y]
grep -r 'pattern' [path]
```
```

#### 5. Testing & Validation
```markdown
## Testing & Validation

### Test Command
```bash
[Specific test command for this component]
```

### Test Strategy
- **Unit**: [What to unit test]
- **Integration**: [What to integration test]
- **E2E**: [What to E2E test]

### Test Locations
- Unit: `[path]`
- Integration: `[path]`
```

#### 6. Component-Specific Gotchas
```markdown
## Component Gotchas

### Common Mistakes
1. **[Mistake]**: [Description and solution]
2. **[Mistake]**: [Description and solution]

### Legacy Patterns
- **[Pattern]**: Deprecated, use [New Pattern] instead
```

## Output Format

Provide results in structured order:

### 1. Analysis Summary
```markdown
# Repository Analysis Summary

## Repository Type
[Monorepo/Polyrepo/Hybrid]

## Tech Stack
- Languages: [List with versions]
- Frameworks: [List with versions]
- Build Tools: [List]

## Architecture
- [Major component 1]: [Description]
- [Major component 2]: [Description]

## Testing
- Frameworks: [List]
- Strategy: [Description]

## Gotchas
1. [Issue 1]: [Description]
2. [Issue 2]: [Description]
```

### 2. Root AGENTS.md
```markdown
---
File: `AGENTS.md` (root)
---

[Complete content following Phase 2 template]
```

### 3. Component AGENTS.md Files
```markdown
---
File: `[component-path]/AGENTS.md`
---

[Complete content following Phase 3 template]

---
File: `[another-component-path]/AGENTS.md`
---

[Complete content following Phase 3 template]
```

## Quality Checklist

Before finalizing AGENTS.md files:

- [ ] **Root < 250 lines**: Constitution is concise
- [ ] **Component < 200 lines**: Sub-files are focused
- [ ] **All paths verified**: File references exist
- [ ] **Commands tested**: All bash commands work
- [ ] **No secrets**: No credentials or API keys
- [ ] **Version-specific**: Framework/language versions stated
- [ ] **JIT index complete**: All components referenced
- [ ] **Search hints work**: Grep/rg commands return results
- [ ] **Examples from codebase**: Real file paths, not generic
- [ ] **Gotchas documented**: Known issues captured

## Best Practices

### Do's
- ✅ Use specific versions ("Python 3.10+", "React 19")
- ✅ Provide file paths for all examples
- ✅ Document "why" for non-obvious rules
- ✅ Keep root AGENTS.md as high-level guide
- ✅ Push details into component AGENTS.md
- ✅ Use bullet points for readability
- ✅ Test all commands before documenting

### Don'ts
- ❌ Don't duplicate content across files
- ❌ Don't include full code snippets (use references)
- ❌ Don't document obvious patterns
- ❌ Don't leave outdated information
- ❌ Don't exceed line limits (250 root, 200 component)
- ❌ Don't use vague language ("usually", "sometimes")
- ❌ Don't forget to update after major changes

## Supporting Files

### Multi-Editor Integration

**For GitHub Copilot** (`.github/copilot-instructions.md`):
```markdown
# GitHub Copilot Instructions

> **Note**: This is a summarized version. See [AGENTS.md](../../AGENTS.md) as source of truth.

[Brief summary of key rules]
```

**For Cursor** (`.cursor/rules/project-rules.md`):
```markdown
# Cursor Project Rules

> **Note**: These supplement [AGENTS.md](../../AGENTS.md). On conflict, AGENTS.md wins.

[Cursor-specific shortcuts or overrides]
```

## Maintenance Strategy

### When to Regenerate
1. **Major refactoring** - Architecture changes
2. **New stack added** - New services or layers
3. **Quarterly review** - Check for drift
4. **Pattern changes** - New conventions adopted

### Update Process
1. Run analysis phase
2. Compare with existing AGENTS.md
3. Update changed sections
4. Test commands
5. Commit with clear message

### Version Control
- Commit AGENTS.md files with code
- Tag with "docs:" prefix in commits
- Review in pull requests
- Track changes over time

## Related Skills

Related skills documentation is maintained outside this repository.

## References

- [AGENTS.md Open Standard](https://github.com/openai/agents.md)
- [GitHub Copilot Custom Instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- [Awesome Cursor Rules](https://github.com/PatrickJS/awesome-cursorrules)

---

**Last Updated**: January 22, 2026
**Maintainer**: Development Team
**Version**: 2.0.0
