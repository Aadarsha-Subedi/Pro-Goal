"""Cache key templates for the join-code brute-force limiter."""

WRONG_CODE_USER_KEY = "join-wrong-code:user:{user_id}"
WRONG_CODE_IP_KEY = "join-wrong-code:ip:{ip}"
WRONG_CODE_WINDOW_SECONDS = 60 * 60
