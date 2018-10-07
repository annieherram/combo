"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from combo_core.source_locator import *
import socket
import struct
import json
import os

COMBO_SERVER_ADDRESS = ('localhost', 9999)
MAX_RESPONSE_LENGTH = 4096


class NackFromServer(ComboException):
    pass


def contact_server(project_name, version):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(COMBO_SERVER_ADDRESS)

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


class DependencyBase(object):
    def __init__(self, dependency_source):
        self.dep_src = dependency_source

    def assert_keywords(self, *keywords):
        for keyword in keywords:
            assert keyword in self.dep_src, 'Invalid import source, missing attribute "{}"'.format(keyword)

    def clone(self, dst_path):
        raise NotImplementedError


class GitDependency(DependencyBase):
    REMOTE_URL_KEYWORD = 'remote_url'
    COMMIT_HASH_KEYWORD = 'commit_hash'

    def clone(self, dst_path):
        from combo_core import git_api

        self.assert_keywords(self.REMOTE_URL_KEYWORD, self.COMMIT_HASH_KEYWORD)

        # Clone the dependency
        repo = git_api.GitRepo(dst_path)

        try:
            repo.clone(self.dep_src[self.REMOTE_URL_KEYWORD], self.dep_src[self.COMMIT_HASH_KEYWORD])
        except BaseException as e:
            # If there is an error, make sure the repo is still closed at the end
            repo.close()
            raise e

        repo.close()


class NonExistingLocalPath(ComboException):
    pass


class LocalPathDependency(DependencyBase):
    PATH_KEYWORD = 'local_path'

    def clone(self, dst_path):
        self.assert_keywords(self.PATH_KEYWORD)

        src_path = self.dep_src[self.PATH_KEYWORD]
        if not os.path.exists(src_path):
            raise NonExistingLocalPath('Local path {} does not exist'.format(src_path))

        copytree(src_path, dst_path)


class DependencyImporter:
    def __init__(self, sources_json=None):
        self._handlers = {
            'git': GitDependency,
            'local_path': LocalPathDependency
        }

        self._external_server = sources_json is None
        if not self._external_server:
            self._source_locator = SourceLocator(sources_json)

    def clone(self, combo_dep, dst_path):
        if self._external_server:
            import_src = contact_server(*combo_dep.as_tuple())
        else:
            import_src = self._source_locator.get_source(*combo_dep.as_tuple()).as_dict()

        if import_src['src_type'] not in self._handlers:
            raise NotImplementedError('Can not import dependency with source type "{}"'.format(import_src.src_type))

        if os.path.exists(dst_path):
            # If already imported, import can be skipped
            return

        handler_type = self._handlers[import_src['src_type']]
        import_handler = handler_type(import_src)
        try:
            import_handler.clone(dst_path)
        except BaseException as e:
            # Delete the imported dependency in case of error, don't leave a corrupted one
            utils.rmtree(dst_path)
            raise e
