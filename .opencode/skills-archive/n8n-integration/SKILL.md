---
name: n8n Integration
description: Integrate an n8n ticket triage workflow with the helpdesk API using a versioned payload contract, idempotency, and failure handling.
---

# n8n Integration

Act as a senior engineer integrating an n8n automation workflow with the helpdesk API.

Your goal is a contract that survives retries, malformed triage output, and workflow edits without corrupting tickets.

## Project Context

n8n receives an email or form submission, classifies it, and creates a ticket through the helpdesk webhook. The helpdesk owns validation, authentication, persistence, and lifecycle rules. n8n's classification is advisory input.

## Responsibilities

- Define the workflow-to-app contract.
- Map triage fields to ticket fields.
- Choose a stable external identity for idempotency.
- Handle retries and partial failures.
- Test the workflow end to end.
- Keep credentials out of exported workflow JSON.

## Workflow

1. Document the n8n trigger and the fields it produces.
2. Define a versioned payload with `source`, `externalId`, `title`, `description`, `requester`, `priority`, `category`, and `triage`.
3. Map priority with an allowlist and a safe default.
4. Use the email Message-ID or form submission ID as `externalId`.
5. Configure the HTTP Request node with JSON body, HMAC headers, a timeout, and retries on `5xx` or `429`.
6. Test success, duplicate, validation failure, and timeout.
7. Store the secret in n8n credentials and reference it by name.
8. Add a dead-letter path in n8n after repeated failures.

## Rules

- Treat n8n as a service, not a user. Never share an agent password.
- Send a stable idempotency key on every retry.
- Do not let the workflow set status, assignee, or user role.
- The helpdesk is the source of truth. n8n suggestions are advisory.
- Do not auto-close tickets from automation.
- Record the n8n execution ID in ticket metadata for traceability.
- Version the payload schema and reject unsupported versions.
- Redact ticket content in workflow logs.
- Do not let automation overwrite an existing ticket on every run. Create once, then update only through explicit endpoints.

## Output

1. Payload contract.
2. Field mapping table.
3. n8n node configuration.
4. Retry and timeout policy.
5. Test plan.
6. Failure runbook.

Reference: `references/payload-examples.md`.
