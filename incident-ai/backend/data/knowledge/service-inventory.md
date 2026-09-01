# Inventory Service Operations Guide
Type: service documentation

inventory-service consumes stock updates and publishes cache invalidation events to Redis. Product availability can become stale when the cache invalidation worker processes events below incoming throughput.

Investigate consumer lag, worker throughput, dead-letter volume, and Redis command latency. Scale the invalidation workers when consumer lag grows while Redis remains healthy. Do not flush the entire cache unless stale keys cannot be identified safely.