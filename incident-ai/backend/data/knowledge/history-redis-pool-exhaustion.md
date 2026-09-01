# Historical Incident: Redis Pool Exhaustion
Type: historical incident

On 2026-06-14, checkout-api latency increased from 280 ms to 1900 ms after a deployment raised payment retry concurrency. The additional requests exhausted the shared Redis connection pool. Redis error rate reached 11.8 percent while CPU reached 93 percent.

Responders increased Redis capacity and reduced retry concurrency. Checkout latency returned below 400 ms within twelve minutes. The follow-up action was to alert on connection pool saturation before request timeouts crossed the customer-impact threshold.