"""Quick test to demonstrate the new RQ workers check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "sample"))

from utils import check_rq_workers

# Test with default Redis URL
redis_url = "redis://localhost:6379/0"

print("Testing RQ Workers Check")
print("=" * 60)
print(f"Redis URL: {redis_url}")
print(f"Queue: default")
print()

result = check_rq_workers(redis_url)

print(f"Status: {result['status']}")
print(f"Message: {result['message']}")

if 'details' in result:
    print(f"Details: {result['details']}")

print()
print("This check validates that RQ workers are actively listening")
print("to the ingestion queue, ensuring jobs won't queue forever.")
