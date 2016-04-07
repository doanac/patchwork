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

from patchwork.models import Check, Patch, Person, Project
from patchwork.views.patch import mbox

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import (
    CurrentUserDefault, HiddenField, ModelSerializer, PrimaryKeyRelatedField)
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from rest_framework_nested.routers import NestedSimpleRouter


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


class AuthenticatedReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        authenticated = request.user.is_authenticated()
        return authenticated and request.method in permissions.SAFE_METHODS


class PatchworkViewSet(ModelViewSet):
    pagination_class = PageSizePagination

    # a dict of the request-query-param -> django ORM query parameter
    query_filters = {}

    def get_queryset(self):
        qs = self.serializer_class.Meta.model.objects.all()
        filters = {}
        for param, val in self.request.query_params.items():
            name = self.query_filters.get(param)
            if name:
                filters[name] = val
        return qs.filter(**filters)

    def options(self, request, *args, **kwargs):
        # add our query filters to make the "options" command a little more
        # helpful.
        resp = super(PatchworkViewSet, self).options(request, *args, **kwargs)
        if self.query_filters:
            resp.data['query_filters'] = self.query_filters.keys()
        return resp


def create_model_serializer(model_class, read_only=None):
    class PatchworkSerializer(ModelSerializer):
        class Meta:
            model = model_class
            read_only_fields = read_only
    return PatchworkSerializer


class PatchViewSet(PatchworkViewSet):
    """Listings support the following query filters:
        * project=<project-name>
        * since=<YYYY-MM-DDTHH:MM:SS.mm>
        * until=<YYYY-MM-DDTHH:MM:SS.mm>
        * state=<state-name>
        * submitter=<name>
        * delegate=<name>

       eg: GET /api/1.0/patches/?project=p&since=2016-01-01&submitter=User+Name
    """
    permission_classes = (PatchworkPermission,)
    serializer_class = create_model_serializer(
        Patch, ('project', 'name', 'date', 'submitter', 'diff', 'content',
                'hash', 'msgid'))

    query_filters = {
        'project': 'project__name',
        'submitter': 'submitter__name',
        'delegate': 'delegate__name',
        'state': 'state__name',
        'since': 'date__gt',
        'until': 'date__lt',
    }


class PeopleViewSet(PatchworkViewSet):
    permission_classes = (AuthenticatedReadOnly,)
    serializer_class = create_model_serializer(Person)


class ProjectViewSet(PatchworkViewSet):
    permission_classes = (PatchworkPermission,)
    serializer_class = create_model_serializer(Project)


class CurrentPatchDefault(object):
    def set_context(self, serializer_field):
        self.patch = serializer_field.context['request'].patch

    def __call__(self):
        return self.patch


class ChecksSerializer(ModelSerializer):
    class Meta:
        model = Check
    user = PrimaryKeyRelatedField(read_only=True, default=CurrentUserDefault())
    patch = HiddenField(default=CurrentPatchDefault())


class ChecksViewSet(PatchworkViewSet):
    serializer_class = ChecksSerializer

    def not_allowed(self, request, **kwargs):
        raise PermissionDenied()

    update = not_allowed
    partial_update = not_allowed
    destroy = not_allowed

    def create(self, request, patch_pk):
        p = Patch.objects.get(id=patch_pk)
        if not p.is_editable(request.user):
            raise PermissionDenied()
        request.patch = p
        return super(ChecksViewSet, self).create(request)

    def list(self, request, patch_pk):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(patch=patch_pk)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CheckViewSet(GenericViewSet):
    def list(self, request, patch_pk):
        state = Patch.objects.get(id=patch_pk).combined_check_state
        return Response({'state': state})


class MboxViewSet(GenericViewSet):
    def list(self, request, patch_pk):
        return mbox(request, patch_pk)


router = DefaultRouter()
router.register('patches', PatchViewSet, 'patch')
router.register('people', PeopleViewSet, 'person')
router.register('projects', ProjectViewSet, 'project')

patches_router = NestedSimpleRouter(router, r'patches', lookup='patch')
patches_router.register(r'checks', ChecksViewSet, base_name='patch-checks')
patches_router.register(r'check', CheckViewSet, base_name='patch-check')
patches_router.register(r'mbox', MboxViewSet, base_name='patch-mbox')

urlpatterns = [
    url(r'^api/1.0/', include(router.urls)),
    url(r'^api/1.0/', include(patches_router.urls)),
]
