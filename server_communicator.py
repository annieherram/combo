from combo_core.source_locator import *
from combo_core.compat import connection_error
import requests

COMBO_SERVER_ADDRESS = ('localhost', 5000)
MAX_RESPONSE_LENGTH = 4096


class ServerConnectionError(ComboException, connection_error):
    pass


class NackFromServer(ComboException):
    pass


class ServerSourceLocator(SourceLocator):
    def __init__(self, address):
        self._addr = address
        self._url = 'http://' + ':'.join(str(x) for x in address)

    def get_source(self, project_name, version):
        params = {'project_name': project_name, 'project_version': str(version)}

        try:
            response = requests.get('/'.join((self._url, 'get_source')), params=params)
            source = json.loads(response.content.decode())
        except BaseException as e:
            raise UndefinedProject('Server could not locate project "{}" version "{}"'.format(project_name, version), e)

        return source

    def all_sources(self):
        try:
            response = requests.get('/'.join((self._url, 'get_available_versions')))
            sources_dict = json.loads(response.content.decode())
        except BaseException as e:
            raise ServerConnectionError('Server did not return a list of the available versions', e)

        return sources_dict
