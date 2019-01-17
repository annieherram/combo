from combo_core.source_locator import *
from combo_core.compat import urllib, connection_error

COMBO_SERVER_ADDRESS = ('localhost', 5000)
MAX_RESPONSE_LENGTH = 4096


class ServerConnectionError(ComboException, connection_error):
    pass


class NackFromServer(ComboException):
    pass


class ServerSourceLocator(SourceLocator):
    def __init__(self, address):
        self._addr = address

    def contact_server(self, project_name, version):
        def get_url(**params):
            url = 'http://' + ':'.join(str(x) for x in self._addr)
            if params:
                url += '/?' + '&'.join('{}={}'.format(key, val) for key, val in params.items())

            return url.replace(' ', '%20')

        url = get_url(request_type='get_source', project_name=project_name, project_version=str(version))
        contents = urllib.urlopen(url).read()

        try:
            source = json.loads(contents.decode())
        except BaseException as e:
            raise NackFromServer(e, contents)

        return source

    def get_source(self, project_name, version):
        try:
            source = self.contact_server(project_name, version)
        except NackFromServer:
            raise UndefinedProject('Server could not locate project {} with version {}'.format(project_name, version))

        return source

    def all_sources(self):
        def full_json():
            d = {
                "(Core Library, v2.1)": {
                    "hash": 1507179887,
                    "size": 126
                },
                "(Lib A, v1.7)": {
                    "hash": 501194260,
                    "size": 229
                },
                "(Lib A, v1.6)": {
                    "hash": 1836199491,
                    "size": 220
                },
                "(Lib B, v1.4)": {
                    "hash": 1555234999,
                    "size": 221
                }
            }

            return json.dumps(d)

        return json.loads(full_json())
