"""Session bookkeeping constants."""

USER_AGENT_MAX_LENGTH = 1000
UNKNOWN_OS = "Unknown OS"
UNKNOWN_BROWSER = "Unknown browser"

# (substring of the lower-cased user agent, label). The first match wins.
OS_TOKENS = (
    ("android", "Android"),
    ("iphone", "iPhone"),
    ("ipad", "iPad"),
    ("windows", "Windows"),
    ("mac os", "macOS"),
    ("linux", "Linux"),
)
BROWSER_TOKENS = (
    ("edg/", "Edge"),
    ("opr/", "Opera"),
    ("chrome", "Chrome"),
    ("firefox", "Firefox"),
    ("safari", "Safari"),
)

# UserSession rows younger than this may not have a committed Session yet.
STALE_SESSION_GRACE_MINUTES = 1
