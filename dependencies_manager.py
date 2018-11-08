from __future__ import print_function
from importer import *
from combo_tree import *


class DependenciesManager:
    def __init__(self, repo_dir, sources_json=None):
        self._repo_dir = repo_dir

        # Root directory must have base manifest
        self._base_manifest = Manifest(self._repo_dir, ComboRoot())
        assert self._base_manifest.valid_as_root(), 'Root manifest cannot be combo root'

        self._importer = Importer(sources_json)
        self._tree = ComboTree(self._importer)
        self._tree_initialized = False

    def cleanup(self):
        # Clean importer's temporary cached data after finished
        self._importer.cleanup()

    def _initialize_tree(self):
        if not self._tree.ready():
            self._tree.build(self._base_manifest)
            self._tree.disconnect_outdated_versions()

    def is_dirty(self, verbose=False):
        """
        Dirty repository means there is a difference between the current manifest on the working directory
        and the versions cloned to the working directory
        :param verbose: print outputs flag
        :return: A boolean indication for the dirty state
        """
        self._initialize_tree()

        mismatches = self._compare_content_with_tree()

        if verbose:
            if mismatches:
                print('The repository is dirty\n'
                      'Use \'combo resolve\' to update unresolved dependencies')
                for mismatch in mismatches:
                    print('\t', mismatch['type'], ':', mismatch['value'])
            else:
                print('The repository is not dirty, no need to resolve')

        return any(mismatches)

    def is_corrupted(self):
        """
        Corrupted repository means that a dependency was manually edited from the working directory.
        This cannot always be detected, as it required a cached "last resolved manifest".
        Thus, a corrupted state cannot be detected after cloning a project, or after pulling
        a version which have changed the dependencies.
        :return: A boolean indication for the corruption state
        """
        pass

    def resolve(self):
        # If the repository is not dirty, this means everything is up-to-date and there is nothing to do
        if not self.is_dirty():
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
                print('Removing deprecated dependency {}'.format(dep.name))
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

        tree_dep_names = [self.get_dependency_path(d.name).name() for d in dependencies]
        contrib_dir_names = [d.name() for d in contrib_dirs]

        mismatches = []

        # Amount
        contrib_dirs_advantage = len(contrib_dirs) > len(dependencies)
        if contrib_dirs_advantage > 0:
            mismatches += [{'type': 'More contrib directories than tree dependencies',
                            'value': contrib_dirs_advantage}]
        elif contrib_dirs_advantage < 0:
            mismatches += [{'type': 'More tree dependencies than contrib directories',
                            'value': -contrib_dirs_advantage}]

        # Directory names
        for tree_dep_name in tree_dep_names:
            if tree_dep_name not in contrib_dir_names:
                mismatches += [{'type': 'Dependency from tree missing from contrib', 'value': tree_dep_name}]
        for contrib_dir_name in contrib_dir_names:
            if contrib_dir_name not in tree_dep_names:
                mismatches += [{'type': 'Directory from contrib does not exist in dependencies tree',
                                'value': contrib_dir_name}]

        if mismatches:
            return mismatches

        """ If we got to this stage, this means the dependencies from the tree
            and the directories from contrib are the same, at least by dependency name
            (not necessarily by version and content) """

        # Sanity check
        tree_dep_names.sort()
        contrib_dir_names.sort()
        if tree_dep_names != contrib_dir_names:
            raise UnhandledComboException('Unhandled mismatch between dependency names')

        # Content
        for dep in dependencies:
            if not self._compare_dep_content(dep):
                mismatches += [{'type': 'Modified content', 'value': dep.name}]

        return mismatches
