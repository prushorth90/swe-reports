# Payment Authorization Troubleshooting Notes
Type: troubleshooting notes

For elevated payment authorization errors, first separate upstream TLS failures from application validation failures. Inspect certificate expiry, trust bundle freshness, and handshake errors before retrying requests.

A stale upstream certificate bundle can produce a sudden authorization error increase with otherwise normal payments-service CPU. Refresh the certificate bundle, then verify authorization success rates and checkout error rates return to baseline.