from uuid import UUID

from rest_framework.request import Request

from accounts.views.base import CsrfProtectedView
from common.response.domain import (
    BaseResponse,
    ResourceCreatedResponse,
    ResourceUpdatedResponse,
    SuccessResponse,
)
from projects.services import access as project_access
from tracker.constants import messages
from tracker.responses import TaskData
from tracker.serializers.task import (
    TaskCreateSerializer,
    TaskListQuerySerializer,
    TaskUpdateSerializer,
)
from tracker.services import access, query, task_service
from tracker.views.base import ip_of, paginated, server_meta


def _list(request: Request, queryset) -> BaseResponse:
    return paginated(
        request, queryset, lambda t: TaskData(t, detail=False), server_meta()
    )


def _fresh(membership, number: int, **kwargs) -> TaskData:
    """Reload with the list prefetches so the response matches the list shape."""
    return TaskData(
        query.base_queryset(project=membership.project, number=number).get()
    )


class TaskListView(CsrfProtectedView):
    query_serializers = {"get": TaskListQuerySerializer}

    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return _list(request, query.project_tasks(membership, request.query_params))

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = TaskCreateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        task = task_service.create(membership, data, ip=ip_of(request))
        return ResourceCreatedResponse(
            data=_fresh(membership, task.number), message=messages.TASK_CREATED
        )


class TaskDetailView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        return SuccessResponse(data=_fresh(membership, task.number), meta=server_meta())

    def patch(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        data = TaskUpdateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        task_service.update(membership, task, data, ip_of(request))
        return ResourceUpdatedResponse(
            data=_fresh(membership, number), message=messages.TASK_UPDATED
        )

    def delete(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        task = task_service.delete(membership, task)
        return SuccessResponse(
            data=TaskData(task, detail=False), message=messages.TASK_DELETED
        )


class TaskRestoreView(CsrfProtectedView):
    def post(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number, allow_deleted=True)
        task_service.restore(membership, task, ip_of(request))
        return SuccessResponse(
            data=_fresh(membership, number), message=messages.TASK_RESTORED
        )


class SubtaskListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        parent = access.get_task(membership, number)
        return _list(request, query.subtasks_of(parent))

    def post(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        data = TaskCreateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        parent = access.get_task(membership, number)
        task = task_service.create(
            membership, data, parent_number=parent.number, ip=ip_of(request)
        )
        return ResourceCreatedResponse(
            data=_fresh(membership, task.number), message=messages.SUBTASK_CREATED
        )


class MyTasksView(CsrfProtectedView):
    query_serializers = {"get": TaskListQuerySerializer}

    def get(self, request: Request) -> BaseResponse:
        return _list(request, query.my_tasks(request.user, request.query_params))
