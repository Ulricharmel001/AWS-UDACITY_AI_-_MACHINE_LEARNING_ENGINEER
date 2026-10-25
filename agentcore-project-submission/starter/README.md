# Udacity AWS AI Engineer — Customer Support Chatbot

An AWS Bedrock-based customer support chatbot for an online shop. It classifies customer messages into three categories and routes them to the appropriate handling path.

## Architecture

1. **Bedrock Flow** (`support-chatbot-flow`) — the entry point. Given a customer `document`, a `Classifier` prompt node categorizes the message into `BUG_REPORT`, `PLATFORM_QUESTION`, or `ANYTHING_ELSE`, then a `Route` condition node sends it down one of three paths:
   - `BUG_REPORT` → `BugReportOutput` — hands off to the AgentCore-managed `support_chatbot` harness, which collects bug details and calls the `create_bug_report` Gateway tool.
   - `PLATFORM_QUESTION` → `FAQPrompt` → `PlatformQuestionOutput` — answers using only the embedded `online_shop_faq.md` content. If the FAQ does not cover the question, it returns: `Please contact human support at 1-800-555-0199 (Mon-Fri).`
   - `ANYTHING_ELSE` → `AnythingElsePrompt` → `AnythingElseOutput` — returns: `Please contact human support at 1-800-555-0199 (Mon-Fri).`
   - A valid `default` condition keeps the flow satisfiable per Bedrock Flow requirements.

2. **AgentCore managed harness** (`support_chatbot`) — runs the system prompt + Nova Pro and drives the multi-turn bug-detail collection (description, reproduction steps, browser, OS, device) before calling `create_bug_report`.

3. **AgentCore Gateway + Lambda tool** — `create_bug_report` validates fields and writes a bug ticket (UUID) to DynamoDB.

4. **DynamoDB** — `bug-report-tool-stack-bug-reports` stores bug tickets.

## Categories

| Category | Handling |
|----------|----------|
| `BUG_REPORT` | AgentCore harness bug-ticket workflow |
| `PLATFORM_QUESTION` | FAQ Prompt from `online_shop_faq.md` |
| `ANYTHING_ELSE` | Human support: 1-800-555-0199 (Mon-Fri) |
| (default) | Falls through to anything-else handling |

## Deployment

- `cloudformation-tool.yaml` — bug-report table, Lambda, and AgentCore IAM roles.
- `setup_gateway.py` — creates the AgentCore Gateway and registers the `create_bug_report` tool.
- `create_harness.py` — creates/updates the `support_chatbot` managed harness.
- `support-chatbot-flow.yaml` / `deploy-flow.sh` — deploys the Bedrock Flow in `us-east-1`.

```bash
./deploy-flow.sh
```

## Testing

- `harness-tests.json` — 30 harness test cases across the three categories.
- `flow-tests.json` — Bedrock Flow tests for bug, covered FAQ, uncovered FAQ, and anything-else paths.

## Evaluation

A Bedrock Evaluations (LLM-as-judge) run was previously completed for the `my-support-chatbot` model with a **0.93 correctness** score. This figure reflects that earlier evaluation and is not a claim of a newly performed evaluation.
