from __future__ import print_function
from dependency_importer import *
from dependencies_tree import *


class DependenciesManager:
    def __init__(self, repo_dir, sources_json=None):
        self._repo_dir = repo_dir

        # Root directory must have base manifest
        self._base_manifest = ManifestDetails(self._repo_dir, ComboRoot())
        assert self._base_manifest.valid_as_root(), 'Root manifest cannot be combo root'

        self._importer = DependencyImporter(sources_json)
        self._tree = DependenciesTree(self._importer)
        self._tree_initialized = False

    def cleanup(self):
        # Clean importer's temporary cached data after finished
        self._importer.cleanup()

    def _initialize_tree(self):
        if not self._tree.ready():
            self._tree.build(self._base_manifest)
            self._tree.disconnect_outdated_versions()

    def dirty(self, silent=False):
        """
        Dirty repository means there is a difference between the current manifest on the working directory
        and the versions cloned to the working directory
        :return: A boolean indication for the dirty state
        """
        self._initialize_tree()

        is_dirty = not self._compare_content_with_tree()

        if not silent:
            print('is_dirty result is {}'.format(is_dirty))

        return is_dirty

    def resolve(self):
        # If the repository is not dirty, this means everything is up-to-date and there is nothing to do
        if not self.dirty(silent=True):
            print('Project is already up-to-date')
            return

        self._initialize_tree()
        self._extern_from_tree()
        return True

    def get_dependency_path(self, dependency_name):
        return self._base_manifest.output_dir.join(ComboDep.normalize_name_dir(dependency_name))

    def _dep_dir(self, dep, from_cache=False):
        if from_cache:
            return self._importer.get_cached_path(dep)
        else:
            return self.get_dependency_path(dep.name)

    def _get_manifests(self):
        return self._tree.manifests

    def _extern_dependency(self, dep):
        dst_path = self.get_dependency_path(dep.name)

        if dst_path.exists():
            raise UnhandledComboException(
                'Trying to extern dependency {} which already existed at {}'.format(dep, dst_path))

        print('Adding dependency {} into {}'.format(dep, dst_path))
        src_path = self._importer.get_cached_path(dep)
        src_path.copy_to(dst_path)

    @staticmethod
    def _check_for_multiple_versions(dependencies):
        instances = {dep.name: len(list(filter(lambda x: x.name == dep.name, dependencies))) for dep in dependencies}
        multiple_versions = list(filter(lambda tup: tup[1] > 1, instances.items()))

        if multiple_versions:
            raise LookupError("Multiple versions found: {}".format(multiple_versions))

    def _extern_from_tree(self):
        dependencies = self._tree.values()
        self._check_for_multiple_versions(dependencies)

        for dep in dependencies:
            if not self._compare_dep_content(dep):
                print('Removing deprecated depencency {}'.format(dep))
                self.get_dependency_path(dep.name).delete()
                self._extern_dependency(dep)

    def _compare_dep_content(self, dep):
        contrib_dir = self.get_dependency_path(dep.name)
        cached_dir = self._importer.get_cached_path(dep)

        if not contrib_dir.exists() or not cached_dir.exists():
            return False

        return contrib_dir == cached_dir

    def _compare_content_with_tree(self):
        contrib_dirs = self._base_manifest.output_dir.sons()
        dependencies = self._tree.values()

        # Amount
        if len(contrib_dirs) != len(dependencies):
            return False

        # Directory names
        contrib_paths = [x.path for x in contrib_dirs]
        if any(self.get_dependency_path(dep.name).path not in contrib_paths for dep in dependencies):
            return False

        # Content
        for dep in dependencies:
            if not self._compare_dep_content(dep):
                return False

        return True
