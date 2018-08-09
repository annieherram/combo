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

        self.original_nodes = dict()
        self.manifests = dict()
        self._dependencies = list()
        self._head = dict()

    def build(self, base_manifest):
        """ Build the tree from the given manifest data recursively """

        # clone everything - recursive clone, keeping both older and newer versions. Create a tree in the process.
        self._head = self._build_tree(self._head_value, base_manifest.sons())
        self._dependencies = self._extract_values()

    def values(self):
        return self._dependencies

    def disconnect_outdated_versions(self):
        """ Remove all irrelevant nodes from the tree using the following algorithm: """

        print(self)
        while not self._is_slashed():
            '''
            1. create_undecided_table:
                Iterate all dependencies. Mark undecided if there is a newer version somewhere.
                For each undecided dependency, mark it's eliminators (newer versions of the same project).
                Out of the eliminators, save the critical eliminators of it,
                which are the eliminators with a different major version.
                Additionally, save an 'alive' flag which always starts as True,
                and 'major_eliminated' which starts as None.
                
                undecided_table_example = {
                    "A-0.1": {
                        "eliminators": ["A-0.2", "A-1.0"], "criticals": ["A-1.0"],
                        "alive": True, "major_eliminated": None
                    },
                    "A-0.2": {
                        "eliminators": ["A-1.0"], "criticals": ["A-1.0"],
                        "alive": True, "major_eliminated": None
                    },
                    "B-0.1": {
                        "eliminators": ["B-0.2"], "criticals": [],
                        "alive": True, "major_eliminated": None
                    }
                }             
            '''
            self._create_undecided_table()

            '''
            2. mark_deads - Go through the tree:
                if is_undecided:
                    pass  # Don't go through the node's sons
                else:
                    for each undecided:
                        if node_is_eliminator:
                            mark_as_dead
                            if node_is_critical_eliminator:
                                save_as_major_eliminated
                    step_in()  # Recursive                
            '''
            self._mark_deads()

            ''' 3. step_in_alive_undecideds - Perform step 3 on every alive "undecided" from the undecided table '''
            self._step_in_undecided()

            '''
            4. remove_deads_from_tree:
                Go through the tree, if a node is marked as "dead" on the undecided table,
                remove the node from the tree (this will remove his "sons" as well).
                
                If a "directly" removed node is "major_eliminated",
                this means there is an error since the older version was connected to the tree and it is removed
                because if a major different version. 
                
                If a "major_eliminated" node was removed "indirectly",
                this is fine because the "major_eliminated" node wasn't required anyway.
            '''
            print(self.undecided_table_as_str())
            self._slash_deads()
            print(self)

    def _extract_values(self, head=None):
        head = head or self._head
        values_set = set()

        for son in self._get_sons(head):
            values_set.add(son['value'])
            values_set |= self._extract_values(son)

        return values_set

    def _is_slashed(self):
        instances = {dep.name: len(list(filter(lambda x: x.name == dep.name, self._dependencies)))
                     for dep in self._dependencies}

        return all(count == 1 for count in instances.values())

    def __str__(self):
        return self._tree_as_str()

    def get_clone_dir(self, dep):
        return os.path.join(self._internal_working_dir,
                            dep.normalized_name_dir(), dep.normalized_version_dir())

    def undecided_table_as_str(self):
        result = ''
        for undecided, details in self._undecided_table.items():
            result += 'Dependency {}: alive={}, major_eliminated={}, eliminators={}, criticals={}'.format(
                str(undecided), details['alive'], str(details['major_eliminated']),
                [str(x) for x in details['eliminators']], [str(x) for x in details['criticals']]) + '\n'

        return result

    def _add_node(self, dependency_node):
        if dependency_node not in self.original_nodes.values():
            self.original_nodes[dependency_node['value']] = dependency_node
            return

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

            dependency_values = [dep_node['value'] for dep_node in self.original_nodes.values()]
            if combo_dependency not in dependency_values:
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

        head = head or self._head

        separator = ',' + new_line(indentation + 1)
        sons = separator.join(self._tree_as_str(son, indentation + 1) for son in self._get_sons(head))
        wrapped = new_line(indentation) + '{' + new_line(indentation + 1) + sons + new_line(indentation) + '}'

        return str(head['value']) + ': ' + (wrapped if sons else '{}')

    def _create_undecided_table(self):
        def is_eliminator(undecided, eliminator):
            return eliminator.name == undecided.name and eliminator.version > undecided.version

        def find_critical(undecided, all_eliminators):
            critical = list(filter(lambda elm: not Version.same_major(elm.version, undecided.version), all_eliminators))
            return critical

        self._undecided_table = dict()

        for dep in self._dependencies:
            eliminators = [eliminator for eliminator in self._dependencies if is_eliminator(dep, eliminator)]
            if any(eliminators):
                self._undecided_table[dep] = {
                    'eliminators': eliminators,
                    'criticals': find_critical(dep, eliminators),
                    'alive': True,
                    'major_eliminated': None
                }

    def _is_undecided(self, dep_value):
        return dep_value in self._undecided_table.keys()

    def _is_alive(self, dep_value):
        if not self._is_undecided(dep_value):
            return True
        return self._undecided_table[dep_value]['alive']

    @staticmethod
    def _get_sons(head):
        # Only the dict values are relevant
        return [head[key] for key in head.keys() if key != 'value']

    def _mark_deads(self, head=None):
        head = head or self._head

        if self._is_undecided(head['value']):
            return

        # If a node is eliminated, mark it as dead
        for undecided in self._undecided_table.values():
            if head['value'] in undecided['eliminators']:
                undecided['alive'] = False
                # If the eliminator is critical, this means that if the undecided is relevant there is a problem
                if head['value'] in undecided['criticals']:
                    undecided['major_eliminated'] = head['value']

        for son in self._get_sons(head):
            # Continue recursively
            self._mark_deads(son)

    def _step_in_undecided(self):
        # Iterate all alive undecided
        for key, undecided in self._undecided_table.items():
            if undecided['alive']:
                # Perform the "mark deads" step of each node of the current dependency
                for node in self.original_nodes.values():
                    if node['value'] == key:
                        self._mark_deads(node)

    def _recursive_slash(self, head=None):
        head = head or self._head
        pop_list = list()

        for son in self._get_sons(head):
            if self._is_alive(son['value']):
                self._recursive_slash(son)
            else:
                # If we explicitly need to remove an major_mismatch node, this means there is a problem
                if self._is_undecided(son['value']):
                    major_eliminator = self._undecided_table[son['value']]['major_eliminated']
                    if major_eliminator:
                        raise MajorVersionMismatch('Dependency {} could not be replaced by {}'.format(
                            son['value'], major_eliminator))
                pop_list.append(son['value'])

        for son_to_pop in pop_list:
            head.pop(son_to_pop)

    def _slash_deads(self):
        self._recursive_slash()
        self._dependencies = self._extract_values()

    def _add_manifest(self, dep, manifest):
        if dep not in self.manifests.keys():
            self.manifests[dep] = manifest
        else:
            if self.manifests[dep] != manifest:
                raise ValueError('Different manifests found for dependency {}'.format(str(dep)))
