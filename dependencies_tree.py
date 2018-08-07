from combo_dependnecy import *
from manifest_details import *
from version import *


class DependencyAlreadyExisted(Exception):
    pass


class DependencyVersionUpdated(Exception):
    pass


class DependenciesTree:
    def __init__(self, dependency_importer, internal_working_dir):
        self._head_value = 'Root'
        self._importer = dependency_importer
        self._internal_working_dir = internal_working_dir

        self.nodes = dict()
        self.manifests = dict()
        self._tree_head = dict()

    def build(self, base_manifest):
        """ Build the tree from the given manifest data recursively """

        # clone everything - recursive clone, keeping both older and newer versions. Create a tree in the process.
        self._tree_head = self._build_tree(self._head_value, base_manifest.sons())

    def disconnect_outdated_versions(self):
        """ Remove all irrelevant nodes from the tree using the following algorithm: """

        '''
        1. create_undecided_table - Iterate all dependencies. Mark undecided if there is a newer version somewhere
            undecided_table_example = {
                "A_v1": {"eliminators": ["A_v2", "A_v3"], "alive": True},  # Always start as alive
                "A_v2": {"eliminators": ["A_v3"], "alive": True},
                "B_v1": {"eliminators": ["B_v2"], "alive": True},
            }
        '''
        self._create_undecided_table()

        '''
        2. mark_deads - Go through the tree:
            if is_undecided():
                pass  # Don't go through the node's sons
            else:
                if is_eliminator():
                    mark_all_eliminated_undecided_as_dead()
                step_in()  # Recursive
        '''
        self._mark_deads()

        ''' 3. step_in_alive_undecideds - Perform step 3 on every alive "undecided" from the undecided table '''
        self._step_in_undecided()

        '''
        4. remove_deads_from_tree - Go through the tree, if a node is marked as "dead" on the undecided table,
                                    remove the node from the tree (this will remove his "sons" as well)
        '''
        self._remove_deads_from_tree()

    def values(self, head=None):
        if head is None:
            head = self._tree_head

        lst = list()

        for son in self._get_sons(head):
            lst += [son['value']]
            lst += self.values(son)

        return lst

    def __str__(self):
        return self._tree_as_str()

    def get_clone_dir(self, dep):
        return os.path.join(self._internal_working_dir,
                            dep.normalized_name_dir(), dep.normalized_version_dir())

    def _add_node(self, dependency_node):
        if dependency_node not in self.nodes.values():
            self.nodes[dependency_node['value']] = dependency_node
            return

    def _get_dep_values(self):
        return [dep_node['value'] for dep_node in self.nodes.values()]

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

        :param head_value: The content of the current node of the tree
        :param sons:       A list of the sons (dependencies) that should be added next
        """
        tree_head = {'value': head_value}

        for dep in sons:
            add_dep_node_flag = False
            combo_dependency = ComboDep(dep['name'], dep['version'])
            dst_path = self.get_clone_dir(combo_dependency)

            if combo_dependency not in self._get_dep_values():
                add_dep_node_flag = True
                self._importer.clone(combo_dependency, dst_path)

            # Clone the recursive dependencies of the current dependency
            next_sons = list()
            dependency_manifest = ManifestDetails(dst_path)
            if dependency_manifest.exists():
                self._add_manifest(combo_dependency, dependency_manifest)
                next_sons = dependency_manifest.sons()

            tree_head[combo_dependency] = self._build_tree(combo_dependency, next_sons)

            if add_dep_node_flag:
                self._add_node(tree_head[combo_dependency])

        return tree_head

    def _tree_as_str(self, head=None, indentation=0):
        def new_line(indent):
            return '\n' + '\t' * indent

        if head is None:
            head = self._tree_head

        separator = ',' + new_line(indentation + 1)
        sons = separator.join(self._tree_as_str(son, indentation + 1) for son in self._get_sons(head))
        wrapped = new_line(indentation) + '{' + new_line(indentation + 1) + sons + new_line(indentation) + '}'

        return str(head['value']) + ': ' + (wrapped if sons else '{}')

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
                for node in self.nodes.values():
                    if node['value'] == key:
                        self._mark_deads(node)

    def _remove_deads_from_tree(self, head=None):
        if head is None:
            head = self._tree_head

        pop_list = list()

        for son in self._get_sons(head):
            if self._is_alive(son['value']):
                self._remove_deads_from_tree(son)
            else:
                pop_list.append(son['value'])

        for son_to_pop in pop_list:
            head.pop(son_to_pop)

    def _add_manifest(self, dep, manifest):
        if dep not in self.manifests.keys():
            self.manifests[dep] = manifest
        else:
            if self.manifests[dep] != manifest:
                raise ValueError('Different manifests found for dependency {}'.format(str(dep)))