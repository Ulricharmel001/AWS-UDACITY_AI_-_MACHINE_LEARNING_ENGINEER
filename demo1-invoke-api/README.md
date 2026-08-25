# Demo 1: Amazon Bedrock Invoke API

This demo shows how to call Amazon Bedrock models with the lower-level Runtime Invoke APIs. It uses a meeting summarization example to demonstrate both normal and streaming responses.

## Files

```text
demo1-invoke-api/
├── README.md
├── meeting_summarizer.py
├── meeting_summarizer_stream.py
└── requirements.txt
```

## What This Demo Teaches

- How to create a Bedrock Runtime client with `boto3`.
- How to build a model request body manually.
- How to call `invoke_model`.
- How to parse the generated text from the response body.
- How to call `invoke_model_with_response_stream`.
- How to print streamed output as chunks arrive.

## Model Used

The scripts use:

```python
model_id = "amazon.nova-pro-v1:0"
```

The AWS region is:

```python
region_name="us-east-1"
```

If your account uses another region, update the `boto3.client(...)` line in both scripts.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r demo1-invoke-api/requirements.txt
```

Make sure AWS credentials are configured:

```bash
aws configure
```

You also need Bedrock model access enabled for `amazon.nova-pro-v1:0`.

## Script 1: Non-Streaming Summarizer

Run:

```bash
cd demo1-invoke-api
python meeting_summarizer.py
```

What happens:

1. The script defines sample meeting notes.
2. `summarize_notes()` creates a Bedrock Runtime client.
3. The prompt asks the model to return key decisions and action items.
4. The request body is serialized with `json.dumps(...)`.
5. `bedrock.invoke_model(...)` sends the request.
6. The response body is read and parsed with `json.loads(...)`.
7. The final summary text is printed.

Important code path:

```python
response = bedrock.invoke_model(
    modelId=model_id,
    body=json.dumps(body),
    contentType="application/json",
    accept="application/json",
)
```

This is useful when your application can wait for the complete model response before displaying it.

## Script 2: Streaming Summarizer

Run:

```bash
cd demo1-invoke-api
python meeting_summarizer_stream.py
```

What happens:

1. The script sends the same meeting notes and prompt.
2. It calls `invoke_model_with_response_stream(...)`.
3. Bedrock returns a stream of events.
4. The script checks each event for `contentBlockDelta`.
5. Text chunks are printed immediately.

Important code path:

```python
for event in response["body"]:
    chunk = json.loads(event["chunk"]["bytes"])
    if "contentBlockDelta" in chunk:
        print(chunk["contentBlockDelta"]["delta"].get("text", ""), end="", flush=True)
```

Streaming is useful for chat interfaces, long summaries, and any user experience where the first visible token should appear quickly.

## Request Body Shape

Both scripts send a request body like this:

```python
body = {
    "messages": [{"role": "user", "content": [{"text": prompt}]}],
    "inferenceConfig": {"maxTokens": 512, "temperature": 0.0},
}
```

Key fields:

- `messages`: the conversation-style input sent to the model.
- `role`: the speaker role, here `user`.
- `content`: the text content for the model.
- `maxTokens`: the maximum response length.
- `temperature`: randomness control. `0.0` makes output more deterministic.

## Expected Output

The model should return a concise summary with:

- Key decisions made during the meeting.
- Action items and owners.

Because this is a generative model, exact wording may vary between runs.

## Common Errors

### Missing Credentials

If you see a credential error, run:

```bash
aws configure
```

### Access Denied

Check IAM permissions and Bedrock model access.

### Wrong Region

The scripts use `us-east-1`. Update the region if your Bedrock access is in a different region.

## When To Use This Pattern

Use `InvokeModel` when:

- You want direct control over the model request body.
- You are building a simple one-shot AI feature.
- You are experimenting with model-specific request and response formats.
- You need streaming but do not need the full Converse abstraction.
