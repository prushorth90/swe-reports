# Checkout Latency Response Runbook
Type: runbook

When checkout-api P95 latency rises above 1000 ms, compare its error rate with payments-service and Redis. A simultaneous rise across these services often indicates retry amplification rather than CPU saturation in checkout-api alone.

Check Redis connection pool utilization, rejected connections, command latency, and client retry concurrency. If the pool is exhausted, add capacity or reduce retry concurrency before restarting checkout-api instances. Confirm recovery by watching checkout P95 latency and payment authorization success rates for at least fifteen minutes.

Escalate to the payments team when authorization errors remain elevated after Redis latency has recovered.