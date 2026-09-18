# Project Agent Instructions

## Change Specification Records

Every change made by an agent must be recorded in the project's `specs/` directory structure. Use the existing subdirectory and file organization used by the project; do not create or maintain one root-level spec file for all changes.

Before editing project files:

1. Identify the appropriate spec file under `specs/`, creating the required directory or file when needed.
2. Add a concise entry describing the requested change, intended behavior, affected files, and implementation approach.

After editing project files:

1. Update the corresponding spec entry with the files actually changed.
2. Record validation performed, including tests, builds, linting, or any remaining limitations.
3. Keep the specification accurate as the implementation evolves.

Changes related to GitHub workflows, configuration, metadata, or repository setup, including files under `.github/`, as well as changes to `.github/copilot-instructions.md` and files under `specs/`, are exempt from this recording requirement.

## Spec File Conventions

- Use one Markdown file for each logical change; do not combine unrelated changes in one spec.
- Place the file in the appropriate existing `specs/` subdirectory. If no suitable subdirectory exists, create one that reflects the project area.
- Name files in lowercase kebab-case, using a short descriptive change name, for example `specs/api/add-rate-limit.md`.
- Preserve any more specific naming or directory conventions already established in `specs/`.
- Use plain Markdown. YAML frontmatter is optional and should only be used when the surrounding project conventions require it.
- Keep the spec concise, specific, and updated as implementation decisions change.

Each spec should contain these sections:

```markdown
# Change Title

## Summary
What is changing and why.

## Requirements
The expected behavior, constraints, and acceptance criteria.

## Scope
The affected components, files, APIs, or user workflows.

## Implementation
The chosen approach and important design decisions.

## Validation
Tests, builds, linting, manual checks, or other verification performed.

## Status
Current state, remaining work, and known limitations.
```

Record facts rather than intentions after implementation: update affected files, validation results, status, and limitations to match the actual change.
