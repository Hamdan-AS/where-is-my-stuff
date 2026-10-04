from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from core import views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("register/", views.register, name="register"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("reports/", views.report_history, name="reports"),
    path("reports/new/", views.wizard, name="create"),
    path("drafts/<int:pk>/", views.wizard, name="draft"),
    path("reports/<int:pk>/", views.report_detail, name="report"),
    path("reports/<int:pk>/edit/", views.edit_report, name="edit"),
    path("reports/<int:pk>/photo/", views.report_photo, name="report-photo"),
    path("drafts/<int:pk>/photo/", views.draft_photo, name="draft-photo"),
    path("matches/<int:pk>/", views.match_detail, name="match"),
    path("labels/", views.qr_labels, name="qr-labels"),
    path("labels/<int:pk>/reactivate/", views.reactivate_qr_label, name="qr-label-reactivate"),
    path("labels/<int:pk>/deactivate/", views.deactivate_qr_label, name="qr-label-deactivate"),
    path("labels/<int:pk>/image/", views.qr_label_image, name="qr-label-image"),
    path("tag/<str:token>/", views.qr_label_public, name="qr-label-public"),
    path("r/<uuid:public_id>/qr/", views.report_qr_image, name="report-qr"),
    path("r/<uuid:public_id>/found/", views.report_found, name="report-found"),
    path("management/", views.management, name="management"),
]
