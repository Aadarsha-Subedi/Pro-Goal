from django.urls import path

from projects.views import activity, explore, member, permission, project, transfer

urlpatterns = [
    # Projects
    path("projects/", project.ProjectListView.as_view()),
    path("projects/join/", member.JoinView.as_view()),
    path("projects/<uuid:project_id>/", project.ProjectDetailView.as_view()),
    path("projects/<uuid:project_id>/archive/", project.ProjectArchiveView.as_view()),
    path(
        "projects/<uuid:project_id>/unarchive/", project.ProjectUnarchiveView.as_view()
    ),
    path("projects/<uuid:project_id>/restore/", project.ProjectRestoreView.as_view()),
    path("projects/<uuid:project_id>/copy/", project.ProjectCopyView.as_view()),
    path(
        "projects/<uuid:project_id>/join-code/regenerate/",
        project.JoinCodeRegenerateView.as_view(),
    ),
    # Members
    path("projects/<uuid:project_id>/members/", member.MemberListView.as_view()),
    path(
        "projects/<uuid:project_id>/members/<uuid:user_id>/",
        member.MemberDetailView.as_view(),
    ),
    path(
        "projects/<uuid:project_id>/members/<uuid:user_id>/permissions/",
        permission.MemberPermissionsView.as_view(),
    ),
    path("projects/<uuid:project_id>/activity/", activity.ActivityListView.as_view()),
    path("explore/", explore.ExploreListView.as_view()),
    path("explore/tags/", explore.ExploreTagView.as_view()),
    path("explore/<uuid:project_id>/join-request/", explore.ExploreJoinView.as_view()),
    path("permissions/", permission.PermissionRegistryView.as_view()),
    path("projects/<uuid:project_id>/leave/", member.LeaveProjectView.as_view()),
    # Join requests
    path(
        "projects/<uuid:project_id>/join-requests/",
        member.JoinRequestListView.as_view(),
    ),
    path(
        "projects/<uuid:project_id>/join-requests/<uuid:request_id>/approve/",
        member.JoinRequestApproveView.as_view(),
    ),
    path(
        "projects/<uuid:project_id>/join-requests/<uuid:request_id>/reject/",
        member.JoinRequestRejectView.as_view(),
    ),
    # Ownership transfer
    path(
        "projects/<uuid:project_id>/transfer/", transfer.ProjectTransferView.as_view()
    ),
    path(
        "projects/<uuid:project_id>/transfer/cancel/",
        transfer.ProjectTransferCancelView.as_view(),
    ),
    path("transfers/", transfer.IncomingTransferListView.as_view()),
    path("transfers/<uuid:transfer_id>/accept/", transfer.TransferAcceptView.as_view()),
]
