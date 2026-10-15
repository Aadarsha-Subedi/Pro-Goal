from datetime import timedelta

# Waits before each retry (the first attempt is immediate). After the last retry
# fails a delivery is marked failed and can be replayed by hand.
RETRY_DELAYS = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
    timedelta(hours=12),
)
# The first attempt plus one retry per delay above; then the delivery is failed.
MAX_ATTEMPTS = 1 + len(RETRY_DELAYS)
MAX_DISPATCH_ATTEMPTS = 5
MAX_PAUSE_SECONDS = 24 * 60 * 60
FAILURES_BEFORE_ATTENTION = 10
DISPATCH_BATCH_SIZE = 100
RETENTION_DAYS = 30
DUE_SOON_DAYS = 1  # due today or tomorrow
MAX_ERROR_LENGTH = 1000
