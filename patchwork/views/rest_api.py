# Patchwork - automated patch tracking system
# Copyright (C) 2016 Linaro Corporation
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from django.conf.urls import url, include

from patchwork.models import Project

from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet


class PageSizePagination(PageNumberPagination):
    """Overide base class to enable the "page_size" query parameter."""
    page_size = 30
    page_size_query_param = 'page_size'


class PatchworkPermission(permissions.BasePermission):
    """This permission works for Project and Patch model objects"""
    def has_permission(self, request, view):
        if request.method in ('POST', 'DELETE'):
            return False
        return super(PatchworkPermission, self).has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # read only for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.is_editable(request.user)


class ProjectSerializer(ModelSerializer):
    class Meta:
        model = Project


class ProjectViewSet(ModelViewSet):
    permission_classes = (PatchworkPermission,)
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    pagination_class = PageSizePagination


router = DefaultRouter()
router.register('projects', ProjectViewSet, 'project')

urlpatterns = [
    url(r'^api/1.0/', include(router.urls)),
]
