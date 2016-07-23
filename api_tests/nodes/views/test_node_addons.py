# -*- coding: utf-8 -*-
import abc
import mock
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from website.util.permissions import READ, WRITE, ADMIN

from tests.base import ApiAddonTestCase
from tests.factories import AuthUserFactory
from website.addons.box.tests.factories import BoxAccountFactory, BoxNodeSettingsFactory
from website.addons.dataverse.tests.factories import DataverseAccountFactory, DataverseNodeSettingsFactory
from website.addons.dropbox.tests.factories import DropboxAccountFactory, DropboxNodeSettingsFactory
from website.addons.github.tests.factories import GitHubAccountFactory, GitHubNodeSettingsFactory
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory, GoogleDriveNodeSettingsFactory
from website.addons.mendeley.tests.factories import MendeleyAccountFactory, MendeleyNodeSettingsFactory
from website.addons.s3.tests.factories import S3AccountFactory, S3NodeSettingsFactory
from website.addons.zotero.tests.factories import ZoteroAccountFactory, ZoteroNodeSettingsFactory

# Varies between addons. Some need to make a call to get the root,
# 'FAKEROOTID' should be the result of a mocked call in that case.
VALID_ROOT_FOLDER_IDS = (
    '/',
    '0',
    'FAKEROOTID',
)

class NodeAddonListMixin(object):
    def set_setting_list_url(self):
        self.setting_list_url = '/{}nodes/{}/addons/?page[size]=100'.format(
            API_BASE, self.node._id
        )

    def get_response_for_addon(self, response):
        for datum in response.json['data']:
            if datum['id'] == self.short_name:
                return datum['attributes']
        return None

    def test_settings_list_GET_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth)

        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert_equal(self.account_id, addon_data['external_account_id'])
            assert_equal(self.node_settings.has_auth, addon_data['node_has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder_id'])
        if wrong_type:
            assert_equal(addon_data, None)

    def test_settings_list_GET_disabled(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth,
            expect_errors=wrong_type)
        addon_data = self.get_response_for_addon(res)
        assert_equal(addon_data, None)

    def test_settings_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(self.setting_list_url, {
            'id': self.short_name,
            'type': 'node-addons'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(self.setting_list_url, {
            'id': self.short_name,
            'type': 'node-addons'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_list_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.setting_list_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_list_raises_error_if_noncontrib_not_public(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_settings_list_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        wrong_type = self.should_expect_errors()
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth)
        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert_equal(self.account_id, addon_data['external_account_id'])
            assert_equal(self.node_settings.has_auth, addon_data['node_has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder_id'])
        if wrong_type:
            assert_equal(addon_data, None)

class NodeAddonDetailMixin(object):
    def set_setting_detail_url(self):
        self.setting_detail_url = '/{}nodes/{}/addons/{}/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_settings_detail_GET_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(self.account_id, addon_data['external_account_id'])
            assert_equal(self.node_settings.has_auth, addon_data['node_has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder_id'])
        if wrong_type:
            assert_equal(res.status_code, 404)

    def test_settings_detail_GET_disabled(self):
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_settings_detail_PUT_all_sets_settings(self):
        wrong_type = self.should_expect_errors(success_types=('CONFIGURABLE', ))
        try:
            self.node_settings.deauthorize(auth=self.auth)
            self.node_settings.save()
        except (ValueError, AttributeError):
            # If addon was mandatory or non-configurable -- OSFStorage, Wiki
            pass
        data = {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': self.account_id,
                    }
                }
            }
        data['data']['attributes'].update(self._mock_folder_info)
        res = self.app.put_json_api(self.setting_detail_url, 
            data, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['external_account_id'], self.account_id)
            assert_equal(addon_data['folder_id'], '0987654321')
            assert_true(addon_data['node_has_auth'])
        if wrong_type:
            assert_in(res.status_code, [404, 501])


    def test_settings_detail_PUT_none_and_enabled_clears_settings(self):
        wrong_type = self.should_expect_errors(success_types=('CONFIGURABLE', ))
        res = self.app.put_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    'folder_id': None
                    }
                }
            }, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['external_account_id'], None)
            assert_equal(addon_data['folder_id'], None)
            assert_false(addon_data['node_has_auth'])
        if wrong_type:
            assert_in(res.status_code, [404, 501])

    def test_settings_detail_PUT_none_and_disabled_deauthorizes(self):
        wrong_type = self.should_expect_errors(success_types=('CONFIGURABLE', ))
        res = self.app.put_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    'folder_id': None
                    }
                }
            }, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['external_account_id'], None)
            assert_equal(addon_data['folder_id'], None)
            assert_false(addon_data['node_has_auth'])
        if wrong_type:
            assert_in(res.status_code, [404, 501])

    def test_settings_detail_DELETE_disables(self):
        wrong_type = self.should_expect_errors()
        res = self.app.delete(self.setting_detail_url, 
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            assert_equal(res.status_code, 204)
        if wrong_type:
            assert_in(res.status_code, [404, 405])

    def test_settings_detail_POST_enables(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.post_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    }
                }
            },
            auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['external_account_id'], None)
            assert_equal(addon_data['folder_id'], None)
            assert_false(addon_data['node_has_auth'])
        if wrong_type:
            assert_in(res.status_code, [404, 405])

    def test_settings_detail_PATCH_to_enable_and_add_external_account_id(self):
        wrong_type = self.should_expect_errors(success_types=('CONFIGURABLE', ))
        try:
            self.node_settings.deauthorize(auth=self.auth)
            self.node_settings.save()
        except (ValueError, AttributeError):
            # If addon was mandatory or non-configurable -- OSFStorage, Wiki
            pass
        res = self.app.patch_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': self.account_id,
                    }
                }
            }, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['external_account_id'], self.account_id)
            assert_equal(addon_data['folder_id'], None)
            assert_true(addon_data['node_has_auth'])
        if wrong_type:
            assert_in(res.status_code, [404, 501])

    def test_settings_detail_PATCH_to_remove_external_account_id(self):
        wrong_type = self.should_expect_errors(success_types=('CONFIGURABLE', ))
        res = self.app.patch_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    }
                }
            }, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['external_account_id'], None)
            assert_equal(addon_data['folder_id'], None)
            assert_false(addon_data['node_has_auth'])
        if wrong_type:
            assert_in(res.status_code, [404, 501])

    def test_settings_detail_PATCH_to_add_folder_without_auth_conflict(self):
        wrong_type = self.should_expect_errors(success_types=('CONFIGURABLE', ))
        try:
            self.node_settings.deauthorize(self.auth)
            self.node_settings.save()
        except (ValueError, AttributeError):
            # If addon was mandatory or non-configurable -- OSFStorage, Wiki
            pass

        data = {'data': { 
            'id': self.short_name,
            'type': 'node_addons',
            'attributes': {
                }
            }
        }
        data['data']['attributes'].update(self._mock_folder_info)
        res = self.app.patch_json_api(self.setting_detail_url, 
            data, auth=self.user.auth,
            expect_errors=True)
        if not wrong_type:
            assert_equal(res.status_code, 409)
            assert_equal('Cannot set folder without authorization',
                         res.json['errors'][0]['detail'])
        if wrong_type:
            assert_in(res.status_code, [404, 501])

    def test_settings_detail_PATCH_readcontrib_raises_error(self):
        read_user = AuthUserFactory()
        self.node.add_contributor(read_user, permissions=[READ], auth=self.auth)
        res = self.app.patch_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    }
                }
            }, auth=read_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_settings_detail_DELETE_success(self):
        wrong_type = self.should_expect_errors()
        res = self.app.delete(self.setting_detail_url, 
            auth=self.user.auth,
            expect_errors=True)
        if not wrong_type:
            assert_equal(res.status_code, 204)
        else:
            assert_equal(res.status_code, 404)

    def test_settings_detail_raises_error_if_DELETE_not_enabled(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.delete(self.setting_detail_url, 
            auth=self.user.auth,
            expect_errors=True)
        # if not wrong_type:
        assert_equal(res.status_code, 404)
        # else:
            # assert_equal(res.status_code, 405)

    def test_settings_detail_raises_error_if_POST_already_configured(self):
        wrong_type = self.should_expect_errors()
        res = self.app.post_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    }
                }
            }, auth=self.user.auth,
            expect_errors=True)
        if not wrong_type:
            assert_equal(res.status_code, 400)
            assert_in('already enabled', res.body)
        else:
            assert_equal(res.status_code, 404)

    def test_settings_detail_raises_error_if_noncontrib_not_public_GET(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_detail_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_settings_detail_raises_error_if_noncontrib_not_public_PUT(self):
        noncontrib = AuthUserFactory()
        res = self.app.put_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None,
                    'folder_id': None,
                    }
                }
            }, auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_settings_detail_raises_error_if_noncontrib_not_public_PATCH(self):
        noncontrib = AuthUserFactory()
        res = self.app.patch_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None
                    }
                }
            }, auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_settings_detail_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        noncontrib = AuthUserFactory()
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_detail_url,
            auth=noncontrib.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            assert_equal(res.status_code, 200)
            addon_data = res.json['data']['attributes']
            assert_equal(self.account_id, addon_data['external_account_id'])
            assert_equal(self.node_settings.has_auth, addon_data['node_has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder_id'])
        if wrong_type:
            assert_equal(res.status_code, 404)

    def test_settings_detail_noncontrib_public_cannot_edit(self):
        self.node.set_privacy('public', auth=self.auth)
        noncontrib = AuthUserFactory()
        res = self.app.patch_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': None
                    }
                }
            }, auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)


class NodeAddonFolderMixin(object):
    def set_folder_url(self):
        self.folder_url = '/{}nodes/{}/addons/{}/folders/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_folder_list_GET_expected_behavior(self):
        wrong_type = self.short_name not in ('googledrive', 'box', 'dropbox', )
        res = self.app.get(
            self.folder_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data'][0]['attributes']
            assert_equal(addon_data['kind'], 'folder')
            assert '/ (Full ' in addon_data['name']
            assert_equal(addon_data['path'], '/')
            assert addon_data['folder_id'] in VALID_ROOT_FOLDER_IDS
        if wrong_type:
            assert_in(res.status_code, [404, 501])


    def test_folder_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(self.folder_url, {
            'id': self.short_name,
            'type': 'node-addon-folders'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_folder_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(self.folder_url, {
            'id': self.short_name,
            'type': 'node-addon-folders'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_folder_list_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.folder_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_folder_list_GET_raises_error_noncontrib_not_public(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.folder_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_folder_list_GET_raises_error_writecontrib_not_authorizer(self):
        write_user = AuthUserFactory()
        self.node.add_contributor(write_user, permissions=[WRITE], auth=self.auth)
        res = self.app.get(self.folder_url, 
            auth=write_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_folder_list_GET_raises_error_admin_not_authorizer(self):
        admin_user = AuthUserFactory()
        self.node.add_contributor(admin_user, permissions=[ADMIN], auth=self.auth)
        res = self.app.get(self.folder_url, 
            auth=admin_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)


class NodeAddonTestSuiteMixin(NodeAddonListMixin, NodeAddonDetailMixin, NodeAddonFolderMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_folder_url()

    def should_expect_errors(self, success_types=('CONFIGURABLE', 'OAUTH')):
        return self.addon_type not in success_types

    @property
    def _mock_folder_info(self):
        return {'folder_id': '0987654321'}


class NodeOAuthAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'OAUTH'

    @abc.abstractproperty
    def AccountFactory(self):
        pass

    @abc.abstractproperty
    def NodeSettingsFactory(self):
        pass

    def _apply_auth_configuration(self, *args, **kwargs):
        settings = self._settings_kwargs(self.node, self.user_settings)
        for key in settings:
            setattr(self.node_settings, key, settings[key])
        self.node_settings.external_account = self.account
        self.node_settings.save()


class NodeConfigurableAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    addon_type = 'CONFIGURABLE'


class NodeOAuthCitationAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'list_id': 'fake_folder_id',
            'owner': self.node
        }

    def test_settings_list_noncontrib_public_can_view(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super(NodeOAuthCitationAddonTestSuiteMixin, self).test_settings_list_noncontrib_public_can_view

    def test_settings_list_GET_enabled(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super(NodeOAuthCitationAddonTestSuiteMixin, self).test_settings_list_GET_enabled

    def test_settings_detail_noncontrib_public_can_view(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super(NodeOAuthCitationAddonTestSuiteMixin, self).test_settings_detail_noncontrib_public_can_view

    def test_settings_detail_GET_enabled(self):
        with mock.patch.object(self.node_settings.__class__, '_fetch_folder_name', return_value='fake_folder'):
            super(NodeOAuthCitationAddonTestSuiteMixin, self).test_settings_detail_GET_enabled



class NodeUnmanageableAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'UNMANAGEABLE'


class TestNodeInvalidAddon(NodeAddonTestSuiteMixin, ApiAddonTestCase):
    addon_type = 'INVALID'
    short_name = 'fake'


# UNMANAGEABLE


class TestNodeForwardAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'forward'


class TestNodeOsfStorageAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'osfstorage'


class TestNodeTwoFactorAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'twofactor'


class TestNodeWikiAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'wiki'


class TestNodeFigshareAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'figshare'


# OAUTH


class TestNodeDataverseAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dataverse'
    AccountFactory = DataverseAccountFactory
    NodeSettingsFactory = DataverseNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            '_dataset_id': '1234567890',
            'owner': self.node
        }


class TestNodeGitHubAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'github'
    AccountFactory = GitHubAccountFactory
    NodeSettingsFactory = GitHubNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }


class TestNodeMendeleyAddon(NodeOAuthCitationAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'mendeley'
    AccountFactory = MendeleyAccountFactory
    NodeSettingsFactory = MendeleyNodeSettingsFactory


class TestNodeZoteroAddon(NodeOAuthCitationAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'zotero'
    AccountFactory = ZoteroAccountFactory
    NodeSettingsFactory = ZoteroNodeSettingsFactory

# CONFIGURABLE


class TestNodeBoxAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory
    NodeSettingsFactory = BoxNodeSettingsFactory

    @mock.patch('website.addons.box.model.BoxClient.get_folder')
    def test_settings_detail_PUT_all_sets_settings(self, mock_get):
        mock_get.return_value = {
            'id': self._mock_folder_info['folder_id'],
            'name': 'FAKEFOLDERNAME',
            'path_collection': {'entries': {}}
        }
        with mock.patch('website.addons.box.model.Box.refresh_oauth_key') as mock_update:
            super(TestNodeBoxAddon, self).test_settings_detail_PUT_all_sets_settings()


class TestNodeDropboxAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dropbox'
    AccountFactory = DropboxAccountFactory
    NodeSettingsFactory = DropboxNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }


class TestNodeS3Addon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 's3'
    AccountFactory = S3AccountFactory
    NodeSettingsFactory = S3NodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'owner': self.node
        }


class TestNodeGoogleDriveAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'googledrive'
    AccountFactory = GoogleDriveAccountFactory
    NodeSettingsFactory = GoogleDriveNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'folder_id': '1234567890',
            'folder_path': '/1234567890'
        }

    @property
    def _mock_folder_info(self):
        return {
            'folder_id': '0987654321',
            'folder_path': '/'
        }

    @mock.patch('website.addons.googledrive.client.GoogleDriveClient.about')
    def test_folder_list_GET_expected_behavior(self, mock_about):
        mock_about.return_value = {'rootFolderId': 'FAKEROOTID'}
        with mock.patch.object(self.node_settings.__class__, 'fetch_access_token', return_value='asdfghjkl') as mock_fetch:
            super(TestNodeGoogleDriveAddon, self).test_folder_list_GET_expected_behavior()

    def test_settings_detail_PUT_PATCH_only_folder_id_raises_error(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        data = {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'folder_id': self._mock_folder_info['folder_id']
                    }
                }
            }
        res_put = self.app.put_json_api(self.setting_detail_url, 
            data, auth=self.user.auth, expect_errors=True)
        res_patch = self.app.patch_json_api(self.setting_detail_url,
            data, auth=self.user.auth, expect_errors=True)

        assert res_put.status_code == res_patch.status_code == 400
        assert ('Must specify both folder_id and folder_path for {}'.format(self.short_name) ==
             res_put.json['errors'][0]['detail'] == res_patch.json['errors'][0]['detail'])

    def test_settings_detail_PUT_PATCH_only_folder_path_raises_error(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        data = {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'folder_path': self._mock_folder_info['folder_path']
                    }
                }
            }
        res_put = self.app.put_json_api(self.setting_detail_url, 
            data, auth=self.user.auth, expect_errors=True)
        res_patch = self.app.patch_json_api(self.setting_detail_url,
            data, auth=self.user.auth, expect_errors=True)

        assert res_put.status_code == res_patch.status_code == 400
        assert ('Must specify both folder_id and folder_path for {}'.format(self.short_name) ==
             res_put.json['errors'][0]['detail'] == res_patch.json['errors'][0]['detail'])

    def test_settings_detail_incomplete_PUT_raises_error(self):
        self.node_settings.deauthorize(auth=self.auth)
        self.node_settings.save()
        data = {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'external_account_id': self.account_id,
                    'folder_id': self._mock_folder_info['folder_id']
                    }
                }
            }
        res = self.app.put_json_api(self.setting_detail_url, 
            data, auth=self.user.auth,
            expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal('Must specify both folder_id and folder_path for {}'.format(self.short_name),
             res.json['errors'][0]['detail'])
