from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
admin.site.register(User, UserAdmin)
# Reports and private answers are deliberately absent from the generic admin.
# Moderation uses the restricted management view and audited service methods.

