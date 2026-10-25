import boto3
import json

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
REGION = "us-west-2"

bedrock = boto3.client("bedrock-runtime", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

OUTPUT_FILE = "eval_responses.jsonl"

# Your actual S3 bucket
BUCKET_NAME = "ulrich-bedrock-evals-oregonulrich-bedrock-evals-oregon"

S3_KEY = "lesson-4/eval_responses.jsonl"

# Prompt Management version ARN
PROMPT_VERSION_ARN = (
    "arn:aws:bedrock:us-west-2:495040113705:prompt/DEBVEYWDBF:1"
)

# ---------------------------------------------------------------------------
# Product FAQ
# ---------------------------------------------------------------------------
PRODUCT_FAQ = """\
Product FAQ

Pricing:
- Individual plan: $29 per month
- Team plan: $99 per month (up to 10 users)
- Enterprise: contact sales for custom pricing

Free Trial:
- 14-day free trial available for all plans
- No credit card required to start

Features:
- Task management with priority levels and due dates
- Time tracking built into each task
- Gantt chart view for project timelines
- Integrations: Slack and Google Workspace only

Storage:
- Individual plan: 10 GB per user
- Team plan: 100 GB shared across the team

Supported Platforms:
- Web browsers (Chrome, Firefox, Safari, Edge)
- iOS and Android mobile apps

Security:
- SOC 2 Type II certified
- All data encrypted at rest and in transit

Support:
- Email support for all plans
- Live chat support for Team and Enterprise plans only
"""

# ---------------------------------------------------------------------------
# Evaluation Dataset
# ---------------------------------------------------------------------------
EVAL_QUESTIONS = [
    {
        "prompt": "How much does the team plan cost and how many users does it include?",
        "referenceResponse": "The Team plan costs $99 per month and includes up to 10 users.",
    },
    {
        "prompt": "Do I need to put in my credit card to start a free trial?",
        "referenceResponse": "No, a credit card is not required to start the 14-day free trial.",
    },
    {
        "prompt": "What kind of support do I get if I'm on the Individual plan?",
        "referenceResponse": "The Individual plan includes email support.",
    },
    {
        "prompt": "Does the software integrate with Microsoft Teams?",
        "referenceResponse": "No, the integrations are currently limited to Slack and Google Workspace only.",
    },
    {
        "prompt": "Do you offer any discounts for non-profit organizations?",
        "referenceResponse": "I'm sorry, but that information is not available in our FAQ.",
    },
    {
        "prompt": "What programming language is your mobile app built in?",
        "referenceResponse": "I'm sorry, but that information is not available in our FAQ.",
    },
]

# ---------------------------------------------------------------------------
# Invoke Nova Pro directly
# ---------------------------------------------------------------------------
def invoke(question: str) -> str:

    prompt_text = f"""You are a helpful customer support assistant for a project management SaaS company.

Your primary goal is to answer customer questions accurately and concisely.

Follow these strict rules:

1. Answer the customer's question using ONLY information explicitly stated in the Product FAQ.
2. Do not use outside knowledge.
3. Do not guess or make assumptions.
4. If the FAQ does not contain enough information to answer the question, reply exactly:
"I'm sorry, but that information is not available in our FAQ."
5. Keep the answer concise and directly answer the customer's question.

<product_faq>
{PRODUCT_FAQ}
</product_faq>

<customer_question>
{question}
</customer_question>
"""

    body = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt_text
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "temperature": 0.0,
            "maxTokens": 256
        }
    })

    response = bedrock.invoke_model(
        modelId="us.amazon.nova-pro-v1:0",
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())

    return result["output"]["message"]["content"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    records = []

    print("Running FAQ Assistant Eval")
    print("=" * 60)

    for item in EVAL_QUESTIONS:

        question = item["prompt"]
        reference = item["referenceResponse"]

        print(f"\nQuestion:  {question}")
        print(f"Expected:  {reference}")

        try:
            response = invoke(question)
        except Exception as e:
            response = f"Error calling Bedrock: {e}"

        print(f"Response:  {response}")
        print("-" * 60)

        records.append({
            "prompt": question,
            "referenceResponse": reference,
            "modelResponses": [
                {
                    "response": response,
                    "modelIdentifier": "faq-assistant"
                }
            ]
        })

    # Write JSONL
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        for record in records:
            f.write(json.dumps(record) + "\n")

    print(f"\nWrote {len(records)} records to {OUTPUT_FILE}")

    # Upload to S3
    s3.upload_file(
        OUTPUT_FILE,
        BUCKET_NAME,
        S3_KEY
    )

    print(
        f"Uploaded to s3://{BUCKET_NAME}/{S3_KEY}"
    )