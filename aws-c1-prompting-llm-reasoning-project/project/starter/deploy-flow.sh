#!/bin/bash
set -e

REGION="us-east-1"
STACK="support-chatbot-flow"

echo "Deploying Bedrock Flow in ${REGION}..."

aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file support-chatbot-flow.yaml \
  --region "$REGION" \
  --capabilities CAPABILITY_NAMED_IAM

echo
echo "FLOW CREATED"
echo "============"

aws cloudformation describe-stacks \
  --stack-name "$STACK" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs' \
  --output table
