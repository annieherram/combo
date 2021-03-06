from __future__ import print_function
from combo_core.source_maintainer import *
from combo_core.importer import *
from combo_core.compat import connection_error
import requests
import json

MAX_RESPONSE_LENGTH = 4096


class ServerConnectionError(ComboException, connection_error):
    pass


class NackFromServer(ComboException):
    pass


class RemoteSourceLocator(SourceLocator):
    def __init__(self, address):
        self._addr = address
        self._url = 'http://' + ':'.join(str(x) for x in address)

    def _extended_url(self, *args):
        return '/'.join((self._url, ) + args)

    def get_source(self, project_name, version):
        req_url = self._extended_url('get_source')
        params = {'project_name': project_name, 'project_version': str(version)}

        try:
            response = requests.get(req_url, params=params)
        except BaseException as e:
            raise ServerConnectionError(
                'Could not get response for request to "{}" with params "{}"'.format(req_url, params), e)

        try:
            source = json.loads(response.content.decode())
        except BaseException as e:
            raise UndefinedProject('Server could not locate project "{}" version "{}"'.format(project_name, version), e)

        return source

    def all_sources(self):
        req_url = self._extended_url('get_available_versions')

        try:
            response = requests.get(req_url)
        except BaseException as e:
            raise ServerConnectionError('Could not get response for request to "{}"'.format(req_url), e)

        try:
            sources_dict = json.loads(response.content.decode())
        except BaseException as e:
            raise ServerConnectionError('Server did not return a list of the available versions', e)

        return sources_dict


class RemoteSourceMaintainer(RemoteSourceLocator, SourceMaintainer):
    def __init__(self, address):
        super(RemoteSourceMaintainer, self).__init__(address)

    def add_project(self, project_name, source_type=None):
        req_url = self._extended_url('add_project')

        data = {'project_name': project_name}
        if source_type:
            data['source_type'] = source_type

        try:
            response = requests.post(req_url, data=data)
            print('Server response: {}'.format(response.content))
        except BaseException as e:
            raise ServerConnectionError('Could not post new project {}'.format(project_name), e)

    def add_version(self, version_details, **kwargs):
        # kwargs is not relevant here, because it is not sent to the server anyway

        req_url = self._extended_url('add_version')
        data = {'version_details': json.dumps(version_details)}

        try:
            response = requests.post(req_url, data=data)
            print('Server response: {}'.format(response.content))
        except BaseException as e:
            raise ServerConnectionError('Could not post version located at {}'.format(version_details), e)


class RemoteImporter(Importer):
    def __init__(self, sources_locator):
        """
        Construct a dependencies importer which uses the combo server
        :param sources_locator: A RemoteSourceLocator object
        """
        if not isinstance(sources_locator, RemoteSourceLocator):
            raise UnhandledComboException(
                'Invalid sources locator for type for server importer: {}'.format(type(sources_locator)))
        super(RemoteImporter, self).__init__(sources_locator)

    def get_all_sources_map(self):
        return self._source_locator.all_sources()

    # TODO: Return this optimized implementation once the server has a real implementation of the all sources map
    # def get_dep_hash(self, dep):
    #     """
    #     :param dep: A combo dependency
    #     :return: The hash of the given dependency
    #     """
    #     # If already cached, return the cached hash
    #     if self._cached_data.has_dep(dep):
    #         return self._cached_data.get_hash(dep)
    #
    #     # Dependency is not cached, use the all sources json instead
    #     sources_map = self.get_all_sources_map()
    #     assert str(dep) in sources_map, 'Dependency "{}" not found on the remote sources map'.format(dep)
    #
    #     return sources_map[str(dep)]['hash']
