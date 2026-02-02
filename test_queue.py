"""Quick test of the background job queue"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.queue import enqueue_job, get_job_status, get_queue_stats
from backend.job_handlers import simple_test_job


print("="*60)
print("TESTING BACKGROUND JOB QUEUE")
print("="*60)

# Test 1: Enqueue a simple job
print("\n[1] Enqueuing simple test job...")
job = enqueue_job(
    simple_test_job,
    "Cogent System",
    "Hello from the job queue!",
    queue_name='high'
)
print(f"   SUCCESS: Job enqueued: {job.id}")
print(f"   Status: {job.get_status()}")

# Test 2: Check queue stats
print("\n[2] Queue statistics:")
stats = get_queue_stats()
for queue_name, queue_data in stats.items():
    print(f"   {queue_name.upper()} queue:")
    print(f"      - Pending: {queue_data['count']}")
    print(f"      - Failed: {queue_data['failed']}")

# Test 3: Get job details
print("\n[3] Job details:")
status = get_job_status(job.id)
print(f"   ID: {status['id']}")
print(f"   Status: {status['status']}")
print(f"   Created: {status['created_at']}")

print("\n" + "="*60)
print("SUCCESS: QUEUE TEST COMPLETED")
print("="*60)
print("\nTo process this job, run:")
print("   python worker.py --burst")
