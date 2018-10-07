from __future__ import print_function
from dependency_importer import *
from dependencies_tree import *


class DependenciesManager:
    def __init__(self, repo_path, sources_json=None):
        self._repo_path = repo_path

        # Root directory must have base manifest
        self._base_manifest = ManifestDetails(self._repo_path, ComboRoot())
        assert self._base_manifest.valid_as_root(), 'Root manifest cannot be combo root'

        self._importer = DependencyImporter(sources_json)
        self._tree = DependenciesTree(self._importer)

        # TODO: Temporary, should probably read data from metadata
        if os.path.exists(self._base_manifest.output_dir):
            rmtree(self._base_manifest.output_dir)

    def dirty(self):
        """
        Dirty repository means there is a difference between the current manifest on the working directory
        and the versions cloned to the working directory
        :return: A boolean indication for the dirty state
        """
        return True  # TODO: Implement dirty function

    def resolve(self):
        # If the repository is not dirty, this means everything is up-to-date and there is nothing to do
        if not self.dirty():
            print('Project is already up to date')
            return

        self._tree.build(self._base_manifest)
        self._tree.disconnect_outdated_versions()
        self._extern_from_tree()

    def get_dependency_path(self, dependency_name):
        return os.path.join(self._base_manifest.output_dir, ComboDep.normalize_name_dir(dependency_name))

    def _dep_dir(self, dep, internal=False):
        if internal:
            return self._importer.get_clone_dir(dep)
        else:
            return self.get_dependency_path(dep.name)

    def _get_manifests(self):
        return self._tree.manifests

    def _extern_dependency(self, dep):
        dst_path = self._dep_dir(dep)

        if not os.path.exists(dst_path):
            src_path = self._dep_dir(dep, True)
            copytree(src_path, dst_path)

    def _extern_from_tree(self):
        dependencies = self._tree.values()

        instances = {dep.name: len(list(filter(lambda x: x.name == dep.name, dependencies))) for dep in dependencies}
        multiple_versions = list(filter(lambda tup: tup[1] > 1, instances.items()))

        if multiple_versions:
            raise LookupError("Multiple versions found: {}".format(multiple_versions))

        for dep in dependencies:
            self._extern_dependency(dep)
