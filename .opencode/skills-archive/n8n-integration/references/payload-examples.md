# n8n Payload Examples

## Success

```http
POST /api/webhooks/n8n/tickets
X-Webhook-Id: 01J8Z3K4T9
X-Webhook-Timestamp: 1763115300
X-Webhook-Signature: sha256=...
X-Webhook-Schema-Version: 1

{
  "schemaVersion": 1,
  "source": "n8n-email-triage",
  "externalId": "<CABc123@mail.example.com>",
  "title": "VPN disconnects every 10 minutes",
  "description": "Remote user loses VPN connection repeatedly since this morning.",
  "requester": { "email": "sam@example.com", "name": "Sam Lee" },
  "priority": "HIGH",
  "category": "network",
  "triage": {
    "summary": "Recurring VPN drop, likely network or client issue",
    "confidence": 0.91,
    "executionId": "exec_88"
  }
}
```

Response `201`:

```json
{ "ticketId": "tkt_1007", "status": "OPEN", "duplicate": false }
```

Duplicate retry returns `200`:

```json
{ "ticketId": "tkt_1007", "status": "OPEN", "duplicate": true }
```

Validation failure `400`:

```json
{
  "error": "VALIDATION_ERROR",
  "details": [{ "field": "requester.email", "message": "Invalid email" }],
  "requestId": "req_abc"
}
```

## Field Mapping

| n8n field | Ticket field | Rule |
| --- | --- | --- |
| schemaVersion | none | Must equal a supported version |
| source | ticket.source | Constant per workflow |
| externalId | ticket.external_id | Unique with source |
| title | ticket.title | Trim, 5 to 200 characters |
| description | ticket.description | Trim, max 10,000 characters |
| requester.email | user.email | Find or create the requester |
| requester.name | user.name | Optional display name |
| priority | ticket.priority | Allowlist, default `MEDIUM` |
| category | ticket.category | Allowlist, default `other` |
| triage.summary | ticket.ai_summary | Advisory only |
| triage.confidence | ticket.triage_confidence | 0 to 1, optional |
| triage.executionId | ticket.metadata.n8nExecutionId | Traceability |

## Priority Mapping

| n8n output | Ticket priority |
| --- | --- |
| critical, outage, urgent | URGENT |
| high, hardware failure | HIGH |
| normal, medium | MEDIUM |
| low, question | LOW |
| unknown or missing | MEDIUM |

## HTTP Request Node

- Method: `POST`.
- URL: `{{ $env.HELPDESK_URL }}/api/webhooks/n8n/tickets`.
- Authentication: none. Use HMAC headers instead.
- Send Body: on, JSON.
- Timeout: 10 seconds.
- Retry On Fail: on, 3 tries, 5-second wait.
- Retry only on `429` and `5xx`, never on `4xx`.
- Store the secret in an n8n credential, not in the node or an exported workflow.

## Test Plan

1. Fresh payload returns `201` and creates one ticket.
2. Replayed payload returns `200` and still has one ticket.
3. Wrong signature returns `401`.
4. Missing `title` returns `400`.
5. Unsupported `schemaVersion` returns `422`.
6. Simulated `500` triggers exactly three retries.
7. The n8n execution ID is present in ticket metadata.
8. The ticket appears with `OPEN` status and no assignee.
