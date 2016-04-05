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

from patchwork.models import Check, Patch, Project
from patchwork.tests.utils import (
    defaults, create_maintainer, create_user, create_patches, make_msgid)


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


@unittest.skipUnless(settings.ENABLE_REST_API, 'requires ENABLE_REST_API')
class TestPersonAPI(APITestCase):
    fixtures = ['default_states']

    def test_anonymous_list(self):
        """The API should reject anonymous users."""
        resp = self.client.get('/api/1.0/people/')
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_authenticated_list(self):
        """This API requires authenticated users."""
        user = create_user()
        self.client.force_authenticate(user=user)
        resp = self.client.get('/api/1.0/people/')
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(1, resp.data['count'])
        self.assertEqual(user.username, resp.data['results'][0]['name'])
        self.assertEqual(user.email, resp.data['results'][0]['email'])

    def test_readonly(self):
        defaults.project.save()
        user = create_maintainer(defaults.project)
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)

        resp = self.client.delete('/api/1.0/people/1/')
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

        resp = self.client.patch('/api/1.0/people/1/', {'email': 'foo@f.com'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

        resp = self.client.post('/api/1.0/people/', {'email': 'foo@f.com'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)


@unittest.skipUnless(settings.ENABLE_REST_API, 'requires ENABLE_REST_API')
class TestPatchAPI(APITestCase):
    fixtures = ['default_states']

    def test_list_simple(self):
        """Validate we can list a patch."""
        patches = create_patches()
        resp = self.client.get('/api/1.0/patches/')
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(1, resp.data['count'])
        patch = resp.data['results'][0]
        self.assertEqual(patches[0].name, patch['name'])

    def test_get(self):
        """Validate we can get a specific project."""
        patches = create_patches()
        resp = self.client.get('/api/1.0/patches/%d/' % patches[0].id)
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(patches[0].name, resp.data['name'])
        self.assertEqual(patches[0].project.id, resp.data['project'])
        self.assertEqual(patches[0].msgid, resp.data['msgid'])
        self.assertEqual(patches[0].diff, resp.data['diff'])
        self.assertEqual(patches[0].submitter.id, resp.data['submitter'])
        self.assertEqual(patches[0].state.id, resp.data['state'])

    def test_anonymous_writes(self):
        """Ensure anonymous "write" operations are rejected."""
        patches = create_patches()
        patch_url = '/api/1.0/patches/%d/' % patches[0].id
        resp = self.client.get(patch_url)
        patch = resp.data
        patch['msgid'] = 'foo'
        patch['name'] = 'this will should fail'

        # create
        resp = self.client.post('/api/1.0/patches/', patch)
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        # update
        resp = self.client.patch(patch_url, {'name': 'foo'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        # delete
        resp = self.client.delete(patch_url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_create(self):
        """Ensure creations are rejected."""
        create_patches()
        patch = {
            'project': defaults.project.id,
            'submitter': defaults.patch_author_person.id,
            'msgid': make_msgid(),
            'name': 'test-create-patch',
            'diff': 'patch diff',
        }

        user = create_maintainer(defaults.project)
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)
        resp = self.client.post('/api/1.0/patches/', patch)
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_update(self):
        """Ensure updates can be performed maintainers."""
        patches = create_patches()

        # A maintainer can update
        user = create_maintainer(defaults.project)
        self.client.force_authenticate(user=user)
        resp = self.client.patch(
            '/api/1.0/patches/%d/' % patches[0].id, {'state': 2})
        self.assertEqual(status.HTTP_200_OK, resp.status_code)

        # A normal user can't
        user = create_user()
        self.client.force_authenticate(user=user)
        resp = self.client.patch(
            '/api/1.0/patches/%d/' % patches[0].id, {'state': 2})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_delete(self):
        """Ensure deletions are rejected."""
        patches = create_patches()

        user = create_maintainer(defaults.project)
        user.is_superuser = True
        user.save()
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/api/1.0/patches/%d/' % patches[0].id)
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        self.assertEqual(1, Patch.objects.all().count())


@unittest.skipUnless(settings.ENABLE_REST_API, 'requires ENABLE_REST_API')
class TestCheckAPI(APITestCase):
    fixtures = ['default_states']

    def setUp(self):
        super(TestCheckAPI, self).setUp()
        self.patch = create_patches()[0]
        self.urlbase = '/api/1.0/patches/%d/checks/' % self.patch.id
        defaults.project.save()
        self.user = create_maintainer(defaults.project)

    def create_check(self):
        return Check.objects.create(patch=self.patch, user=self.user,
                                    state=Check.STATE_WARNING, target_url='t',
                                    description='d', context='c')

    def test_list_simple(self):
        """Validate we can list checks on a patch."""
        resp = self.client.get(self.urlbase)
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(0, resp.data['count'])

        c = self.create_check()
        resp = self.client.get(self.urlbase)
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(1, resp.data['count'])
        check = resp.data['results'][0]
        self.assertEqual(c.state, check['state'])
        self.assertEqual(c.target_url, check['target_url'])
        self.assertEqual(c.context, check['context'])
        self.assertEqual(c.description, check['description'])

    def test_get(self):
        """Validate we can get a specific check."""
        c = self.create_check()
        resp = self.client.get(self.urlbase + str(c.id) + '/')
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(c.target_url, resp.data['target_url'])

        # and we can get the combined check status
        resp = self.client.get('/api/1.0/patches/%d/check/' % self.patch.id)
        self.assertEqual(status.HTTP_200_OK, resp.status_code)
        self.assertEqual(c.state, resp.data['state'])

    def test_update_delete(self):
        """Ensure updates and deletes aren't allowed"""
        c = self.create_check()

        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

        # update
        resp = self.client.patch(
            self.urlbase + str(c.id) + '/', {'target_url': 'fail'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
        # delete
        resp = self.client.delete(self.urlbase + str(c.id) + '/')
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)

    def test_create(self):
        """Ensure creations can be performed by user of patch."""
        check = {
            'state': Check.STATE_SUCCESS,
            'target_url': 'http://t.co',
            'description': 'description',
            'context': 'context',
        }

        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.urlbase, check)
        self.assertEqual(status.HTTP_201_CREATED, resp.status_code)
        self.assertEqual(1, Check.objects.all().count())

        user = create_user()
        self.client.force_authenticate(user=user)
        resp = self.client.post(self.urlbase, check)
        self.assertEqual(status.HTTP_403_FORBIDDEN, resp.status_code)
