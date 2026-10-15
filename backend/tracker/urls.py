from django.urls import path

from tracker.views import comment, note, task, workflow

P = "projects/<uuid:project_id>"

urlpatterns = [
    # Statuses and priorities
    path(f"{P}/statuses/", workflow.StatusListView.as_view()),
    path(f"{P}/statuses/<uuid:status_id>/", workflow.StatusDetailView.as_view()),
    path(f"{P}/priorities/", workflow.PriorityListView.as_view()),
    path(f"{P}/priorities/<uuid:priority_id>/", workflow.PriorityDetailView.as_view()),
    # Tasks and subtasks
    path(f"{P}/tasks/", task.TaskListView.as_view()),
    path(f"{P}/tasks/<int:number>/", task.TaskDetailView.as_view()),
    path(f"{P}/tasks/<int:number>/restore/", task.TaskRestoreView.as_view()),
    path(f"{P}/tasks/<int:number>/subtasks/", task.SubtaskListView.as_view()),
    # Comments
    path(f"{P}/tasks/<int:number>/comments/", comment.CommentListView.as_view()),
    path(
        f"{P}/tasks/<int:number>/comments/<uuid:comment_id>/",
        comment.CommentDetailView.as_view(),
    ),
    # Notes
    path(f"{P}/notes/", note.NoteListView.as_view()),
    path(f"{P}/notes/<uuid:note_id>/", note.NoteDetailView.as_view()),
    path(f"{P}/notes/<uuid:note_id>/revisions/", note.NoteRevisionListView.as_view()),
    path(f"{P}/tasks/<int:number>/notes/", note.TaskNoteListView.as_view()),
    path(
        f"{P}/tasks/<int:number>/notes/<uuid:note_id>/",
        note.TaskNoteLinkView.as_view(),
    ),
    # Board preference and the caller's tasks
    path(f"{P}/kanban-preference/", comment.KanbanPreferenceView.as_view()),
    path("me/tasks/", task.MyTasksView.as_view()),
]
