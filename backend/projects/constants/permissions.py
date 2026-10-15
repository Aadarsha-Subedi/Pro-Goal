"""Permission codes and the registry that describes them.

The owner holds every code implicitly; other members hold the codes granted to
them (`MemberPermission`). `projects.permissions` is the single place that
decides. To add a code: define the constant, add it to `REGISTRY` below, and
enforce it in a service through `projects.permissions`.
"""

from dataclasses import dataclass

PROJECT_NAME_CHANGE = "project.name.change"
PROJECT_DESCRIPTION_CHANGE = "project.description.change"
PROJECT_TAGS_CHANGE = "project.tags.change"
PROJECT_START_DATE_CHANGE = "project.start_date.change"
PROJECT_END_DATE_CHANGE = "project.end_date.change"
PROJECT_TASK_KEY_CHANGE = "project.task_key.change"
MEMBER_APPROVE = "member.approve"
MEMBER_REMOVE = "member.remove"
PERMISSIONS_MANAGE = "permissions.manage"

TASK_CREATE = "task.create"
TASK_DELETE = "task.delete"
TASK_TITLE_CHANGE = "task.title.change"
TASK_DESCRIPTION_CHANGE = "task.description.change"
TASK_STATUS_CHANGE = "task.status.change"
TASK_PRIORITY_CHANGE = "task.priority.change"
TASK_ASSIGNEES_CHANGE = "task.assignees.change"
TASK_START_DATE_CHANGE = "task.start_date.change"
TASK_DUE_DATE_CHANGE = "task.due_date.change"
TASK_TAGS_CHANGE = "task.tags.change"
TASK_PARENT_CHANGE = "task.parent.change"
NOTE_CREATE = "note.create"
NOTE_TITLE_CHANGE = "note.title.change"
NOTE_BODY_CHANGE = "note.body.change"
NOTE_TAGS_CHANGE = "note.tags.change"
NOTE_DELETE = "note.delete"
NOTE_LINK_CHANGE = "note.link.change"
COMMENT_CREATE = "comment.create"
COMMENT_MODERATE = "comment.moderate"
ATTACHMENT_CREATE = "attachment.create"
ATTACHMENT_DELETE = "attachment.delete"
INTEGRATION_LOGS_VIEW = "integration.logs.view"
INTEGRATION_SLACK_MANAGE = "integration.slack.manage"
ACTIVITY_VIEW = "activity.view"
STATUS_CREATE = "status.create"
STATUS_UPDATE = "status.update"
STATUS_DELETE = "status.delete"
PRIORITY_CREATE = "priority.create"
PRIORITY_UPDATE = "priority.update"
PRIORITY_DELETE = "priority.delete"


@dataclass(frozen=True)
class PermissionInfo:
    """One entry of the registry the API serves to the frontend."""

    code: str
    label: str
    description: str
    group: str


G_PROJECT = "Project"
G_MEMBERS = "Members"
G_TASKS = "Tasks"
G_NOTES = "Notes"
G_COMMENTS = "Comments"
G_STATUSES = "Statuses"
G_PRIORITIES = "Priorities"
G_ATTACHMENTS = "Attachments"
G_INTEGRATIONS = "Integrations"
G_ACTIVITY = "Activity"

GROUPS = (
    G_PROJECT,
    G_MEMBERS,
    G_TASKS,
    G_NOTES,
    G_COMMENTS,
    G_STATUSES,
    G_PRIORITIES,
    G_ATTACHMENTS,
    G_INTEGRATIONS,
    G_ACTIVITY,
)

REGISTRY: tuple[PermissionInfo, ...] = (
    PermissionInfo(
        PROJECT_NAME_CHANGE, "Rename project", "Change the project name.", G_PROJECT
    ),
    PermissionInfo(
        PROJECT_DESCRIPTION_CHANGE,
        "Edit project description",
        "Change the project description.",
        G_PROJECT,
    ),
    PermissionInfo(
        PROJECT_TAGS_CHANGE,
        "Edit project tags",
        "Add or remove project tags.",
        G_PROJECT,
    ),
    PermissionInfo(
        PROJECT_START_DATE_CHANGE,
        "Change project start date",
        "Set or clear the project start date.",
        G_PROJECT,
    ),
    PermissionInfo(
        PROJECT_END_DATE_CHANGE,
        "Change project end date",
        "Set or clear the project end date.",
        G_PROJECT,
    ),
    PermissionInfo(
        PROJECT_TASK_KEY_CHANGE,
        "Change task key",
        "Change the key shown before task numbers (for example APL).",
        G_PROJECT,
    ),
    PermissionInfo(
        MEMBER_APPROVE,
        "Review join requests",
        "See, approve and reject requests to join the project.",
        G_MEMBERS,
    ),
    PermissionInfo(
        MEMBER_REMOVE,
        "Remove members",
        "Remove other members from the project.",
        G_MEMBERS,
    ),
    PermissionInfo(
        PERMISSIONS_MANAGE,
        "Manage permissions",
        "Grant and revoke permissions the person holds themselves.",
        G_MEMBERS,
    ),
    PermissionInfo(TASK_CREATE, "Create tasks", "Create tasks and subtasks.", G_TASKS),
    PermissionInfo(TASK_DELETE, "Delete tasks", "Delete and restore tasks.", G_TASKS),
    PermissionInfo(
        TASK_TITLE_CHANGE, "Edit task titles", "Change a task title.", G_TASKS
    ),
    PermissionInfo(
        TASK_DESCRIPTION_CHANGE,
        "Edit task descriptions",
        "Change a task description.",
        G_TASKS,
    ),
    PermissionInfo(
        TASK_STATUS_CHANGE,
        "Change task status",
        "Move a task to another status.",
        G_TASKS,
    ),
    PermissionInfo(
        TASK_PRIORITY_CHANGE, "Change task priority", "Change a task priority.", G_TASKS
    ),
    PermissionInfo(
        TASK_ASSIGNEES_CHANGE,
        "Change assignees",
        "Assign or unassign people on a task.",
        G_TASKS,
    ),
    PermissionInfo(
        TASK_START_DATE_CHANGE,
        "Change task start date",
        "Set or clear a task start date.",
        G_TASKS,
    ),
    PermissionInfo(
        TASK_DUE_DATE_CHANGE,
        "Change task due date",
        "Set or clear a task due date.",
        G_TASKS,
    ),
    PermissionInfo(
        TASK_TAGS_CHANGE, "Edit task tags", "Add or remove task tags.", G_TASKS
    ),
    PermissionInfo(
        TASK_PARENT_CHANGE,
        "Change task parent",
        "Turn a task into a subtask, or back.",
        G_TASKS,
    ),
    PermissionInfo(NOTE_CREATE, "Create notes", "Create notes.", G_NOTES),
    PermissionInfo(
        NOTE_TITLE_CHANGE, "Edit note titles", "Change a note title.", G_NOTES
    ),
    PermissionInfo(NOTE_BODY_CHANGE, "Edit note text", "Change a note body.", G_NOTES),
    PermissionInfo(
        NOTE_TAGS_CHANGE, "Edit note tags", "Add or remove note tags.", G_NOTES
    ),
    PermissionInfo(NOTE_DELETE, "Delete notes", "Delete notes.", G_NOTES),
    PermissionInfo(
        NOTE_LINK_CHANGE,
        "Link notes to tasks",
        "Link and unlink notes on tasks.",
        G_NOTES,
    ),
    PermissionInfo(
        COMMENT_CREATE,
        "Write comments",
        "Comment on tasks. Everyone can edit and delete their own comments.",
        G_COMMENTS,
    ),
    PermissionInfo(
        COMMENT_MODERATE,
        "Moderate comments",
        "Edit and delete other people's comments.",
        G_COMMENTS,
    ),
    PermissionInfo(
        STATUS_CREATE,
        "Create statuses",
        "Add statuses to the project workflow.",
        G_STATUSES,
    ),
    PermissionInfo(
        STATUS_UPDATE,
        "Edit statuses",
        "Rename, reorder and re-categorise statuses.",
        G_STATUSES,
    ),
    PermissionInfo(
        STATUS_DELETE,
        "Delete statuses",
        "Delete statuses, moving their tasks elsewhere.",
        G_STATUSES,
    ),
    PermissionInfo(
        PRIORITY_CREATE, "Create priorities", "Add priorities.", G_PRIORITIES
    ),
    PermissionInfo(
        PRIORITY_UPDATE,
        "Edit priorities",
        "Rename and reorder priorities.",
        G_PRIORITIES,
    ),
    PermissionInfo(
        PRIORITY_DELETE,
        "Delete priorities",
        "Delete priorities, moving their tasks elsewhere.",
        G_PRIORITIES,
    ),
    PermissionInfo(
        ATTACHMENT_CREATE,
        "Upload attachments",
        "Attach files to tasks, notes and comments.",
        G_ATTACHMENTS,
    ),
    PermissionInfo(
        INTEGRATION_LOGS_VIEW,
        "View integration logs",
        "See integration health and the delivery log.",
        G_INTEGRATIONS,
    ),
    PermissionInfo(
        INTEGRATION_SLACK_MANAGE,
        "Manage Slack",
        "Connect, configure, disconnect and replay deliveries for Slack.",
        G_INTEGRATIONS,
    ),
    PermissionInfo(
        ACTIVITY_VIEW,
        "View project activity",
        "See everything that happened in the project. Everyone can see their own actions.",
        G_ACTIVITY,
    ),
    PermissionInfo(
        ATTACHMENT_DELETE,
        "Delete attachments",
        "Delete other people's attachments. Everyone can delete their own.",
        G_ATTACHMENTS,
    ),
)

ALL_PERMISSIONS = tuple(info.code for info in REGISTRY)
REGISTERED = frozenset(ALL_PERMISSIONS)

# Actions that stay with the owner and can never be delegated.
OWNER_ONLY_ACTIONS = (
    "Delete or restore the project",
    "Transfer ownership",
    "Regenerate the join code",
    "Archive or unarchive the project",
    "List the project on the explore page",
    "Manage the owner's permissions",
)

PRESET_VIEWER = "viewer"
PRESET_CONTRIBUTOR = "contributor"
PRESET_MANAGER = "manager"


@dataclass(frozen=True)
class PermissionPreset:
    name: str
    label: str
    description: str
    codes: frozenset[str]


_CONTRIBUTOR = frozenset(
    {
        TASK_CREATE,
        TASK_TITLE_CHANGE,
        TASK_DESCRIPTION_CHANGE,
        TASK_STATUS_CHANGE,
        TASK_PRIORITY_CHANGE,
        TASK_ASSIGNEES_CHANGE,
        TASK_START_DATE_CHANGE,
        TASK_DUE_DATE_CHANGE,
        TASK_TAGS_CHANGE,
        TASK_PARENT_CHANGE,
        NOTE_CREATE,
        NOTE_TITLE_CHANGE,
        NOTE_BODY_CHANGE,
        NOTE_TAGS_CHANGE,
        NOTE_LINK_CHANGE,
        COMMENT_CREATE,
        ATTACHMENT_CREATE,
    }
)

PRESETS: dict[str, PermissionPreset] = {
    PRESET_VIEWER: PermissionPreset(
        PRESET_VIEWER, "Viewer", "Can read everything and nothing else.", frozenset()
    ),
    PRESET_CONTRIBUTOR: PermissionPreset(
        PRESET_CONTRIBUTOR,
        "Contributor",
        "Creates and edits tasks and notes, comments and uploads files.",
        _CONTRIBUTOR,
    ),
    PRESET_MANAGER: PermissionPreset(
        PRESET_MANAGER,
        "Manager",
        "Everything that can be delegated, except managing permissions.",
        frozenset(REGISTERED - {PERMISSIONS_MANAGE}),
    ),
}

# Writable project field -> permission needed to change it.
PROJECT_FIELD_PERMISSIONS = {
    "name": PROJECT_NAME_CHANGE,
    "description": PROJECT_DESCRIPTION_CHANGE,
    "tags": PROJECT_TAGS_CHANGE,
    "start_date": PROJECT_START_DATE_CHANGE,
    "end_date": PROJECT_END_DATE_CHANGE,
    "task_key": PROJECT_TASK_KEY_CHANGE,
}
