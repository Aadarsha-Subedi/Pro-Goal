"""Choices and seeded defaults for statuses, priorities and kanban."""

from django.db import models


class StatusCategory(models.TextChoices):
    TODO = "todo", "To do"
    IN_PROGRESS = "in_progress", "In progress"
    DONE = "done", "Done"


class GroupBy(models.TextChoices):
    STATUS = "status"
    PRIORITY = "priority"
    ASSIGNEE = "assignee"
    TAG = "tag"


class SortBy(models.TextChoices):
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    NUMBER = "number"
    TITLE = "title"


DEFAULT_GROUP_BY = GroupBy.STATUS
DEFAULT_SORT_BY = SortBy.NUMBER

# (name, category, is_default) in board order.
DEFAULT_STATUSES = (
    ("To do", StatusCategory.TODO, True),
    ("In progress", StatusCategory.IN_PROGRESS, False),
    ("In review", StatusCategory.IN_PROGRESS, False),
    ("Done", StatusCategory.DONE, False),
    ("Cancelled", StatusCategory.DONE, False),
)
# (name, is_default); rank follows the order, 1 = lowest.
DEFAULT_PRIORITIES = (
    ("Low", False),
    ("Medium", True),
    ("High", False),
    ("Urgent", False),
)
