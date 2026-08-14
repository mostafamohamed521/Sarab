from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Read (GET/HEAD/OPTIONS) is allowed for anyone the view's queryset
    already permits. Write operations (PATCH/PUT/DELETE) on a specific
    object are only allowed to the object's own `user`."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'user_id', None) == request.user.id
