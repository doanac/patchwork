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

import unittest

from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase

from patchwork.models import Project
from patchwork.tests.utils import defaults, create_maintainer, create_user


@unittest.skipUnless(settings.ENABLE_REST_API, 'requires ENABLE_REST_API')
class TestProjectAPI(APITestCase):
    fixtures = ['default_states']

    def test_list_simple(self):
        """Validate we can list the default test project."""
        defaults.project.save()
        resp = self.client.get('/api/1.0/projects/')
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(1, resp.data['count'])
        proj = resp.data['results'][0]
        self.assertEqual(defaults.project.linkname, proj['linkname'])
        self.assertEqual(defaults.project.name, proj['name'])
        self.assertEqual(defaults.project.listid, proj['listid'])

    def test_get(self):
        """Validate we can get a specific project."""
        defaults.project.save()
        resp = self.client.get('/api/1.0/projects/1/')
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(defaults.project.name, resp.data['name'])

    def test_anonymous_writes(self):
        """Ensure anonymous "write" operations are rejected."""
        defaults.project.save()
        # create
        resp = self.client.post(
            '/api/1.0/projects/',
            {'linkname': 'l', 'name': 'n', 'listid': 'l', 'listemail': 'e'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        # update
        resp = self.client.patch('/api/1.0/projects/1/', {'linkname': 'foo'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        # delete
        resp = self.client.delete('/api/1.0/projects/1/')
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_create(self):
        """Ensure creations are rejected."""
        defaults.project.save()

        user = create_maintainer(defaults.project)
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)
        resp = self.client.post(
            '/api/1.0/projects/',
            {'linkname': 'l', 'name': 'n', 'listid': 'l', 'listemail': 'e'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_update(self):
        """Ensure updates can be performed maintainers."""
        defaults.project.save()

        # A maintainer can update
        user = create_maintainer(defaults.project)
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/api/1.0/projects/1/', {'linkname': 'TEST'})
        self.assertEqual(status.HTTP_200_OK, resp.status_code)

        # A normal user can't
        user = create_user()
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/api/1.0/projects/1/', {'linkname': 'TEST'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_delete(self):
        """Ensure deletions are rejected."""
        defaults.project.save()

        # Even an admin can't remove a project
        user = create_maintainer(defaults.project)
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/api/1.0/projects/1/')
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        self.assertEqual(1, Project.objects.all().count())
