# Demo 2: Amazon Bedrock Converse API

This demo shows how to build conversational assistants with the Amazon Bedrock Converse API. It includes a simple multi-turn travel chatbot and a restaurant booking assistant that demonstrates tool use.

## Files

```text
demo2-converse-api/
├── README.md
├── simple_travel_chat.py
├── restaurants_booking_assistant.py
└── requirements.txt
```

## What This Demo Teaches

- How to call `bedrock.converse(...)`.
- How to keep chat history across turns.
- How to use a system prompt.
- How to define tools for a model.
- How to execute local Python functions when the model requests a tool.
- How to send tool results back to the model.

## Model Used

The scripts use:

```python
MODEL_ID = "amazon.nova-lite-v1:0"
```

The AWS region is:

```python
region_name="us-east-1"
```

If your Bedrock setup uses another region, update the `boto3.client(...)` line in both scripts.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r demo2-converse-api/requirements.txt
```

Make sure AWS credentials are configured:

```bash
aws configure
```

You also need Bedrock model access enabled for `amazon.nova-lite-v1:0`.

## Script 1: Simple Travel Chat

Run:

```bash
cd demo2-converse-api
python simple_travel_chat.py
```

This script starts a command-line travel assistant.

Example conversation:

```text
Travel Assistant: Hello! I can help you plan your next trip. Where are you thinking of going?

You: I want to visit Japan for one week
Travel Assistant: ...
```

### How It Works

The script keeps a `messages` list:

```python
messages = []
```

Each user input is appended:

```python
messages.append({"role": "user", "content": [{"text": user_input}]})
```

Then the full conversation is sent to Bedrock:

```python
response = bedrock.converse(
    modelId=MODEL_ID,
    system=[{"text": SYSTEM_PROMPT}],
    messages=messages,
)
```

The assistant response is also appended to `messages`, which gives the model context for the next turn:

```python
output_message = response["output"]["message"]
messages.append(output_message)
```

This is the basic pattern for a stateful chat application.

## Script 2: Restaurant Booking Assistant With Tools

Run:

```bash
cd demo2-converse-api
python restaurants_booking_assistant.py
```

This script starts a command-line assistant that helps find a restaurant for tonight.

The assistant has access to three local tools:

- `get_cuisines`: returns cuisine types available in the mock restaurant data.
- `search_restaurants`: finds restaurants that match one or more cuisines.
- `get_availability`: checks whether a restaurant is available tonight.

The data is mocked in local Python lists and dictionaries, so the script does not call a real restaurant booking API.

## Tool Calling Flow

The restaurant assistant follows this loop:

1. User asks for a restaurant.
2. The user message is added to `messages`.
3. The app calls `bedrock.converse(...)` with `toolConfig`.
4. The model either returns a final answer or requests a tool.
5. If the model requests a tool, the Python script executes the matching local function.
6. The tool result is appended back into `messages`.
7. The app calls `bedrock.converse(...)` again so the model can use the tool result.
8. The loop continues until the model returns `end_turn`.

Important code path:

```python
response = bedrock.converse(
    modelId=MODEL_ID,
    system=[{"text": SYSTEM_PROMPT}],
    messages=messages,
    toolConfig={"tools": TOOLS},
)
```

The script checks why the model stopped:

```python
stop_reason = response["stopReason"]
```

If the stop reason is `tool_use`, the script runs the requested function locally:

```python
result = execute_tool(tool_name, tool_input)
```

Then it sends the tool result back as a user message:

```python
messages.append({"role": "user", "content": tool_results})
```

## Tool Schema Example

Each tool is described with a `toolSpec`. For example:

```python
{
    "toolSpec": {
        "name": "get_availability",
        "description": "Checks whether a specific restaurant has availability for tonight.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "string",
                        "description": "The unique ID of the restaurant to check.",
                    }
                },
                "required": ["restaurant_id"],
            }
        },
    }
}
```

The model reads the tool name, description, and input schema to decide when and how to call the tool.

## Mock Restaurant Data

The restaurant assistant uses hard-coded sample data:

- Italian: `Pasta Roma`, `Trattoria Bella`
- Japanese: `Sakura Garden`, `Ramen Yuki`
- Mexican: `El Mercado`
- Indian: `Spice Route`
- French: `Le Bistro`
- American: `The Grill House`

Availability is also mocked. For example, `Le Bistro` and `Ramen Yuki` are currently unavailable.

## Expected Output

The app prints tool calls and tool results so you can see the agent loop:

```text
[tool call] search_restaurants({'cuisines': ['Italian']})
[tool result] {'restaurants': [...]}
```

After checking availability, the assistant should recommend a restaurant using only the tool results.

## Common Errors

### Missing Credentials

Run:

```bash
aws configure
```

### Access Denied

Check that your IAM identity can invoke Bedrock models and that model access is enabled.

### Tool Validation Error

Check the `TOOLS` list. Tool schemas must be valid JSON Schema objects.

### Model Hallucinated A Restaurant

The system prompt tells the model to use tool results only. If behavior is inconsistent, make the system prompt stricter or add validation before printing the final response.

## When To Use This Pattern

Use the Converse API when:

- You are building a chatbot or assistant.
- You need multi-turn memory within a session.
- You want a consistent message format across models.
- You want the model to call tools.
- You are building an agent-style workflow.
