from __future__ import print_function
import git
from dependency_importer import *
from source_locator_server import *
from combo_dependnecy import *
from version import *


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

    def sons(self):
        return list(self.dependencies.values())

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
        self._tree_head = dict()

        self._repo_path = repo_path

        self._importer = DependencyImporter()
        self._metadata_directory = '.combo'

    def get_dependency_dir(self, dep, internal=False):
        if not internal:
            return os.path.join(self._base_manifest.output_dir, dep.normalized_name_dir())
        else:
            return os.path.join(self._repo_path, self._metadata_directory,
                                dep.normalized_name_dir(), dep.normalized_version_dir())

    def add_manifest(self, manifest):
        if manifest.name in self._manifests.keys():
            raise KeyError('Dependency {} exists in multiple manifests'.format(manifest.name))

        self._manifests[manifest.name] = manifest

    def _add_dep_node(self, dependency_node):
        if dependency_node not in self._dependencies.values():
            self._dependencies[dependency_node['value']] = dependency_node
            return

    def _get_dep_values(self):
        return [dep_node['value'] for dep_node in self._dependencies.values()]

        # TODO: Handle major version mismatches
        # existing_dependency = self._dependencies[dependency['name']]
        # try:
        #     latest_version = max(Version(dependency['version']), Version(existing_dependency['version']))
        # except MajorVersionMismatch:
        #     raise MajorVersionMismatch('Both {} and {} versions of {} are required'.format(
        #         dependency['version'], existing_dependency['version'], dependency['name']))
        #
        # if latest_version.as_string() == dependency['version']:
        #     self._dependencies[dependency['name']] = dependency
        #     raise DependencyAlreadyExisted
        #
        # raise DependencyVersionUpdated

    def _build_tree(self, head_value, sons=list()):
        """
        This is step #1.
        In this step, every dependency of the current manifest is going to be cloned, followed by his own dependencies.
        This function will continue recursively.
        Additionally, while cloning a dependencies tree is going to be built.

        :param head_node: The content of the current node of the tree
        """
        tree_head = {'value': head_value}

        for dep in sons:
            add_dep_node_flag = False
            combo_dependency = ComboDep(dep['name'], dep['version'])
            dst_path = self.get_dependency_dir(combo_dependency, True)

            if combo_dependency not in self._get_dep_values():
                add_dep_node_flag = True
                self._importer.clone(combo_dependency, dst_path)

            # Clone the recursive dependencies of the current dependency
            next_sons = list()
            dependency_manifest = ManifestDetails(dst_path)
            if dependency_manifest.exists():
                self.add_manifest(dependency_manifest)
                next_sons = dependency_manifest.sons()

            tree_head[combo_dependency] = self._build_tree(combo_dependency, next_sons)

            if add_dep_node_flag:
                self._add_dep_node(tree_head[combo_dependency])

        return tree_head

    def _create_undecided_table(self):
        def _find_eliminators(project_name, min_version):
            return list(filter(lambda x: x.name == project_name and x.version > min_version, self._get_dep_values()))

        self.undecided_table = dict()

        for dep in self._get_dep_values():
            eliminators = _find_eliminators(dep.name, dep.version)
            if any(eliminators):
                self.undecided_table[dep] = {'eliminators': eliminators, 'alive': True}

    def _is_undecided(self, dep_value):
        return dep_value in self.undecided_table.keys()

    def _is_alive(self, dep_value):
        if not self._is_undecided(dep_value):
            return True
        return self.undecided_table[dep_value]['alive']

    @staticmethod
    def _get_sons(head):
        # Only the dict values are relevant
        return [head[key] for key in head.keys() if key != 'value']

    def _mark_deads(self, head=None):
        if head is None:
            head = self._tree_head

        if self._is_undecided(head['value']):
            return

        # If a node is eliminated, mark it as dead
        for undecided in self.undecided_table.values():
            if head['value'] in undecided['eliminators']:
                undecided['alive'] = False

        for son in self._get_sons(head):
            # Continue recursively
            self._mark_deads(son)

    def _step_in_undecided(self):
        for key, undecided in self.undecided_table.items():
            if undecided['alive']:
                # Perform the "mark deads" step of each node with the "key" value
                for node in self._dependencies.values():
                    if node['value'] == key:
                        self._mark_deads(node)

    def _remove_deads_from_tree(self, head=None):
        if head is None:
            head = self._tree_head

        for son in self._get_sons(head):
            if self._is_alive(son['value']):
                self._remove_deads_from_tree(son)
            else:
                head.pop(son)

    def _extern_dependency(self, dep):
        dst_path = self.get_dependency_dir(dep)

        if not os.path.exists(dst_path):
            src_path = self.get_dependency_dir(dep, True)
            copytree(src_path, dst_path)

    def _extern_from_tree(self, head=None):
        if head is None:
            head = self._tree_head

        for son in self._get_sons(head):
            self._extern_dependency(son['value'])
            self._extern_from_tree(son)

    def resolve(self):
        """
        Pre-resolve steps - check if "dirty"
        Resolve algorithm steps:
        """

        '''
        1. clone everything - Recursive clone, keeping both older and newer versions.
            Create a tree in the process.
        '''
        self._tree_head = self._build_tree('Root', self._base_manifest.sons())

        '''
        2. create_undecided_table - Iterate all dependencies. Mark undecided if there is a newer version somewhere
            undecided_table_example = {
                "A_v1": {"eliminators": ["A_v2", "A_v3"], "alive": True},  # Always start as alive
                "A_v2": {"eliminators": ["A_v3"], "alive": True},
                "B_v1": {"eliminators": ["B_v2"], "alive": True},
            }
        '''
        self._create_undecided_table()

        '''
        3. mark_deads - Go through the tree:
            if is_undecided():
                pass  # Don't go through the node's sons
            else:
                if is_eliminator():
                    mark_all_eliminated_undecided_as_dead()
                step_in()  # Recursive
        '''
        self._mark_deads()

        ''' 4. step_in_alive_undecideds - Perform step 3 on every alive "undecided" from the undecided table '''
        self._step_in_undecided()

        '''
        5. remove_deads_from_tree - Go through the tree, if a node is marked as "dead" on the undecided table,
                                    remove the node from the tree (this will remove his "sons" as well)
        '''
        self._remove_deads_from_tree()

        '''
        6. keep_from_tree - All of the dependencies were already cloned on step 1,
                            keep only the files of those who are still remaining on the tree
        '''

        print(self._tree_head)
        self._extern_from_tree()
        # Puking bags will be delivered on the exit. Thank you for choosing Combo :)
