# payments.speck.py — before feature

STRIPE_KEY: str
MAX_RETRIES: int
FRAUD_THRESHOLD: float

def charge(order: Order) -> Receipt:
    """Charge a customer for an order, retrying on transient failures.

    PSEUDOCODE:
    1) if this order was already charged, return its receipt
    2) load the customer, and reject if they are blocked
    3) reject if the order's fraud score exceeds FRAUD_THRESHOLD
    4) charge the customer and save the receipt, retrying on failure

    CONSTANTS:
      - STRIPE_KEY: str
      - MAX_RETRIES: int
      - FRAUD_THRESHOLD: float

    CALLS:
      - load_customer(customer_id) -> Customer
      - fraud_score(order: Order) -> float
      - stripe_charge(key: str, customer: Customer, amount: Money) -> Receipt
    """
    ...
