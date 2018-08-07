from __future__ import print_function
from dependency_importer import *
from dependencies_tree import *


class DependenciesManager:
    def __init__(self, repo_path):
        self._METADATA_DIR_NAME = '.combo'

        self._base_manifest = ManifestDetails(repo_path)
        self._manifests = {self._base_manifest.name: self._base_manifest}

        self._repo_path = repo_path

        self._importer = DependencyImporter()
        self._metadata_dir_path = os.path.join(repo_path, self._METADATA_DIR_NAME)
        self._tree = DependenciesTree(self._importer, self._metadata_dir_path)

    def resolve(self):
        """
        Pre-resolve steps - check if "dirty"
        Resolve algorithm steps:
        """

        self._tree.build(self._base_manifest)
        print(self._tree, '\n')

        self._tree.disconnect_outdated_versions()
        print(self._tree, '\n')

        self._extern_from_tree()

    def _get_dependency_dir(self, dep, internal=False):
        if internal:
            return self._tree.get_clone_dir(dep)
        else:
            return os.path.join(self._base_manifest.output_dir, dep.normalized_name_dir())

    def _get_manifests(self):
        return self._tree.manifests

    def _extern_dependency(self, dep):
        dst_path = self._get_dependency_dir(dep)

        if not os.path.exists(dst_path):
            src_path = self._get_dependency_dir(dep, True)
            copytree(src_path, dst_path)

    def _extern_from_tree(self):
        dependencies = self._tree.values()

        instances = {dep.name: len(list(filter(lambda x: x.name == dep.name, dependencies))) for dep in dependencies}
        multiple_versions = list(filter(lambda tup: tup[1] > 1, instances.items()))

        if multiple_versions:
            raise LookupError("Multiple versions found: {}".format(multiple_versions))

        for dep in dependencies:
            self._extern_dependency(dep)
