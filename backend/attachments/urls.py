from django.urls import path

from attachments.views import attachment

P = "projects/<uuid:project_id>"

urlpatterns = [
    path(f"{P}/attachments/", attachment.AttachmentListView.as_view()),
    path(f"{P}/attachments/upload-url/", attachment.UploadUrlView.as_view()),
    path(
        f"{P}/attachments/<uuid:attachment_id>/",
        attachment.AttachmentDetailView.as_view(),
    ),
    path(
        f"{P}/attachments/<uuid:attachment_id>/confirm/",
        attachment.AttachmentConfirmView.as_view(),
    ),
    path(
        f"{P}/attachments/<uuid:attachment_id>/download/",
        attachment.AttachmentDownloadView.as_view(),
    ),
    path(f"{P}/storage/", attachment.ProjectStorageView.as_view()),
    path("me/storage/", attachment.MyStorageView.as_view()),
]
