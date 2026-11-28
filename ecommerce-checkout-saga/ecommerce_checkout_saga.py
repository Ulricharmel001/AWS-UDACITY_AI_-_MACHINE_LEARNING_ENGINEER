"""
ecommerce_checkout_saga.py - EXERCISE SOLUTION
==============================================
Lesson 7 Exercise: Saga Pattern for E-Commerce Checkout

Architecture:
    Customer submits order
          |
     ┌────┴─────────────────────────────────────────────────┐
     │  Checkout Saga Orchestrator (Python, NOT LLM-driven)  │
     │  Forward: Inventory → Payment → Shipping              │
     │  Compensate: reverse order on failure                 │
     └────┬─────────────────────────────────────────────────┘
          |
     ┌────┴─────────────────────────────────────────────────┐
     │  Checkout Saga State (DynamoDB)                       │
     │  checkout_id (PK) | status | current_step | steps[]   │
     │  lock | barrier counters                              │
     └────┬─────────────────────────────────────────────────┘
          |
     Three service agents (each has forward + compensating action):
     ┌────┴─────────────────────────────────────────────────┐
     │ InventoryAgent:  release_items / restore_stock       │
     │ PaymentAgent:    charge_card  / refund_card          │
     │ ShippingAgent:   schedule_shipping / cancel_shipping │
     └──────────────────────────────────────────────────────┘

Saga Pattern:
    1. Forward execution: call each service sequentially
       - On success: update state machine, move to next step
       - On failure: transition to "compensating" mode
    2. Compensation: iterate completed steps in REVERSE order
       - Each agent has a compensating tool
       - Update step status: completed → compensating → compensated
    3. Barrier counter: wait until all compensations complete
       - DynamoDB ADD atomically increments the counter
    4. Distributed lock: conditional write before compensation
       - Prevents concurrent compensation attempts

Key Concepts:
  1. SAGA: sequence of steps, each with a compensating action
  2. COMPENSATING TRANSACTION: undoes a completed step on failure
  3. REVERSE ORDER: compensate step 2 before step 1
  4. STATE MACHINE: tracks checkout progression
  5. DISTRIBUTED LOCK: prevents concurrent compensations
  6. BARRIER COUNTER: tracks N-of-N compensation completion

Tech Stack:
  - Python 3.11+
  - Strands Agents SDK (Agent class, @tool decorator)
  - Amazon Bedrock (Nova Lite for all agents)
  - DynamoDB checkout state (real AWS resource created by CloudFormation)
"""

import boto3
import json
import os
import re
import time
from decimal import Decimal
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from strands import Agent, tool
from strands.models import BedrockModel

load_dotenv()

# ─────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
NOVA_LITE_MODEL = os.environ.get("NOVA_LITE_MODEL", "amazon.nova-lite-v1:0")
CHECKOUT_SAGA_TABLE = os.environ.get(
    "CHECKOUT_SAGA_TABLE", "lesson-07-saga-checkout-saga"
)

# ─────────────────────────────────────────────────────
# DYNAMODB STATE
# ─────────────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
checkout_table = dynamodb.Table(CHECKOUT_SAGA_TABLE)


def clean_response(text: str) -> str:
    """Strip <thinking>...</thinking> tags from Nova outputs."""
    return re.sub(r"<thinking>.*?</thinking>\s*", "", str(text), flags=re.DOTALL).strip()


def run_agent_with_retry(agent_builder, prompt: str, max_retries: int = 3):
    """Run an agent with retry logic for transient Bedrock errors.

    Returns (elapsed_seconds, response_text).
    """
    for attempt in range(max_retries):
        try:
            agent = agent_builder()
            started = time.time()
            response = agent(prompt)
            elapsed = time.time() - started
            return elapsed, str(response)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(
                    f"    [Retry {attempt + 1}/{max_retries}] "
                    f"{e.__class__.__name__}, waiting {wait}s..."
                )
                time.sleep(wait)
            else:
                print(f"    [Failed] {e.__class__.__name__} after {max_retries} attempts")
                raise


def create_saga(checkout_id: str, order: dict, steps: list) -> dict:
    """Create the initial saga record in DynamoDB."""
    record = {
        "checkout_id": checkout_id,
        "order": order,
        "status": "pending",
        "current_phase": "executing",
        "current_step": 0,
        "steps": [
            {
                "name": step["name"],
                "forward_tool": step["forward_tool"],
                "compensating_tool": step["compensating_tool"],
                "status": "pending",
            }
            for step in steps
        ],
        "total_charged": 0.0,
        "total_refund": 0.0,
        "compensations_needed": 0,
        "compensations_completed": 0,
        "lock_status": "unlocked",
        "created_at": int(time.time()),
        "ttl": int(time.time()) + 7200,
    }
    checkout_table.put_item(Item=record)
    return record


def acquire_lock(checkout_id: str) -> bool:
    """Atomically acquire the compensation lock via conditional write."""
    try:
        checkout_table.update_item(
            Key={"checkout_id": checkout_id},
            UpdateExpression="SET lock_status = :locked, current_phase = :phase",
            ConditionExpression="lock_status = :unlocked",
            ExpressionAttributeValues={
                ":locked": "locked",
                ":phase": "compensating",
                ":unlocked": "unlocked",
            },
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def release_lock(checkout_id: str) -> None:
    """Release the compensation lock after resolution."""
    checkout_table.update_item(
        Key={"checkout_id": checkout_id},
        UpdateExpression="SET lock_status = :unlocked",
        ExpressionAttributeValues={":unlocked": "unlocked"},
    )


def get_saga(checkout_id: str) -> dict | None:
    """Get the latest saga record, or None if it does not exist."""
    response = checkout_table.get_item(Key={"checkout_id": checkout_id})
    return response.get("Item")


def increment_barrier(checkout_id: str) -> int:
    """Atomically increment the compensation barrier; return the new count."""
    response = checkout_table.update_item(
        Key={"checkout_id": checkout_id},
        UpdateExpression="ADD compensations_completed :one",
        ExpressionAttributeValues={":one": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["compensations_completed"])


def update_step_in_list(
    checkout_id: str,
    step_index: int,
    status: str,
    phase: str = "executing",
    **fields,
) -> None:
    """Update step fields using an explicit list index."""
    expression = f"SET steps[{step_index}].#st = :status"
    names = {"#st": "status"}
    values = {":status": status}

    for key, value in fields.items():
        expression += f", steps[{step_index}].{key} = :{key}"
        values[f":{key}"] = Decimal(str(value)) if isinstance(value, float) else value

    checkout_table.update_item(
        Key={"checkout_id": checkout_id},
        ConditionExpression="current_phase = :phase",
        UpdateExpression=expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues={":phase": phase, **values},
    )


def parse_agent_result(text: str) -> dict:
    """Extract the JSON result from an agent response."""
    cleaned = clean_response(text)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if not match:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {"success": False, "error": "No JSON found in agent response"}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON from agent"}


# ─────────────────────────────────────────────────────
# AGENT BUILDERS — FORWARD ACTIONS
# ─────────────────────────────────────────────────────
def build_inventory_agent(checkout_id: str, simulate_failure: bool = False):
    """Build an agent that releases items from inventory."""

    @tool
    def release_items(items: list, order_id: str) -> dict:
        """Release requested items from inventory for an order.

        Args:
            items: List of product IDs to release.
            order_id: Checkout identifier.
        """
        if simulate_failure:
            return {"success": False, "error": "Inventory service unavailable"}
        reserved = {item: 1 for item in items}
        update_step_in_list(checkout_id, 0, "completed", reserved=reserved)
        return {"success": True, "reserved": reserved}

    model = BedrockModel(model_id=NOVA_LITE_MODEL, temperature=0.0)
    return Agent(
        model=model,
        tools=[release_items],
        system_prompt=(
            "You manage inventory. Call release_items with the provided items and "
            "order ID. Return only its JSON result."
        ),
    )


def build_payment_agent(checkout_id: str, simulate_failure: bool = False):
    """Build an agent that charges the customer's card."""

    @tool
    def charge_card(amount: float, card: str, order_id: str) -> dict:
        """Charge the customer's card for an order.

        Args:
            amount: Total amount to charge.
            card: Payment method identifier.
            order_id: Checkout identifier.
        """
        if simulate_failure:
            return {"success": False, "error": "Card declined"}
        update_step_in_list(checkout_id, 1, "completed", charged=amount)
        checkout_table.update_item(
            Key={"checkout_id": checkout_id},
            UpdateExpression="ADD total_charged :amount",
            ExpressionAttributeValues={":amount": Decimal(str(amount))},
        )
        return {"success": True, "charge_id": f"CHG-{order_id}", "amount": amount}

    model = BedrockModel(model_id=NOVA_LITE_MODEL, temperature=0.0)
    return Agent(
        model=model,
        tools=[charge_card],
        system_prompt=(
            "You process payments. Call charge_card with the provided amount, card, "
            "and order ID. Return only its JSON result."
        ),
    )


def build_shipping_agent(checkout_id: str, simulate_failure: bool = False):
    """Build an agent that schedules shipping."""

    @tool
    def schedule_shipping(address: str, items: list, order_id: str) -> dict:
        """Schedule shipment for an order.

        Args:
            address: Shipping address.
            items: List of product IDs to ship.
            order_id: Checkout identifier.
        """
        if simulate_failure:
            return {"success": False, "error": "Shipping carrier unavailable"}
        tracking = f"TRK-{order_id}"
        update_step_in_list(checkout_id, 2, "completed", tracking_number=tracking)
        return {"success": True, "tracking_number": tracking}

    model = BedrockModel(model_id=NOVA_LITE_MODEL, temperature=0.0)
    return Agent(
        model=model,
        tools=[schedule_shipping],
        system_prompt=(
            "You schedule shipping. Call schedule_shipping with the provided address, "
            "items, and order ID. Return only its JSON result."
        ),
    )


# ─────────────────────────────────────────────────────
# COMPENSATING ACTION BUILDERS
# ─────────────────────────────────────────────────────
def build_restore_stock_agent(checkout_id: str, step_index: int):
    """Build an agent that restores previously reserved inventory."""

    @tool
    def restore_stock(items: list) -> dict:
        """Restore items to inventory during compensation.

        Args:
            items: List of product IDs to restore.
        """
        update_step_in_list(checkout_id, step_index, "compensated", phase="compensating")
        increment_barrier(checkout_id)
        return {"success": True, "action": "restore_stock", "items": items}

    model = BedrockModel(model_id=NOVA_LITE_MODEL, temperature=0.0)
    return Agent(
        model=model,
        tools=[restore_stock],
        system_prompt=(
            "You restore inventory during checkout compensation. Call restore_stock "
            "with the provided items. Return only its JSON result."
        ),
    )


def build_refund_agent(checkout_id: str, step_index: int):
    """Build an agent that refunds a completed payment."""

    @tool
    def refund_card(amount: float, charge_id: str) -> dict:
        """Refund a charge during checkout compensation.

        Args:
            amount: Amount to refund.
            charge_id: Original charge identifier.
        """
        checkout_table.update_item(
            Key={"checkout_id": checkout_id},
            UpdateExpression="ADD total_refund :amount",
            ExpressionAttributeValues={":amount": Decimal(str(amount))},
        )
        update_step_in_list(checkout_id, step_index, "compensated", phase="compensating")
        increment_barrier(checkout_id)
        return {"success": True, "action": "refund_card", "amount": amount}

    model = BedrockModel(model_id=NOVA_LITE_MODEL, temperature=0.0)
    return Agent(
        model=model,
        tools=[refund_card],
        system_prompt=(
            "You issue refunds during checkout compensation. Call refund_card with "
            "the provided amount and charge ID. Return only its JSON result."
        ),
    )


def build_cancel_shipping_agent(checkout_id: str, step_index: int):
    """Build an agent that cancels scheduled shipping."""

    @tool
    def cancel_shipping(tracking_number: str) -> dict:
        """Cancel a shipment during checkout compensation.

        Args:
            tracking_number: Tracking number of the shipment to cancel.
        """
        update_step_in_list(checkout_id, step_index, "compensated", phase="compensating")
        increment_barrier(checkout_id)
        return {"success": True, "action": "cancel_shipping", "tracking_number": tracking_number}

    model = BedrockModel(model_id=NOVA_LITE_MODEL, temperature=0.0)
    return Agent(
        model=model,
        tools=[cancel_shipping],
        system_prompt=(
            "You cancel shipments during checkout compensation. Call cancel_shipping "
            "with the provided tracking number. Return only its JSON result."
        ),
    )


# ─────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────
STEPS = [
    {
        "name": "inventory",
        "forward_tool": "release_items",
        "compensating_tool": "restore_stock",
    },
    {
        "name": "payment",
        "forward_tool": "charge_card",
        "compensating_tool": "refund_card",
    },
    {
        "name": "shipping",
        "forward_tool": "schedule_shipping",
        "compensating_tool": "cancel_shipping",
    },
]


def run_checkout_saga(order: dict) -> dict:
    """Run one checkout saga end to end."""
    checkout_id = order["checkout_id"]
    print(f"\n{'=' * 60}")
    print(f"CHECKOUT {checkout_id}: {order['customer']}")
    print(f"{'=' * 60}")

    create_saga(checkout_id, order, STEPS)

    total_elapsed = 0.0
    completed_steps = []

    forward_specs = [
        (
            lambda: build_inventory_agent(checkout_id, order["simulate_failure"] == "inventory"),
            json.dumps({
                "items": order["items"],
                "order_id": checkout_id,
            }),
        ),
        (
            lambda: build_payment_agent(checkout_id, order["simulate_failure"] == "payment"),
            json.dumps({
                "amount": order["total"],
                "card": order["payment_method"],
                "order_id": checkout_id,
            }),
        ),
        (
            lambda: build_shipping_agent(checkout_id, order["simulate_failure"] == "shipping"),
            json.dumps({
                "address": order["shipping_address"],
                "items": order["items"],
                "order_id": checkout_id,
            }),
        ),
    ]

    for index, (builder, prompt) in enumerate(forward_specs):
        step = STEPS[index]
        print(f"\n  Step {index + 1}: {step['name']}")
        elapsed, result_text = run_agent_with_retry(builder, prompt)
        total_elapsed += elapsed
        result = parse_agent_result(result_text)

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            print(f"    FAILED: {error}")
            update_step_in_list(checkout_id, index, "failed", error=error)

            if not acquire_lock(checkout_id):
                return {
                    "saga_id": checkout_id,
                    "status": "failed",
                    "error": "Could not acquire compensation lock",
                }

            checkout_table.update_item(
                Key={"checkout_id": checkout_id},
                UpdateExpression=(
                    "SET current_phase = :phase, #st = :st, "
                    "compensations_needed = :needed, compensations_completed = :done"
                ),
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":phase": "compensating",
                    ":st": "failed",
                    ":needed": len(completed_steps),
                    ":done": 0,
                },
            )

            return compensate(completed_steps, checkout_id, total_elapsed, error)

        print(f"    OK ({elapsed:.2f}s)")
        update_step_in_list(checkout_id, index, "completed")
        completed_steps.append((index, step, result))
        checkout_table.update_item(
            Key={"checkout_id": checkout_id},
            UpdateExpression="SET current_step = :next",
            ExpressionAttributeValues={":next": index + 1},
        )

    checkout_table.update_item(
        Key={"checkout_id": checkout_id},
        UpdateExpression="SET current_phase = :phase, #st = :st",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":phase": "done", ":st": "completed"},
    )

    print(f"\n  RESULT: COMPLETED ({total_elapsed:.2f}s)")
    return {
        "saga_id": checkout_id,
        "status": "completed",
        "steps_completed": len(completed_steps),
    }


def compensate(
    completed_steps: list,
    checkout_id: str,
    elapsed: float,
    error: str,
) -> dict:
    """Compensate completed steps in reverse order."""
    print(f"\n  Compensation: {len(completed_steps)} step(s) to undo")
    compensations = []

    compensation_builders = {
        "inventory": build_restore_stock_agent,
        "payment": build_refund_agent,
        "shipping": build_cancel_shipping_agent,
    }

    for index, step, forward_result in reversed(completed_steps):
        builder = lambda: compensation_builders[step["name"]](checkout_id, index)
        print(f"    Compensating: {step['name']}")

        if step["name"] == "inventory":
            prompt = json.dumps({"items": forward_result.get("reserved", {})})
        elif step["name"] == "payment":
            prompt = json.dumps({
                "amount": forward_result.get("amount", 0),
                "charge_id": forward_result.get("charge_id", ""),
            })
        else:
            prompt = json.dumps({
                "tracking_number": forward_result.get("tracking_number", "")
            })

        _, result_text = run_agent_with_retry(builder, prompt)
        result = parse_agent_result(result_text)
        compensations.append(result)

        saga = get_saga(checkout_id)
        if saga is None:
            continue
        needed = saga.get("compensations_needed", 0)
        done = saga.get("compensations_completed", 0)
        print(f"    Barrier: {done}/{needed}")

        if done >= needed:
            checkout_table.update_item(
                Key={"checkout_id": checkout_id},
                UpdateExpression=(
                    "SET current_phase = :phase, #st = :st, "
                    "compensations = :comps, error = :err"
                ),
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":phase": "resolved",
                    ":st": "failed",
                    ":comps": compensations,
                    ":err": error,
                },
            )
            break

    release_lock(checkout_id)
    print(f"\n  RESULT: COMPENSATED ({elapsed:.2f}s)")
    return {
        "saga_id": checkout_id,
        "status": "failed",
        "error": error,
        "compensations": compensations,
    }


ORDERS = [
    {
        "checkout_id": "CHK-001",
        "customer": "Alice Chen",
        "items": ["LAPTOP-001", "MOUSE-002"],
        "total": 1299.99,
        "payment_method": "card-****4242",
        "shipping_address": "123 Main St, Seattle, WA",
        "simulate_failure": None,
    },
    {
        "checkout_id": "CHK-002",
        "customer": "Bob Martinez",
        "items": ["BOOK-101", "PEN-202"],
        "total": 45.50,
        "payment_method": "card-****1881",
        "shipping_address": "456 Oak Ave, Portland, OR",
        "simulate_failure": "payment",
    },
    {
        "checkout_id": "CHK-003",
        "customer": "Carol Johnson",
        "items": ["CAMERA-300", "LENS-301"],
        "total": 899.00,
        "payment_method": "card-****9021",
        "shipping_address": "789 Pine Rd, Austin, TX",
        "simulate_failure": "shipping",
    },
]


def main() -> None:
    print("=" * 60)
    print("E-COMMERCE CHECKOUT SAGA — EXERCISE SOLUTION")
    print("=" * 60)
    print(f"Region: {AWS_REGION}")
    print(f"Model: {NOVA_LITE_MODEL}")
    print(f"Table: {CHECKOUT_SAGA_TABLE}")

    results = [run_checkout_saga(order) for order in ORDERS]

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for result in results:
        print(
            f"  {result['saga_id']}: {result['status'].upper()} "
            f"— {len(result.get('compensations', []))} compensation(s)"
        )


if __name__ == "__main__":
    main()
