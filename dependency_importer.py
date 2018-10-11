"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from combo_core.source_locator import *
from combo_core.compat import appdata_dir
from combo_dependnecy import *
import socket
import struct
import json
import os

COMBO_SERVER_ADDRESS = ('localhost', 9999)
MAX_RESPONSE_LENGTH = 4096


class NackFromServer(ComboException):
    pass


class NoDependencyOnAppData(ComboException):
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
        raise NotImplementedError()


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


class CachedData:
    def __init__(self, clones_dir_name):
        self._cache_size = 64 * 1024**2  # 64 MB
        self._clones_dir = os.path.join(appdata_dir, clones_dir_name)
        self._fifo_file_path = os.path.join(appdata_dir, 'cached_fifo.txt')

        if not os.path.exists(self._fifo_file_path):
            open(self._fifo_file_path, 'w').close()

        with open(self._fifo_file_path, 'r') as f:
            self._fifo = f.readlines()

    def get_dep_cached_dir(self, dep):
        return os.path.join(self._clones_dir,
                            dep.normalized_name_dir(), dep.normalized_version_dir())

    def _get_used_storage(self):
        return utils.get_dir_size(self._clones_dir)

    def _update_file(self):
        with open(self._fifo_file_path, 'w') as f:
            f.writelines(self._fifo or '')  # In case of an empty fifo

    def add(self, dep):
        self._fifo += [str(dep)]
        self._update_file()

    def apply_limit(self):
        """
        Delete dependencies from cache until the size limit is applicable
        """
        while self._get_used_storage() > self._cache_size:
            dep_to_delete = ComboDep.destring(self._fifo[0])
            dep_path = self.get_dep_cached_dir(dep_to_delete)
            rmtree(dep_path)
            self._fifo = self._fifo[1:]

        # Update the file for the remaining lines
        self._update_file()


class DependencyImporter:
    def __init__(self, sources_json=None):
        self._handlers = {
            'git': GitDependency,
            'local_path': LocalPathDependency
        }

        self._external_server = sources_json is None
        if not self._external_server:
            self._source_locator = SourceLocator(sources_json)

        self._cached_data = CachedData('clones')

    def clone(self, combo_dep):
        clone_dir = self._cached_data.get_dep_cached_dir(combo_dep)

        # If the requested import already exists in metadata, ignore it
        if os.path.exists(clone_dir):
            return clone_dir

        if self._external_server:
            import_src = contact_server(*combo_dep.as_tuple())
        else:
            import_src = self._source_locator.get_source(*combo_dep.as_tuple()).as_dict()

        if import_src['src_type'] not in self._handlers:
            raise NotImplementedError('Can not import dependency with source type "{}"'.format(import_src.src_type))

        handler_type = self._handlers[import_src['src_type']]
        import_handler = handler_type(import_src)
        try:
            import_handler.clone(clone_dir)
        except BaseException as e:
            # Delete the imported dependency in case of error, don't leave a corrupted one
            utils.rmtree(clone_dir)
            raise e

        self._cached_data.add(combo_dep)
        return clone_dir

    def get_clone_dir(self, dep):
        path = self._cached_data.get_dep_cached_dir(dep)
        if not os.path.exists(path):
            raise NoDependencyOnAppData('Dependency {} not found on AppData'.format(dep))

        return path

    def cleanup(self):
        self._cached_data.apply_limit()
