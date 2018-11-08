from combo_core.source_locator import *
import socket
import struct

COMBO_SERVER_ADDRESS = ('localhost', 9999)
MAX_RESPONSE_LENGTH = 4096


class NackFromServer(ComboException):
    pass


class ServerSourceLocator(SourceLocator):
    def __init__(self, address):
        self._addr = address

    def contact_server(self, project_name, version):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(self._addr)

        request = ';'.join((project_name, str(version))).encode()
        request_length = struct.pack('>i', len(request))

        client.send(request_length)
        client.recv(4)  # Ack
        client.send(request)

        response = client.recv(MAX_RESPONSE_LENGTH)
        if response.startswith(b'\x00\xde\xc1\x1e'):
            raise NackFromServer()

        source = json.loads(response.decode())
        return source

    def get_source(self, project_name, version):
        try:
            source = self.contact_server(project_name, version)
        except NackFromServer:
            raise UndefinedProject('Server could not locate project {} with version {}'.format(project_name, version))

        return source

