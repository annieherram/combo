from __future__ import print_function
from utils import *
import git
from dependency_import import *

class DependencyAlreadyExisted(Exception):
    pass

class DependencyVersionUpdated(Exception):
    pass


class ManifestDetails:
    manifest_file_name = "combo_manifest.json"

    def __init__(self, dir_path):
        self.base_path = dir_path
        self.file_path = os.path.join(dir_path, ManifestDetails.manifest_file_name)
        if not self.exists():
            return

        self.manifest = self.read_manifest(self.file_path)
        self.name = self.manifest['name']
        self.dependencies = {dep['name']: dep for dep in self.manifest['dependencies']}

        self.output_dir = None
        self.is_exec = bool(self.manifest['is_executable'])

        if self.is_exec:
            self.output_dir = os.path.abspath(os.path.join(dir_path, self.manifest['output_directory']))

    def exists(self):
        return os.path.exists(self.file_path)

    @staticmethod
    def read_manifest(path):
        with open(path, 'r') as f:
            data = json.load(f)
        return data


class Combo:
    def __init__(self, repo_path, urls):
        self._base_manifest = ManifestDetails(repo_path)
        self._manifests = {self._base_manifest.name: self._base_manifest}
        self._dependencies = dict()

        self._urls = urls
        self._repo_path = repo_path
        self._my_repo = git.Repo(repo_path)

        self.validate_params()

    def validate_params(self):
        for manifest in self._manifests.values():
            for dep in manifest.dependencies.values():
                assert dep['name'] in self._urls, "Count not find a source for dependency '{}'".format(dep['name'])

    def get_dependency_dir(self, dep):
        dep_name = dep if isinstance(dep, basestring) else dep['name']
        return os.path.join(self._base_manifest.output_dir, dep_name.lower().replace(' ', '_'))

    def add_manifest(self, manifest):
        if manifest.name in self._manifests.keys():
            raise KeyError("Dependency {} exists in multiple manifests".format(manifest.name))

        self._manifests[manifest.name] = manifest

    def add_dependency(self, dependency):
        if dependency['name'] not in self._dependencies.keys():
            self._dependencies[dependency['name']] = dependency
            return

        existing_dependency = self._dependencies[dependency['name']]
        try:
            latest_version = VersionFormatter().get_latest((dependency['version'], existing_dependency['version']))
        except MajorVersionMismatch:
            raise MajorVersionMismatch("Both {} and {} versions of {} are required".format(
                dependency['version'], existing_dependency['version'], dependency['name']))

        if latest_version == dependency['version']:
            self._dependencies[dependency['name']] = dependency
            raise DependencyVersionUpdated

        raise DependencyAlreadyExisted

    def clone_dependencies(self, custom_manifest=None):
        """ Iterate the dependencies and clone them to the configured version """
        manifest = self._base_manifest if custom_manifest is None else custom_manifest

        for dep_name, dep in manifest.dependencies.items():
            dst_path = self.get_dependency_dir(dep_name)
            repo_url = self._urls[dep_name]

            try:
                self.add_dependency(dep)
            except DependencyAlreadyExisted:
                continue
            except DependencyVersionUpdated:
                # Old version is now irrelevant
                # TODO: Remove old version's dependencies
                rmtree(dst_path)

            DependencyImport(repo_url).clone(dep['version'], dst_path)

            # Clone the recursive dependencies of the current dependency
            dependency_manifest = ManifestDetails(dst_path)
            if dependency_manifest.exists():
                self.add_manifest(dependency_manifest)
                self.clone_dependencies(dependency_manifest)

    def resolve(self):
        """ Commit the current manifest's into your repository """
        self.clone_dependencies()

        # TODO: Decide if we want this
        # # Stage
        # for manifest in self._manifests.values():
        #     for dep in manifest.dependencies.values():
        #         # Stage all files of the current dependency
        #         dep_dir = self.get_dependency_dir(dep)
        #         self._my_repo.index.add([dep_dir])
        #
        # Commit the changes
        # self._my_repo.index.commit('Manifest apply', parent_commits=[self._my_repo.commit()])
