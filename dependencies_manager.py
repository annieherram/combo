from __future__ import print_function
from dependency_importer import *
from dependencies_tree import *


class ComboMetadata:
    METADATA_DIR_NAME = '.combo'

    def __init__(self, project_path):
        self.path = os.path.join(project_path, self.METADATA_DIR_NAME)
        self.clones_dir = os.path.join(self.path, 'clones')

        self.exists = os.path.exists(self.path)


class DependenciesManager:
    def __init__(self, repo_path):
        self._base_manifest = ManifestDetails(repo_path)
        self._repo_path = repo_path

        self._importer = DependencyImporter()
        self._metadata = ComboMetadata(self._repo_path)
        self._tree = DependenciesTree(self._importer, self._metadata.clones_dir)

        # TODO: Temporary, should probably read data from metadata
        if os.path.exists(self._base_manifest.output_dir):
            rmtree(self._base_manifest.output_dir)
        if os.path.exists(self._metadata.path):
            rmtree(self._metadata.path)

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
