"""Content of the shared demo projects. Plain data, no dates, so nothing goes
stale. Statuses and priorities are the project defaults."""

# Each task: (title, description, status, priority, parent index or None, tags)
# Each note: (title, body)
# Each comment: (task index, body)
DEMO_PROJECTS = [
    {
        "key": "sprint-board",
        "name": "Demo: Product sprint",
        "task_key": "SPR",
        "description": (
            "A software team's sprint board. Look around: board, task detail, "
            "notes and activity. Use Copy to my workspace to edit your own copy."
        ),
        "tags": ["demo", "software"],
        "tasks": [
            (
                "Plan sprint 12",
                "Pick the goal and size the work.",
                "Done",
                "High",
                None,
                ["planning"],
            ),
            (
                "Design onboarding flow",
                "Sketch the first-run screens.",
                "In review",
                "High",
                None,
                ["design"],
            ),
            (
                "Wireframes for the welcome screen",
                "Low fidelity is fine.",
                "Done",
                "Medium",
                1,
                ["design"],
            ),
            ("Copy review", "Check tone and spelling.", "To do", "Low", 1, ["design"]),
            (
                "Build sign-up API",
                "Email and Google sign-in.",
                "In progress",
                "Urgent",
                None,
                ["backend"],
            ),
            (
                "Write API tests",
                "Cover the happy path and rate limits.",
                "To do",
                "Medium",
                4,
                ["backend"],
            ),
            (
                "Fix login redirect bug",
                "Users land on a blank page after login.",
                "In progress",
                "High",
                None,
                ["bug"],
            ),
            ("Update the README", "Add setup steps.", "To do", "Low", None, ["docs"]),
            (
                "Cancel the legacy export",
                "Replaced by the new report.",
                "Cancelled",
                "Low",
                None,
                ["cleanup"],
            ),
        ],
        "notes": [
            (
                "Sprint goals",
                "# Sprint 12\n\n- Ship the onboarding flow\n- Fix the login redirect\n- Keep the API tests green\n",
            ),
            (
                "Definition of done",
                "A task is done when it is reviewed, tested and documented.\n",
            ),
        ],
        "comments": [
            (4, "Google sign-in works locally. Email verification is next."),
            (6, "Reproduced on Safari only. Looking at the cookie settings."),
        ],
    },
    {
        "key": "marketing-launch",
        "name": "Demo: Marketing launch",
        "task_key": "MKT",
        "description": (
            "A small marketing team preparing a product launch. Shows tags, "
            "priorities and subtasks."
        ),
        "tags": ["demo", "marketing"],
        "tasks": [
            (
                "Launch announcement",
                "Blog post, email and social.",
                "In progress",
                "Urgent",
                None,
                ["content"],
            ),
            (
                "Draft the blog post",
                "800 words, one screenshot.",
                "In review",
                "High",
                0,
                ["content"],
            ),
            (
                "Schedule social posts",
                "Three platforms, one week.",
                "To do",
                "Medium",
                0,
                ["social"],
            ),
            (
                "Prepare the email list",
                "Clean and segment.",
                "To do",
                "Medium",
                None,
                ["email"],
            ),
            (
                "Press kit",
                "Logo, screenshots and a one pager.",
                "In progress",
                "Medium",
                None,
                ["content"],
            ),
            (
                "Collect customer quotes",
                "Ask five friendly customers.",
                "To do",
                "Low",
                None,
                ["research"],
            ),
            (
                "Set up analytics dashboard",
                "Track sign-ups per channel.",
                "Done",
                "High",
                None,
                ["analytics"],
            ),
        ],
        "notes": [
            ("Brand voice", "Plain, friendly and specific. No buzzwords.\n"),
        ],
        "comments": [
            (1, "First draft is ready for review."),
        ],
    },
    {
        "key": "personal-goals",
        "name": "Demo: Personal goals",
        "task_key": "ME",
        "description": (
            "One person tracking goals for the year. Shows the project tool is "
            "not only for teams."
        ),
        "tags": ["demo", "personal"],
        "tasks": [
            (
                "Run a 10k",
                "Follow an eight week plan.",
                "In progress",
                "High",
                None,
                ["health"],
            ),
            (
                "Run three times a week",
                "Easy pace, no records.",
                "In progress",
                "Medium",
                0,
                ["health"],
            ),
            (
                "Read twelve books",
                "One a month.",
                "In progress",
                "Medium",
                None,
                ["learning"],
            ),
            (
                "Finish the current book",
                "Forty pages to go.",
                "To do",
                "Low",
                2,
                ["learning"],
            ),
            (
                "Learn basic Spanish",
                "Fifteen minutes a day.",
                "To do",
                "Medium",
                None,
                ["learning"],
            ),
            (
                "Plan the summer trip",
                "Pick dates and book the flights.",
                "To do",
                "High",
                None,
                ["travel"],
            ),
            (
                "Declutter the garage",
                "Sort, donate and recycle.",
                "Done",
                "Low",
                None,
                ["home"],
            ),
        ],
        "notes": [
            (
                "Why these goals",
                "Health, learning and time away. Keep the list short.\n",
            ),
        ],
        "comments": [
            (0, "Week three done. Feeling good."),
        ],
    },
]
