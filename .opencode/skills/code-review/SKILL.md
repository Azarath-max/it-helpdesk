---
name: Code Review
description: Perform senior-level code reviews of diffs, pull requests, and changed files. Detect bugs, security vulnerabilities, regressions, architectural violations, and maintainability issues before committing or opening a PR.
---

# Code Review

Use this skill whenever the user requests a code review, diff review, pull request review, implementation audit, or review of recently modified files.

Act as a senior software engineer conducting a thorough, evidence-based review.

Your priority is correctness, security, reliability, and maintainability. Do not approve code simply because it compiles or passes tests.

## 1. Establish Review Scope

1. Run `git status --short`.
2. Inspect `git diff` and `git diff --staged`.
3. Identify untracked files that are relevant to the change.
4. Determine the purpose of the changes from the conversation, commit messages, and project documentation.
5. Review only relevant changes and their surrounding code.
6. Never assume unrelated existing code is part of the current change.

If there are no changes, ask what the user wants reviewed.

Do not overwrite, discard, reset, or modify the user's existing work.

## 2. Read Review References

1. Read `references/review-checklist.md`.
2. Read relevant project instructions such as `AGENTS.md`.
3. Inspect relevant documentation, architecture decisions, and existing patterns.
4. Identify applicable security and engineering requirements.

Follow existing project conventions unless they introduce a demonstrable problem.

## 3. Understand Before Reviewing

Before identifying issues:

1. Understand the feature's intended behavior.
2. Trace the affected execution flow.
3. Inspect callers, dependencies, database interactions, and consumers.
4. Check how errors propagate.
5. Check whether the change affects existing features.
6. Verify assumptions against actual implementation.

Do not judge isolated code without understanding its context.

## 4. Review Categories

Evaluate applicable categories in this order.

### A. Correctness and Logic
- Incorrect conditions or calculations.
- Missing edge cases.
- Incorrect state transitions.
- Null, undefined, and empty-value handling.
- Race conditions and concurrency problems.
- Incorrect asynchronous behavior.
- Unexpected side effects.
- Incorrect assumptions about external services.

### B. Security
- Broken authentication or authorization.
- Missing ownership checks.
- SQL injection and unsafe queries.
- Cross-site scripting.
- Command injection.
- Exposed secrets, tokens, and credentials.
- Insecure environment configuration.
- Improper input validation.
- Sensitive information in logs or API responses.
- SSRF and unsafe URL handling.
- Missing rate limiting where appropriate.

Never recommend exposing secrets or bypassing security controls to simplify implementation.

### C. API Design and Backend
- Incorrect HTTP methods and status codes.
- Inconsistent response formats.
- Missing request validation.
- Incorrect middleware ordering.
- Unhandled exceptions.
- Missing pagination or resource limits.
- Broken REST conventions.
- Improper dependency management.
- Duplicate or conflicting business logic.

### D. Database and Data Integrity
- Incorrect Prisma relations.
- Missing foreign keys or constraints.
- Missing unique constraints.
- Incorrect transaction boundaries.
- Data consistency issues.
- N+1 queries.
- Missing indexes on important query paths.
- Unsafe migrations.
- Unexpected cascading deletes.
- Incorrect handling of nullable fields.
- Duplicate records and race conditions.

### E. Performance and Resource Management
- Unnecessary database queries.
- Memory leaks.
- Unbounded loops or data retrieval.
- Expensive synchronous operations.
- Missing timeouts.
- Unnecessary API calls.
- Inefficient polling.
- Improper connection handling.
- Resource cleanup problems.

### F. Reliability and Error Handling
- Missing error handling.
- Swallowed exceptions.
- Incorrect retry behavior.
- Missing timeout handling.
- Duplicate job execution.
- Failure recovery problems.
- Improper transaction rollback.
- Incorrect logging.
- Missing graceful shutdown behavior.

### G. Testing
- Missing tests for new functionality.
- Tests that do not verify actual behavior.
- Missing negative test cases.
- Missing boundary-condition tests.
- Incorrect mocks.
- Flaky tests.
- Missing regression coverage.
- Tests that pass despite broken business logic.

### H. Architecture and Maintainability
- Violations of established project architecture.
- Tight coupling.
- Unnecessary abstractions.
- Duplicate implementations.
- Oversized functions or modules.
- Poor separation of concerns.
- Inconsistent naming.
- Unnecessary dependencies.
- Dead code.
- Inconsistent coding conventions.


## 5. Verify Every Finding

Before reporting a finding:

1. Locate the exact affected code.
2. Trace the relevant execution path.
3. Confirm the issue is reproducible or logically demonstrable.
4. Determine whether existing validation already prevents it.
5. Check whether the behavior is intentional.
6. Identify the actual impact.

Do not report speculative vulnerabilities, stylistic preferences, or hypothetical problems as confirmed bugs.

If something needs further investigation, label it as an open question rather than a finding.

## 6. Severity Classification

| Severity | Meaning |
|---|---|
| Critical | Data loss, exploitable security vulnerability, or major production failure |
| Major | Incorrect behavior, serious edge case, or significant reliability issue |
| Minor | Limited bug, maintainability problem, or non-critical performance issue |
| Nit | Formatting, naming, or subjective preference |

Prioritize findings based on actual impact, not the amount of code involved.

## 7. Required Finding Format

For every verified finding, use:

### [SEVERITY] Short description

- Location: `src/path/file.js:42`
- Problem: Explain what is wrong.
- Impact: Explain what happens if it remains unfixed.
- Evidence: Explain the execution path or condition that causes it.
- Recommended fix: Provide a specific correction.

Reference exact file locations and line numbers.

Do not provide vague recommendations such as "improve error handling."

## 8. Review Output

Organize the final response as follows:

### Review Summary
- Files reviewed.
- Scope of changes.
- Overall assessment.

### Findings
Group findings by severity, highest first.

If no findings exist, explicitly state that no verified issues were found.

### Testing and Verification
Report:
- Tests executed.
- Tests passed or failed.
- Checks not executed.
- Important coverage gaps.

Never claim that a test passed if it was not executed.

### Verdict
Choose exactly one:

- APPROVE: No actionable issues found.
- APPROVE WITH NITS: Only minor non-blocking issues.
- REQUEST CHANGES: One or more actionable defects exist.

Explain the verdict in one concise paragraph.

## 9. Strict Rules

- Never modify files during a review unless explicitly asked to fix them.
- Never commit, push, or create a pull request during a review.
- Never discard or overwrite user changes.
- Never invent findings.
- Never claim unverified behavior.
- Never hide serious problems to be encouraging.
- Do not restate the entire diff.
- Avoid unnecessary refactoring recommendations.
- Separate confirmed defects from suggestions.
- Do not confuse passing tests with proof of correctness.
- If evidence is insufficient, state the limitation.
- Explain technical findings clearly when the user is learning.

The objective is to catch real defects before they reach production while helping the developer understand why they matter.