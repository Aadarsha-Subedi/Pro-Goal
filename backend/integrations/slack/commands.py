"""The `/task` slash command. Runs in a worker: the HTTP endpoint has already
answered Slack within its 3-second limit."""

import logging
import re
from urllib.parse import parse_qs

from django.conf import settings

from common.exception.domain import AppException
from integrations.constants.events import Source
from integrations.constants.statuses import IntegrationStatus
from integrations.context import use_source
from integrations.models import InboundWebhook, Integration
from integrations.services import linking
from integrations.slack import client, constants
from integrations.slack.messages import task_url
from projects.models import Membership, Project
from tracker.constants import fields
from tracker.constants.categories import StatusCategory
from tracker.models import Status
from tracker.services import access as tracker_access
from tracker.services import task_service

logger = logging.getLogger(__name__)

_CREATE = re.compile(r"^create\s+(?P<key>[A-Za-z]{2,5})\s+(?P<title>.+)$", re.DOTALL)
_DONE = re.compile(r"^done\s+(?P<key>[A-Za-z]{2,5})-(?P<number>\d+)$")


class CommandError(Exception):
    """A problem to tell the person in plain words."""


def parse(text: str) -> tuple[str, str, str | int] | None:
    """("create", KEY, title) or ("done", KEY, number), or None for bad syntax."""
    text = text.strip()
    if match := _CREATE.match(text):
        return "create", match["key"].upper(), match["title"].strip()
    if match := _DONE.match(text):
        return "done", match["key"].upper(), int(match["number"])
    return None


def _form(webhook: InboundWebhook) -> dict[str, str]:
    return {
        k: v[0]
        for k, v in parse_qs(webhook.raw_payload, keep_blank_values=True).items()
    }


def reply(response_url: str, text: str) -> None:
    """Answer privately (only the person who typed the command sees it)."""
    if not response_url.startswith(constants.RESPONSE_URL_PREFIX):
        logger.warning("Ignoring response_url outside Slack")
        return
    client.webhook_client(response_url).send(text=text, response_type="ephemeral")


def _project_for(user, team_id: str, key: str) -> Membership:
    """The one project that has this key, belongs to this Slack workspace and
    has the user as a member."""
    project_ids = (
        Integration.objects.filter(
            provider=constants.PROVIDER,
            external_workspace_id=team_id,
            project__is_deleted=False,
            project__task_key__iexact=key,
            project__memberships__user=user,
        )
        .exclude(status=IntegrationStatus.DISCONNECTED)
        .values_list("project_id", flat=True)
    )
    projects = list(Project.objects.filter(pk__in=list(project_ids)))
    if not projects:
        raise CommandError(constants.NO_PROJECT.format(key=key))
    if len(projects) > 1:
        names = ", ".join(sorted(p.name for p in projects))
        raise CommandError(constants.AMBIGUOUS_PROJECT.format(key=key, names=names))
    return Membership.objects.select_related("project", "user").get(
        project=projects[0], user=user
    )


def _create(membership: Membership, title: str) -> str:
    if len(title) > fields.TASK_TITLE_MAX_LENGTH:
        raise CommandError(
            constants.TITLE_TOO_LONG.format(limit=fields.TASK_TITLE_MAX_LENGTH)
        )
    task = task_service.create(membership, {"title": title})
    return constants.TASK_CREATED.format(
        key=f"{membership.project.task_key}-{task.number}",
        title=title,
        url=task_url(membership.project.pk, task.number),
    )


def _done(membership: Membership, number: int) -> str:
    key = f"{membership.project.task_key}-{number}"
    try:
        task = tracker_access.get_task(membership, number)
    except AppException:
        raise CommandError(constants.TASK_NOT_FOUND.format(key=key)) from None
    if task.status.category == StatusCategory.DONE:
        return constants.TASK_ALREADY_DONE.format(key=key)
    done = (
        Status.objects.filter(project=membership.project, category=StatusCategory.DONE)
        .order_by("position")
        .first()
    )
    if done is None:
        raise CommandError(constants.NO_DONE_STATUS)
    task_service.update(membership, task, {"status": done.pk})
    return constants.TASK_DONE.format(
        key=key, title=task.title, url=task_url(membership.project.pk, number)
    )


def handle(webhook: InboundWebhook) -> None:
    form = _form(webhook)
    response_url = form.get("response_url", "")
    team_id, slack_user = form.get("team_id", ""), form.get("user_id", "")

    user = linking.find_user(constants.PROVIDER, team_id, slack_user)
    if user is None:
        reply(
            response_url,
            constants.NOT_LINKED.format(
                url=f"{settings.FRONTEND_URL}/settings/integrations"
            ),
        )
        return
    parsed = parse(form.get("text", ""))
    if parsed is None:
        reply(response_url, constants.USAGE)
        return
    action, key, argument = parsed
    try:
        membership = _project_for(user, team_id, key)
        # Changes made here carry source=slack, so they are not posted back.
        with use_source(Source.SLACK):
            message = (
                _create(membership, argument)
                if action == "create"
                else _done(membership, argument)
            )
    except CommandError as exc:
        message = str(exc)
    except AppException as exc:
        message = exc.message
    except Exception:
        logger.exception("Slash command failed")
        message = constants.COMMAND_FAILED
    reply(response_url, message)
