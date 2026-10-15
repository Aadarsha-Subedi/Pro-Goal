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
from tracker.responses import NoteData, NoteRevisionData
from tracker.serializers.note import (
    NoteCreateSerializer,
    NoteQuerySerializer,
    NoteUpdateSerializer,
)
from tracker.services import access, note_service
from tracker.views.base import ip_of, paginated


def _fresh(membership, note_id) -> NoteData:
    note = note_service.list_notes(membership).get(pk=note_id)
    return NoteData(note)


class NoteListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID) -> BaseResponse:
        query = NoteQuerySerializer.parse(request.query_params.dict())
        membership = project_access.get_membership(request.user, project_id)
        queryset = note_service.list_notes(
            membership, q=query.get("q"), tag=query.get("tag")
        )
        return paginated(request, queryset, lambda n: NoteData(n, detail=False))

    def post(self, request: Request, project_id: UUID) -> BaseResponse:
        data = NoteCreateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        note = note_service.create(membership, ip=ip_of(request), **data)
        return ResourceCreatedResponse(
            data=_fresh(membership, note.pk), message=messages.NOTE_CREATED
        )


class NoteDetailView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, note_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        access.get_note(membership, note_id)
        return SuccessResponse(data=_fresh(membership, note_id))

    def patch(self, request: Request, project_id: UUID, note_id: UUID) -> BaseResponse:
        data = NoteUpdateSerializer.parse(request.data)
        membership = project_access.get_membership(request.user, project_id)
        note_service.update(membership, note_id, data, ip_of(request))
        return ResourceUpdatedResponse(
            data=_fresh(membership, note_id), message=messages.NOTE_UPDATED
        )

    def delete(self, request: Request, project_id: UUID, note_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        note_service.delete(membership, note_id, ip_of(request))
        return SuccessResponse(message=messages.NOTE_DELETED)


class NoteRevisionListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, note_id: UUID) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        return paginated(
            request, note_service.revisions(membership, note_id), NoteRevisionData
        )


class TaskNoteListView(CsrfProtectedView):
    def get(self, request: Request, project_id: UUID, number: int) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        return paginated(
            request,
            note_service.notes_for_task(task),
            lambda n: NoteData(n, detail=False),
        )


class TaskNoteLinkView(CsrfProtectedView):
    def put(
        self, request: Request, project_id: UUID, number: int, note_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        note_service.link(membership, task, note_id, ip_of(request))
        return SuccessResponse(
            data=_fresh(membership, note_id), message=messages.NOTE_LINKED
        )

    def delete(
        self, request: Request, project_id: UUID, number: int, note_id: UUID
    ) -> BaseResponse:
        membership = project_access.get_membership(request.user, project_id)
        task = access.get_task(membership, number)
        note_service.unlink(membership, task, note_id, ip_of(request))
        return SuccessResponse(message=messages.NOTE_UNLINKED)
