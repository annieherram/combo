from __future__ import print_function
import git
from dependency_importer import *
from source_locator_server import *
import six


class DependencyAlreadyExisted(Exception):
    pass


class DependencyVersionUpdated(Exception):
    pass


class ManifestDetails:
    manifest_file_name = 'combo_manifest.json'

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


class DependenciesManager:
    def __init__(self, repo_path):
        self._base_manifest = ManifestDetails(repo_path)
        self._manifests = {self._base_manifest.name: self._base_manifest}
        self._dependencies = dict()

        self._repo_path = repo_path
        self._my_repo = git.Repo(repo_path)

        self.importer = DependencyImporter()

    def get_dependency_dir(self, dep):
        dep_name = dep if isinstance(dep, six.string_types) else dep['name']
        return os.path.join(self._base_manifest.output_dir, dep_name.lower().replace(' ', '_'))

    def add_manifest(self, manifest):
        if manifest.name in self._manifests.keys():
            raise KeyError('Dependency {} exists in multiple manifests'.format(manifest.name))

        self._manifests[manifest.name] = manifest

    def add_dependency(self, dependency):
        if dependency['name'] not in self._dependencies.keys():
            self._dependencies[dependency['name']] = dependency
            return

        existing_dependency = self._dependencies[dependency['name']]
        try:
            latest_version = VersionFormatter().get_latest((dependency['version'], existing_dependency['version']))
        except MajorVersionMismatch:
            raise MajorVersionMismatch('Both {} and {} versions of {} are required'.format(
                dependency['version'], existing_dependency['version'], dependency['name']))

        if latest_version == dependency['version']:
            self._dependencies[dependency['name']] = dependency
            raise DependencyAlreadyExisted

        raise DependencyVersionUpdated

    def clone_dependencies(self, custom_manifest=None):
        """ Iterate the dependencies and clone them to the configured version """
        manifest = self._base_manifest if custom_manifest is None else custom_manifest

        for dep_name, dep in manifest.dependencies.items():
            dst_path = self.get_dependency_dir(dep_name)

            try:
                self.add_dependency(dep)
            except DependencyAlreadyExisted:
                continue
            except DependencyVersionUpdated:
                # Old version is now irrelevant
                # TODO: Remove old version's dependencies
                rmtree(dst_path)

            self.importer.clone(dep_name, dep['version'], dst_path)

            # Clone the recursive dependencies of the current dependency
            dependency_manifest = ManifestDetails(dst_path)
            if dependency_manifest.exists():
                self.add_manifest(dependency_manifest)
                self.clone_dependencies(dependency_manifest)

    def resolve(self):
        """ Commit the current manifest's into your repository """

        """
        Pre-resolve steps - check if "dirty"
        
        Resolve algorithm steps:
        1. clone_everything - Recursive clone, keeping both older and newer versions. Create a tree in the process.
        2. create_debatables_table - Iterate all dependencies. Mark debatable if there is a newer version somewhere
            debatables_table_example = [
                {"debatable_key": "A_v1", "eliminators": ["A_v2", "A_v3"], "alive": True},  # Always start as alive
                {"debatable_key": "A_v2", "eliminators": ["A_v3"], "alive": True},
                {"debatable_key": "B_v1", "eliminators": ["B_v2"], "alive": True},
            ]
        3. marks_deads - Go through the tree:
            if is_debatable():
                pass  # Don't go through the node's sons
            else:
                if is_eliminator():
                    mark_all_eliminated_debatables_as_dead()
                step_in()  # Recursive
        4. step_in_alive_debatables - Perform step 3 on every alive "debatable" from the debatables table
        5. remote_deads_from_tree - Go through the tree, if a node is marked as "dead" on the debatables table,
                                    remove the node from the tree (this will remove his "sons" as well)  
        6. keep_from_tree - All of the dependencies were already cloned on step 1,
                            keep only the files of those who are still remaining on the tree
                            
        Puking bags will be delivered on the exit. Thank you for choosing Combo :)
        """

        self.clone_dependencies()
