"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from combo_core.compat import appdata_dir_path
from combo_nodes import *
from server_communicator import *
import json


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


class AppDataManuallyEdited(ComboException):
    pass


class AppDataCloneManuallyDeleted(AppDataManuallyEdited):
    pass


class ServerUnavailable(ComboException):
    pass


class LocalPathDependency(DependencyBase):
    PATH_KEYWORD = 'local_path'

    def clone(self, dst_path):
        self.assert_keywords(self.PATH_KEYWORD)

        src_path = Directory(self.dep_src[self.PATH_KEYWORD])
        if not src_path.exists():
            raise NonExistingLocalPath('Local path {} does not exist'.format(src_path))

        Directory(src_path).copy_to(dst_path)


class CachedData:
    def __init__(self, clones_dir_name):
        self._cache_size = 64 * 1024**2  # 64 MB
        self.appdata_dir = Directory(appdata_dir_path)
        self._clones_dir = self.appdata_dir.join(clones_dir_name)

        # If the JSON file doesn't exist yet, create a default one
        self._json_file_path = self.appdata_dir.join('local_projects.json').get_file(json.dumps(dict()))

        with open(self._json_file_path, 'r') as f:
            self._cached_projects = json.load(f)

        assert isinstance(self._cached_projects, dict), 'The local projects json should contain a projects dictionary'

    def dep_stored_data(self, dep):
        if str(dep) not in self._cached_projects:
            raise AppDataManuallyEdited('Could not find dependency {} in stored data'.format(dep))

        return self._cached_projects[str(dep)]

    def has_dep(self, dep):
        return self.dep_dir_path(dep).exists()

    def get_hash(self, dep):
        assert self.has_dep(dep)
        return self._cached_projects[str(dep)]['hash']

    def _validate_dep_param(self, dep, func, name):
        expected = self.dep_stored_data(dep)[name]
        found = func(self.dep_dir_path(dep))

        if found != expected:
            raise AppDataManuallyEdited(
                'Dependency {}: expected directory {} to be {}, found {}'.format(dep, name, expected, found))

    def valid(self, dep):
        if not self.has_dep(dep):
            return False

        if str(dep) in self._cached_projects:
            raise AppDataManuallyEdited(
                'Dependency {} was found in dictionary but not in clones directory'.format(dep))

        self._validate_dep_param(dep, len, 'size')
        self._validate_dep_param(dep, hash, 'hash')

        return True

    def cached_dependency_location(self, dep):
        if not self.has_dep(dep):
            raise AppDataCloneManuallyDeleted(dep)

        # Check directory hash matches to know the directory is valid
        self._validate_dep_param(dep, hash, 'hash')

        return self.dep_dir_path(dep)

    def remove(self, dep):
        # Delete the dependency's directory if it exists
        self.dep_dir_path(dep).delete()

        # Remove the dependency from the json if exists and update the file
        if str(dep) in self._cached_projects:
            self._cached_projects.pop(str(dep))
            self._update_file()

    def _get_used_storage(self):
        return self._clones_dir.size()

    def _update_file(self):
        with open(self._json_file_path, 'w') as f:
            json.dump(self._cached_projects, f, indent=4)

    def dep_dir_path(self, dep):
        return self._clones_dir.join(dep.normalized_name_dir(), dep.normalized_version_dir())

    def add(self, dep):
        directory = self.dep_dir_path(dep)
        self._cached_projects[str(dep)] = {'size': directory.size(), 'hash': hash(directory)}
        self._update_file()

    def apply_limit(self):
        """
        Delete dependencies from cache until the size limit is applicable
        """
        while self._get_used_storage() > self._cache_size:
            dep_to_remove = ComboDep.destring(self._cached_projects.keys()[0])
            self.remove(dep_to_remove)


class Importer:
    def __init__(self, sources_json=None):
        self._handlers = {
            'git': GitDependency,
            'local_path': LocalPathDependency
        }

        self._server_available = sources_json is None
        if self._server_available:
            self._source_locator = ServerSourceLocator(COMBO_SERVER_ADDRESS)
        else:
            self._source_locator = JsonSourceLocator(sources_json)
        assert isinstance(self._source_locator, SourceLocator), 'Invalid source locator type'

        self._cached_data = CachedData('clones')

    def clone(self, combo_dep):
        clone_dir = self._cached_data.dep_dir_path(combo_dep)

        # If the requested import already exists in metadata, ignore it
        if clone_dir.exists():
            return clone_dir

        print('Caching dependency {}'.format(combo_dep))

        import_src = self._source_locator.get_source(*combo_dep.as_tuple())
        if import_src['src_type'] not in self._handlers:
            raise NotImplementedError('Can not import dependency with source type "{}"'.format(import_src.src_type))

        handler_type = self._handlers[import_src['src_type']]
        import_handler = handler_type(import_src)

        try:
            import_handler.clone(clone_dir)
        except BaseException as e:
            # Delete the imported dependency in case of error, don't leave a corrupted one
            clone_dir.delete()
            raise e

        self._cached_data.add(combo_dep)
        return clone_dir

    def get_all_sources_map(self):
        if not isinstance(self._source_locator, ServerSourceLocator):
            raise ServerUnavailable('Unable to get all sources map without combo server')

        # TODO: Contact the server to get the actual map
        return self._source_locator.all_sources()

    def get_dep_hash(self, dep):
        """
        :param dep: A combo dependency
        :return: The hash of the given dependency
        """
        # If already cached, return the cached hash
        if self._cached_data.has_dep(dep):
            return self._cached_data.get_hash(dep)

        # Dependency is not cached
        # if there is a server, just use the all sources json
        if self._server_available:
            sources_map = self.get_all_sources_map()
            return sources_map[str(dep)]['hash']

        # If we don't have the server available, we need to cache the dependency ourselves
        self.clone(dep)
        return self._cached_data.get_hash(dep)

    def get_cached_path(self, dep):
        try:
            path = self._cached_data.cached_dependency_location(dep)
        except AppDataManuallyEdited:
            self._cached_data.remove(dep)
            path = self.clone(dep)

        return path

    def cleanup(self):
        self._cached_data.apply_limit()
