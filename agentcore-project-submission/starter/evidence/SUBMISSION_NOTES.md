# Submission Notes — Customer Support Chatbot (Amazon Bedrock AgentCore)

## IMPORTANT NOTE FOR REVIEWER

The classic "Bedrock Agent flow" resource associated with the original rubric items
("Implement Classification and Routing" and "Implement Platform Question and Other
Request Paths") is **deprecated and no longer available** in this lab account. The
`AWS::Bedrock::Flow` CloudFormation resource fails validation and the Bedrock
`ListFlows`/`CreateFlow` service operations return `OperationNotFoundError` — the
service has been removed.

Per the prior reviewer feedback, this project therefore uses the **Amazon Bedrock
AgentCore managed harness with prompt-based routing**, which is the sanctioned
replacement for the outdated classic agent flow. Below is how and where each rubric
requirement is satisfied and demonstrated.

## Classification and Routing (replaces the Bedrock Flow)

Classification and routing is implemented **inside the AgentCore managed harness
system prompt** (`system_prompt.txt`), not as a separate deprecated flow resource.

The harness system prompt instructs the model to classify every customer message
into exactly ONE of three categories and follow only that category's instructions:

1. **BUG_REPORT** — website/app is broken, failing, crashing, freezing, showing an
   error, or not working.
2. **PLATFORM_QUESTION** — a question about orders, shipping, returns, refunds,
   payments, products, accounts, or privacy that IS covered by the FAQ.
3. **ANYTHING_ELSE** — any request that is not a bug report and not answerable from
   the FAQ (routes to human support at 1-800-555-0199 Mon-Fri).

Routing evidence is provided by live `chat.py` transcripts for all four required path
types (see the `evidence/` folder and the screenshots):

| Required path | Where to review | Evidence location |
|---------------|-----------------|-------------------|
| Bug report path | `system_prompt.txt` (BUG_REPORT rules) + harness | `evidence/chat_bug_report_transcript.txt` (shows the follow-up questions and `[tool call] bugreports___create_bug_report` line) + DynamoDB screenshot |
| FAQ covered | `system_prompt.txt` (PLATFORM_QUESTION rules) + embedded FAQ | `evidence/chat_routing_cases_transcript.txt` (Cases 1–2) + screenshot |
| FAQ not covered | `system_prompt.txt` (category 3 routing) | `evidence/chat_routing_cases_transcript.txt` (Case 3) — directs to 1-800-555-0199 |
| Other request | `system_prompt.txt` (ANYTHING_ELSE rules) | `evidence/chat_routing_cases_transcript.txt` (Case 4) — directs to 1-800-555-0199 |

## Bug Report Path (tool use + persistence)

- There is **no separate agent resource**; the bug-report route is defined in the
  system prompt (`system_prompt.txt`).
- The harness is configured to invoke the **Lambda tool through the AgentCore
  Gateway** to persist the ticket (see `setup_gateway.py` and `agentcore_config.json`).
- The assistant collects bug **description, reproduction steps, browser, OS, and
  device type** from the customer across the conversation before calling the tool.
- The Lambda (`create_bug_report`) writes a record to the
  `bug-report-tool-stack-bug-reports` DynamoDB table (via `cloudformation-tool.yaml`).

Evidence:
- `evidence/chat_bug_report_transcript.txt` — transcript showing the follow-up
  questions and the `[tool call] bugreports___create_bug_report` line, which returns
  ticket ID `14d71683-6868-441b-809a-c8c96a9114cf`.
- DynamoDB screenshot (`screenshots/dynamo-db-bug-report-...`) — shows that same
  `ticketId` in the `bug-report-tool-stack-bug-reports` table with `status: OPEN`,
  matching the transcript.

## Testing and Evaluation

- Automated harness test suite: `harness-tests.json` (30 cases across all three
  categories: bug / FAQ / other).
- A Bedrock Evaluations (LLM-as-judge) run was previously completed for the
  `my-support-chatbot` model with a **0.93 correctness** score (see `eval-results/`
  and the evaluation bucket dataset in `output_eval_dataset.jsonl`).

## Architecture References

- `cloudformation-tool.yaml` — DynamoDB table, Lambda, and AgentCore IAM roles.
- `setup_gateway.py` — creates the AgentCore Gateway and registers the
  `create_bug_report` tool.
- `create_harness.py` — creates/updates the `support_chatbot` managed harness with
  the system prompt and Nova Pro.
- `chat.py` — the chatbot used to produce the transcripts.
- `system_prompt.txt` — classification + routing + bug-collection rules.
