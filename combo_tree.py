from __future__ import print_function
from combo_core import *
from combo_core.manifest import *
from combo_core.version import *


class CircularDependency(ComboException):
    pass


class NotAllowedDependency(ComboException):
    pass


class UndecidedTable(dict):
    def __init__(self, dependencies=list()):
        super(dict, self).__init__()

        for dep in dependencies:
            eliminators = [eliminator for eliminator in dependencies if self.is_eliminator(dep, eliminator)]
            if any(eliminators):
                self[dep] = {
                    'eliminators': eliminators,
                    'criticals': self.find_critical(dep, eliminators),
                    'alive': True,
                    'incompatible_eliminated': set()
                }

    def __str__(self):
        result = ''
        for undecided, details in self.items():
            result += 'Dependency {}: alive={}, incompatible_eliminated={}, eliminators={}, criticals={}'.format(
                str(undecided), details['alive'], [str(x) for x in details['incompatible_eliminated']],
                [str(x) for x in details['eliminators']], [str(x) for x in details['criticals']]) + '\n'
        return result

    def get(self, dep):
        if dep not in self.keys():
            raise KeyError('Dependency {} is not undecided'.format(dep))
        return self[dep]

    def is_alive(self, dep):
        if dep not in self.keys():
            return True
        return self[dep]['alive']

    @staticmethod
    def is_eliminator(undecided, eliminator):
        return eliminator.name == undecided.name and eliminator.version > undecided.version

    @staticmethod
    def find_critical(undecided, all_eliminators):
        return list(filter(lambda elm: not VersionNumber.compatible(elm.version, undecided.version), all_eliminators))


class ComboTree:
    def __init__(self, dependency_importer):
        self.original_nodes = dict()
        self.manifests = dict()

        self._importer = dependency_importer
        self._undecideds = UndecidedTable()

        self._dependencies = list()
        self._head = dict()
        self._done = False

    def ready(self):
        return self._done

    def build(self, base_manifest):
        """ Build the tree from the given manifest data recursively """
        def build_tree(head_value, sons=list(), path=list()):
            """
            In this step, every dependency of the current manifest will be cloned, followed by his own dependencies.
            This function will continue recursively.
            Additionally, while cloning a dependencies tree is going to be built.

            :param head_value: The content of the current node of the tree
            :param sons:       A list of the sons (dependencies) that should be added next
            :param path:       The previous dependencies that has led here, used to identify circular dependencies
            """

            tree_head = {'value': head_value}
            next_path = path + [head_value]

            if head_value.name in [dep.name for dep in path]:
                higher_dep = xfilter(lambda dep: dep.name == head_value.name, path)
                raise CircularDependency('Dependency {} eventually requires {}'.format(higher_dep, head_value),
                                         ' -> '.join(map(str, next_path)))

            for dep in sons:
                add_dep_node_flag = False
                combo_dependency = ComboDep(dep['name'], dep['version'])

                dependency_values = [dep_node['value'] for dep_node in self.original_nodes.values()]
                if combo_dependency not in dependency_values:
                    add_dep_node_flag = True
                    cached_clone = self._importer.clone(combo_dependency)
                else:
                    cached_clone = self._importer.get_cached_path(combo_dependency)

                # Clone the recursive dependencies of the current dependency
                dependency_manifest = Manifest(cached_clone, combo_dependency)

                if not dependency_manifest.valid_as_lib():
                    raise NotAllowedDependency('Dependency {} cannot be used as a library'.format(combo_dependency))

                self._add_manifest(combo_dependency, dependency_manifest)
                next_sons = dependency_manifest.sons()

                tree_head[combo_dependency] = build_tree(combo_dependency, next_sons, next_path)

                if add_dep_node_flag:
                    self._add_node(tree_head[combo_dependency])

            return tree_head

        # clone everything - recursive clone, keeping both older and newer versions. Create a tree in the process.
        self._head = build_tree(ComboRoot(), base_manifest.sons())
        self._dependencies = self._extract_values()

    def values(self):
        return self._dependencies

    def disconnect_outdated_versions(self):
        """ Remove all irrelevant nodes from the tree using the following algorithm: """

        while not self._is_slashed():
            '''
            1. create_undecided_table:
                Iterate all dependencies. Mark undecided if there is a newer version somewhere.
                For each undecided dependency, mark it's eliminators (newer versions of the same project).
                Out of the eliminators, save the critical eliminators of it,
                which are the eliminators with an incompatible version.
                Additionally, save an 'alive' flag which always starts as True,
                and 'incompatible_eliminated' which starts as an empty set.
                
                undecided_table_example = {
                    "A-0.1": {
                        "eliminators": ["A-0.2", "A-1.0"], "criticals": ["A-1.0"],
                        "alive": True, "incompatible_eliminated": set()
                    },
                    "A-0.2": {
                        "eliminators": ["A-1.0"], "criticals": ["A-1.0"],
                        "alive": True, "incompatible_eliminated": set()
                    },
                    "B-0.1": {
                        "eliminators": ["B-0.2"], "criticals": [],
                        "alive": True, "incompatible_eliminated": set()
                    }
                }             
            '''
            self._undecideds = UndecidedTable(self._dependencies)

            '''
            2. mark_deads - Go through the tree:
                if is_undecided:
                    pass  # Don't go through the node's sons
                else:
                    for each undecided:
                        if node_is_eliminator:
                            mark_as_dead
                            if node_is_critical_eliminator:
                                save_as_incompatible_eliminated
                    step_in()  # Recursive                
            '''
            self._mark_deads()

            ''' 3. step_in_alive_undecideds - Perform step 3 on every alive "undecided" from the undecided table '''
            self._step_in_undecided()

            '''
            4. remove_deads_from_tree:
                Go through the tree, if a node is marked as "dead" on the undecided table,
                remove the node from the tree (this will remove his "sons" as well).
                
                If a "directly" removed node is "incompatible_eliminated",
                this means there is an error since the older version was connected to the tree
                and it is removed because of an incompatible version. 
                
                If a "incompatible_eliminated" node was removed "indirectly",
                this is fine because the "incompatible_eliminated" node wasn't required anyway.
            '''
            self._slash_deads()

        self._done = True

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
        def recursive_str(head=None, indentation=0):
            def new_line(indent):
                return '\n' + '\t' * indent

            head = head or self._head

            separator = ',' + new_line(indentation + 1)
            sons = separator.join(recursive_str(son, indentation + 1) for son in self._get_sons(head))
            wrapped = new_line(indentation) + '{' + new_line(indentation + 1) + sons + new_line(indentation) + '}'

            return str(head['value']) + ': ' + (wrapped if sons else '{}')

        return recursive_str() + '\n'

    def _add_node(self, dependency_node):
        if dependency_node not in self.original_nodes.values():
            self.original_nodes[dependency_node['value']] = dependency_node

    @staticmethod
    def _get_sons(head):
        # Only the dict values are relevant
        return [head[key] for key in head.keys() if key != 'value']

    def _mark_deads(self, head=None):
        head = head or self._head

        if head['value'] in self._undecideds:
            return

        # If a node is eliminated, mark it as dead
        for undecided in self._undecideds.values():
            if head['value'] in undecided['eliminators']:
                undecided['alive'] = False
                # If the eliminator is critical, this means that if the undecided is relevant there is a problem
                if head['value'] in undecided['criticals']:
                    undecided['incompatible_eliminated'].add(head['value'])

        for son in self._get_sons(head):
            # Continue recursively
            self._mark_deads(son)

    def _step_in_undecided(self):
        # Iterate all alive undecided
        for key, undecided in self._undecideds.items():
            if undecided['alive']:
                # Perform the "mark deads" step of each node of the current dependency
                for node in self.original_nodes.values():
                    if node['value'] == key:
                        self._mark_deads(node)

    def _slash_deads(self):
        def recursive_slash(head=None):
            head = head or self._head
            pop_list = list()

            for son in self._get_sons(head):
                if self._undecideds.is_alive(son['value']):
                    recursive_slash(son)
                else:
                    # If we explicitly need to remove an incompatible node, this means there is a problem
                    if son['value'] in self._undecideds:
                        incompatible_eliminator = self._undecideds.get(son['value'])['incompatible_eliminated']
                        if incompatible_eliminator:
                            raise IncompatibleVersions('Dependency {} could not be replaced by {}'.format(
                                son['value'], ', '.join(map(str, incompatible_eliminator))))
                    pop_list.append(son['value'])

            for son_to_pop in pop_list:
                head.pop(son_to_pop)

        recursive_slash()
        self._dependencies = self._extract_values()

    def _add_manifest(self, dep, manifest):
        if dep not in self.manifests.keys():
            self.manifests[dep] = manifest
        else:
            if self.manifests[dep] != manifest:
                raise ValueError('Different manifests found for dependency {}'.format(str(dep)))
