"""Who should hear about an event, whatever the channel (Slack DM, email).
Channels apply their own preference and delivery rules on top of this."""

from integrations.constants.events import EventType
from integrations.models import OutboxEvent
from integrations.services import event_text
from projects.constants.permissions import MEMBER_APPROVE
from projects.models import MemberPermission, Membership

# Events a person can be told about personally (besides channel announcements).
PERSONAL_EVENTS = (
    EventType.TASK_ASSIGNED,
    EventType.TASK_DUE_SOON,
    EventType.TASK_OVERDUE,
    EventType.COMMENT_ADDED,
    EventType.JOIN_REQUEST_CREATED,
)


def candidate_users(event: OutboxEvent) -> set[str]:
    """User ids who should hear about `event`, before preferences and any
    account linking. The person who caused the event never hears about their
    own action."""
    kind = event.event_type
    payload = event.payload
    ids: set[str] = set()
    if kind == EventType.TASK_ASSIGNED:
        if payload.get("assignee_id"):
            ids.add(payload["assignee_id"])
    elif kind in (EventType.TASK_DUE_SOON, EventType.TASK_OVERDUE):
        task = event_text.task_for(event)
        if task is not None:
            ids |= {str(pk) for pk in task.assignees.values_list("pk", flat=True)}
    elif kind == EventType.COMMENT_ADDED:
        task = event_text.task_for(event)
        if task is not None:
            ids |= {str(pk) for pk in task.assignees.values_list("pk", flat=True)}
            if task.created_by_id:
                ids.add(str(task.created_by_id))
    elif kind == EventType.JOIN_REQUEST_CREATED:
        approvers = MemberPermission.objects.filter(
            membership__project=event.project, code=MEMBER_APPROVE
        ).values_list("membership__user_id", flat=True)
        owners = Membership.objects.filter(
            project=event.project, is_owner=True
        ).values_list("user_id", flat=True)
        ids |= {str(pk) for pk in approvers} | {str(pk) for pk in owners}
    ids.discard(payload.get("actor_id"))
    return ids


def current_members(event: OutboxEvent, user_ids: set[str]) -> set[str]:
    """Of `user_ids`, those still in the project."""
    return {
        str(pk)
        for pk in Membership.objects.filter(
            project=event.project, user_id__in=user_ids
        ).values_list("user_id", flat=True)
    }
