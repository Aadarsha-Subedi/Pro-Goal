INTEGRATION_DISCONNECTED = "Integration disconnected."
DELIVERY_REPLAYED = "Delivery queued again."
WEBHOOK_ACCEPTED = "Accepted."

NOT_CONFIGURED = "Integrations are not configured on this server."
UNKNOWN_PROVIDER = "Unknown integration provider."
INTEGRATION_NOT_FOUND = "Integration not found."
DELIVERY_NOT_FOUND = "Delivery not found."
NOT_REPLAYABLE = "Only failed deliveries can be replayed."
INTEGRATION_INACTIVE = "Reconnect the integration before replaying."
INVALID_SIGNATURE = "Invalid signature."
INVALID_KEY = (
    "PROJECT_MANAGEMENT_INTEGRATION_ENCRYPTION_KEYS holds an invalid key. "
    'Generate one with: python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())"'
)
