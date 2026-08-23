# Demo 3: Prompt Chaining And Critique

This demo shows how to build multi-step AI workflows with Amazon Bedrock. Instead of asking the model to do everything in one prompt, the scripts break the work into smaller model calls and pass outputs from one step into the next.

## Files

```text
demo3-chaining--critique/
├── README.md
├── content_pipeline.py
├── email_refiner.py
└── requirements.txt
```

## What This Demo Teaches

- How to chain multiple Bedrock `invoke_model` calls.
- How to use one model output to choose the next prompt.
- How to build a simple classification and response pipeline.
- How to ask a model to critique generated content.
- How to parse a model-generated score.
- How to use a quality threshold to decide whether to stop or refine.
- How to limit iterative workflows with a maximum attempt count.

## Model Used

Both scripts use:

```python
MODEL_ID = "amazon.nova-pro-v1:0"
```

The AWS region is:

```python
region_name="us-east-1"
```

If your Bedrock model access is enabled in another region, update the `boto3.client(...)` line in both scripts.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r demo3-chaining--critique/requirements.txt
```

Make sure AWS credentials are configured:

```bash
aws configure
```

You also need Bedrock model access enabled for `amazon.nova-pro-v1:0`.

## Script 1: Content Pipeline

Run:

```bash
cd demo3-chaining--critique
python content_pipeline.py
```

This script simulates a customer support workflow.

It processes three sample customer emails:

- A delayed delivery complaint.
- A subscription question.
- A refund request.

### Flow

```text
Customer Email
      |
      v
LLM Call 1: classify the email
      |
      v
COMPLAINT, QUESTION, or REFUND
      |
      v
LLM Call 2: generate the matching support response
      |
      v
Final Response
```

### How It Works

The first model call classifies the email:

```python
category = classify_email(email)
```

The model must return exactly one category:

```text
COMPLAINT, QUESTION, REFUND
```

The second model call uses the category to choose a response prompt:

```python
response = respond_to_email(email, category)
```

Each category has a different prompt template in `RESPONSE_PROMPTS`.

For example:

- `COMPLAINT` asks for empathy, apology, and investigation.
- `QUESTION` asks for a clear and concise answer.
- `REFUND` asks for refund status, timeline, and apology.

This is a routing pattern: classify first, then send the request down the right path.

## Script 2: Email Refiner

Run:

```bash
cd demo3-chaining--critique
python email_refiner.py
```

This script demonstrates an iterative generation loop.

The goal is to produce a professional cold outreach email inviting a senior engineering manager to speak at a local AWS community meetup.

### Flow

```text
Outreach Context
      |
      v
LLM Call 1: draft email
      |
      v
LLM Call 2: critique and score email
      |
      v
score >= threshold?
      |
      +-- yes --> done
      |
      +-- no --> LLM Call 3: refine email
                     |
                     v
              critique again
```

The loop stops when either:

- The score is at least `QUALITY_THRESHOLD`.
- The script reaches `MAX_ATTEMPTS`.

Current values:

```python
QUALITY_THRESHOLD = 8
MAX_ATTEMPTS = 5
```

### Key Functions

`draft_email(...)` creates the first version:

```python
email = draft_email(OUTREACH_CONTEXT)
```

`critique_email(...)` asks the model to score the draft:

```python
score, critique = critique_email(email)
```

The critique prompt requires the model to start with:

```text
SCORE: X/10
```

The script extracts the score with a regular expression:

```python
match = re.search(r"SCORE:\s*(\d+)", response)
```

If the score is too low, `refine_email(...)` rewrites the draft using the critique:

```python
email = refine_email(email, critique)
```

This is a critique-and-revision pattern. It is useful when output quality matters and the model can improve its own work based on structured feedback.

## Shared Bedrock Helper

Both scripts use a helper function named `invoke(...)`.

It builds a Bedrock Runtime request body:

```python
body = {
    "messages": [{"role": "user", "content": [{"text": prompt}]}],
    "inferenceConfig": {"maxTokens": 512, "temperature": temperature},
}
```

Then it calls:

```python
response = bedrock.invoke_model(
    modelId=MODEL_ID,
    body=json.dumps(body),
    contentType="application/json",
    accept="application/json",
)
```

Finally, it parses the model text from the response:

```python
result["output"]["message"]["content"][0]["text"]
```

## Expected Output

For `content_pipeline.py`, you should see each email, its category, and a generated support response.

For `email_refiner.py`, you should see one or more attempts. Each attempt prints:

- The current email draft.
- The score.
- The critique if the score is below the threshold.
- A final completion message when the quality threshold is met or attempts run out.

Exact wording can change between runs because the model is generative.

## Common Errors

### Missing Credentials

Run:

```bash
aws configure
```

### Access Denied

Check that your IAM identity can call Amazon Bedrock Runtime and that model access is enabled for `amazon.nova-pro-v1:0`.

### Wrong Region

The scripts use `us-east-1`. Change the region in the `boto3.client(...)` call if needed.

### Score Parsed As Zero

In `email_refiner.py`, the score becomes `0` if the model does not follow the required `SCORE: X/10` format. The prompt already asks for that exact format. In a production app, you could make this stronger by validating the response and retrying the critique step.

## When To Use These Patterns

Use prompt chaining when:

- A task has clear stages.
- One model output should influence the next step.
- You need routing, classification, or decision points.
- You want each prompt to stay focused and easier to debug.

Use critique and refinement when:

- Quality matters more than one-call latency.
- You can define a quality bar.
- You want to improve drafts before showing them to users.
- You need a repeatable review loop for generated content.
