# AWS Bedrock API Demos

This repository contains small Python demos for calling Amazon Bedrock foundation models from code. The demos are designed for learners who want to understand the practical differences between the Bedrock `InvokeModel` API and the higher-level `Converse` API.

## What You Will Learn

- How to call Amazon Bedrock Runtime with `boto3`.
- How to send a prompt to an Amazon Nova model.
- How to read a normal model response.
- How to stream generated text token by token.
- How to build a conversational assistant with chat history.
- How to connect the Converse API to local tools.
- How to chain multiple model calls into a workflow.
- How to critique and refine generated content.

## Project Structure

```text
Demos/
├── README.md
├── demo1-invoke-api/
│   ├── README.md
│   ├── meeting_summarizer.py
│   ├── meeting_summarizer_stream.py
│   └── requirements.txt
├── demo2-converse-api/
│   ├── README.md
│   ├── simple_travel_chat.py
│   ├── restaurants_booking_assistant.py
│   └── requirements.txt
└── demo3-chaining--critique/
    ├── README.md
    ├── content_pipeline.py
    ├── email_refiner.py
    └── requirements.txt
```

## Demo Overview

### Demo 1: Invoke API

`demo1-invoke-api` shows the lower-level Bedrock Runtime invocation style.

It includes:

- `meeting_summarizer.py`: sends meeting notes to a model and prints the full response after generation finishes.
- `meeting_summarizer_stream.py`: sends the same request but streams the response as it is generated.

Use this demo when you want to understand request bodies, response parsing, and streaming events.

### Demo 2: Converse API

`demo2-converse-api` shows the higher-level Bedrock Converse API.

It includes:

- `simple_travel_chat.py`: a command-line travel assistant that keeps multi-turn chat history.
- `restaurants_booking_assistant.py`: a restaurant assistant that uses tool calling with local Python functions.

Use this demo when you want to build chat-style applications, assistants, or agents.

### Demo 3: Chaining And Critique

`demo3-chaining--critique` shows how to connect multiple Bedrock model calls into a complete workflow.

It includes:

- `content_pipeline.py`: classifies customer emails, then uses the classification to generate the right support response.
- `email_refiner.py`: drafts a cold outreach email, critiques and scores it, then improves it until it meets a quality threshold or reaches the maximum attempt count.

Use this demo when you want to understand prompt chaining, routing, self-critique, quality gates, and iterative refinement.

## Prerequisites

You need:

- Python 3.10 or newer.
- An AWS account.
- AWS credentials configured locally.
- Access enabled for the Amazon Nova models used by these demos.
- The AWS region `us-east-1`, unless you update the scripts.

The scripts use these model IDs:

- `amazon.nova-pro-v1:0` in Demo 1.
- `amazon.nova-lite-v1:0` in Demo 2.
- `amazon.nova-pro-v1:0` in Demo 3.

## AWS Setup

Configure credentials using one of the standard AWS methods:

```bash
aws configure
```

Or export environment variables:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

Your IAM identity needs permission to call Amazon Bedrock Runtime. For these demos, the important actions are:

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`

You must also enable model access for the Amazon Nova models in the Amazon Bedrock console.

## Recommended Setup

Create a virtual environment from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies for the demo you want to run:

```bash
pip install -r demo1-invoke-api/requirements.txt
```

or:

```bash
pip install -r demo2-converse-api/requirements.txt
```

or:

```bash
pip install -r demo3-chaining--critique/requirements.txt
```

All demos currently use the same dependency set.

## Running The Demos

Run Demo 1:

```bash
cd demo1-invoke-api
python meeting_summarizer.py
python meeting_summarizer_stream.py
```

Run Demo 2:

```bash
cd demo2-converse-api
python simple_travel_chat.py
python restaurants_booking_assistant.py
```

Run Demo 3:

```bash
cd demo3-chaining--critique
python content_pipeline.py
python email_refiner.py
```

## API Comparison

| API | Best For | What You Manage |
| --- | --- | --- |
| `invoke_model` | One-shot prompts, custom request bodies, direct model access | JSON body, model-specific response parsing |
| `invoke_model_with_response_stream` | Streaming output for lower latency user experience | Stream events and incremental text output |
| `converse` | Chat apps, multi-turn assistants, tool use | Message history, optional system prompt, tool config |

## Workflow Patterns

These demos introduce common AI application patterns:

- Single-call generation: send one prompt and return one answer.
- Streaming generation: show output as soon as model chunks arrive.
- Conversational state: preserve prior user and assistant messages.
- Tool use: let the model request external actions and use the results.
- Prompt chaining: use one model output as input to the next model call.
- Critique and refinement: evaluate output, then improve it until it passes a quality bar.

## Troubleshooting

### `AccessDeniedException`

Check that:

- Your AWS credentials are valid.
- Your IAM policy allows Bedrock Runtime calls.
- Model access is enabled in the Bedrock console.
- You are using the same region where model access is enabled.

### `ValidationException`

Check that:

- The model ID is correct.
- The request body matches the API you are calling.
- Tool schemas are valid JSON Schema objects.

### `NoCredentialsError`

Run `aws configure` or export AWS credential environment variables.

### Model Not Available

The scripts use `us-east-1`. If your Bedrock model access is configured in another region, update this line in the scripts:

```python
boto3.client("bedrock-runtime", region_name="us-east-1")
```

## Notes For Future Demos

This repository is ready for more demos. A good naming pattern is:

```text
demo3-feature-name/
demo4-feature-name/
demo5-feature-name/
```

Each new demo should include:

- A focused `README.md`.
- A `requirements.txt`.
- Small runnable scripts.
- Clear comments around the Bedrock API pattern being taught.
