# payments.py — before feature

STRIPE_KEY = os.environ["STRIPE_KEY"]
MAX_RETRIES = 3

def charge(order: Order) -> Receipt:
    """Charge a customer for an order, retrying on transient failures."""
    if existing := receipts.get(order.idempotency_key):
        return existing

    customer = load_customer(order.customer_id)
    if customer.is_blocked:
        raise PaymentFailed(order.id, reason="customer blocked")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            receipt = stripe_charge(STRIPE_KEY, customer, order.total)
            receipts.save(order.idempotency_key, receipt)
            return receipt
        except TransientError as err:
            last_error = err
            backoff(attempt)

    raise PaymentFailed(order.id) from last_error
