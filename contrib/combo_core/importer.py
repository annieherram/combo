"""
Handles importing dependencies from multiple possible sources (git repository, zip file, server, etc...)
"""

from __future__ import print_function
from .compat import appdata_dir_path
from .combo_nodes import *
from .source_types import *
import json


class AppDataManuallyEdited(ComboException):
    pass


class AppDataCloneManuallyDeleted(AppDataManuallyEdited):
    pass


class CachedData:
    def __init__(self, clones_dir_name):
        self._cache_size = 64 * 1024**2  # 64 MB
        self.appdata_dir = Directory(appdata_dir_path)
        self._clones_dir = self.appdata_dir.join(clones_dir_name)

        # If the JSON file doesn't exist yet, create a default one
        self._json_file_path = self.appdata_dir.join('local_projects.json').get_file(json.dumps(dict()))
        self._cached_projects = JsonFile(self._json_file_path)

    def dep_stored_data(self, dep):
        if str(dep) not in self._cached_projects:
            raise AppDataManuallyEdited('Could not find dependency {} in stored data'.format(dep))

        return self._cached_projects[str(dep)]

    def has_dep(self, dep):
        dir_found = self.dep_dir_path(dep).exists()
        found_in_map = str(dep) in self._cached_projects
        return dir_found and found_in_map

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
            raise AppDataManuallyEdited('Dependency {} does not exist'.format(dep))

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

    def _get_used_storage(self):
        return self._clones_dir.size()

    def dep_dir_path(self, dep):
        return self._clones_dir.join(dep.normalized_name_dir(), dep.normalized_version_dir())

    def add(self, dep):
        directory = self.dep_dir_path(dep)
        self._cached_projects[str(dep)] = {'size': directory.size(), 'hash': hash(directory)}

    def apply_limit(self):
        """
        Delete dependencies from cache until the size limit is applicable
        """
        while self._get_used_storage() > self._cache_size:
            dep_to_remove = ComboDep.destring(self._cached_projects.keys()[0])
            self.remove(dep_to_remove)


class Importer(object):
    def __init__(self, sources_locator):
        """
        Construct a dependencies importer
        :param sources_locator: an implementation of the SourceLocator interface
        """
        self._handlers = {
            'git': GitDependency,
            'file_system': FileSystemDependency
        }
        if not isinstance(sources_locator, SourceLocator):
            raise UnhandledComboException('Unsupported source locator type "{}"'.format(type(sources_locator)))

        self._source_locator = sources_locator
        self._cached_data = CachedData('clones')

    def clone(self, combo_dep):
        clone_dir = self._cached_data.dep_dir_path(combo_dep)

        # If the requested import already exists in metadata, ignore it
        if clone_dir.exists():
            try:
                self._cached_data.valid(combo_dep)
                return clone_dir
            except AppDataManuallyEdited:
                self._cached_data.remove(combo_dep)
                clone_dir.delete()

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

    def get_dep_hash(self, dep):
        """
        :param dep: A combo dependency
        :return: The hash of the given dependency
        """
        # If already cached, return the cached hash
        if self._cached_data.has_dep(dep):
            return self._cached_data.get_hash(dep)

        # We don't have the server available, so we need to cache the dependency to get its hash
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


class SourceDetailsProvider:
    def __init__(self, working_dir):
        self._handlers = {
            GitDetailsProvider.TYPE_NAME: GitDetailsProvider,
            FileSystemDetailsProvider.TYPE_NAME: FileSystemDetailsProvider
        }

        self._working_dir = working_dir

    def get_details(self, source_type):
        provider = self._handlers[source_type](self._working_dir)
        return provider.get_details()
