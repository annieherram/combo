from __future__ import print_function
from importer import *
from combo_tree import *


class CorruptedDependency(ComboException):
    pass


class NonExistingCachedPath(NonExistingLocalPath):
    pass


class DependenciesManager:
    MISMATCH_TYPES = {
        'More contrib': 'More contrib directories than tree dependencies',
        'More tree': 'More tree dependencies than contrib directories',
        'Missing from contrib': 'Dependency from tree missing from contrib',
        'Missing from tree': 'Directory from contrib does not exist in dependencies tree',
        'Modified content': 'Modified content'
    }

    def __init__(self, repo_dir, sources_json=None):
        self._repo_dir = repo_dir

        # Root directory must have base manifest
        self._base_manifest = Manifest(self._repo_dir, ComboRoot())
        assert self._base_manifest.valid_as_root(), '{} is not valid as root manifest'.format(self._base_manifest)

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

        # If a dependency is corrupted, it's not considered dirty since the problem is not due to manifest update
        if self.is_corrupted():
            # TODO: A dependency can be both dirty an corrupted if the reason is a different dependency.
            # We still have to check the rest of them for dirtiness
            print('No informative message yet. repository is corrupted')
            return False

        mismatches = self._content_to_tree_mismatches()

        if verbose:
            if mismatches:
                print('The repository is dirty\n'
                      'Use "combo resolve" to update unresolved dependencies')
                for mismatch in mismatches:
                    print('\t', mismatch['type'], ':', mismatch['value'])
            else:
                print('The repository is not dirty, no need to resolve')

        return any(mismatches)

    def check_corruption(self):
        """
        Corrupted repository means that a dependency was manually edited from the working directory.
        Our way to detect this scenario is that we have a dependency that its content
        differs from the content of the version specified is its manifest.
        Keep in mind, manual edit will not always be recognized in this case,
        as a dependency which was manually replaced to a newer version, a dependency which was manually removed,
        or added with a valid content, would not be detected as corrupted.
        The reason this is "the best we can do", is because we don't have the "last resolved manifest".
        """
        for contrib_dir in self._output_directories():
            dep_manifest = Manifest(contrib_dir)
            combo_dep = ComboDep(dep_manifest.name, dep_manifest.version)

            expected_hash = self._importer.get_dep_hash(combo_dep)
            actual_hash = hash(contrib_dir)

            if actual_hash != expected_hash:
                raise CorruptedDependency('Content found in directory "{}" does not match expected content of "{}"'
                                          .format(contrib_dir, combo_dep))

    def is_corrupted(self):
        """
        See more at the 'check_corruption' function.
        :return: A boolean indication for the corruption state
        """
        try:
            self.check_corruption()
            return False
        except CorruptedDependency:
            return True

    def resolve(self, force=False):
        # Make sure the repository is not corrupted before resolving
        if not force:
            self.check_corruption()

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

    def _output_directories(self):
        return list(filter(Manifest.is_combo_repo, self._base_manifest.output_dir.sons()))

    def _extern_from_tree(self):
        dependencies = self._tree.values()
        self._check_for_multiple_versions(dependencies)

        for dep in dependencies:
            try:
                if self._dep_content_equals(dep):
                    continue
                print('Removing deprecated dependency {}'.format(dep.name))
                self.get_dependency_path(dep.name).delete()

            except NonExistingLocalPath:
                pass

            self._extern_dependency(dep)

        # Clear irrelevant dependencies
        tree_dir_names = [self.get_dependency_path(d.name).name() for d in dependencies]
        for contrib_dir in self._output_directories():
            if contrib_dir.name() not in tree_dir_names:
                contrib_dir.delete()

    def _dep_content_equals(self, dep):
        contrib_dir = self.get_dependency_path(dep.name)
        cached_dir = self._importer.get_cached_path(dep)

        if not contrib_dir.exists():
            raise NonExistingLocalPath('Comparing content of non existing contrib directory {}'.format(contrib_dir))
        if not cached_dir.exists():
            raise NonExistingLocalPath('Comparing content of non existing cached directory {}'.format(cached_dir))

        return contrib_dir == cached_dir

    def _content_to_tree_mismatches(self):
        contrib_dirs = self._output_directories()
        dependencies = self._tree.values()

        tree_dep_names = [self.get_dependency_path(d.name).name() for d in dependencies]
        contrib_dir_names = [d.name() for d in contrib_dirs]

        mismatches = []

        # Amount
        contrib_dirs_advantage = len(contrib_dirs) > len(dependencies)
        if contrib_dirs_advantage > 0:
            mismatches += [{'type': self.MISMATCH_TYPES['More contrib'],
                            'value': contrib_dirs_advantage}]
        elif contrib_dirs_advantage < 0:
            mismatches += [{'type': self.MISMATCH_TYPES['More tree'],
                            'value': -contrib_dirs_advantage}]

        # Directory names
        for tree_dep_name in tree_dep_names:
            if tree_dep_name not in contrib_dir_names:
                mismatches += [{'type': self.MISMATCH_TYPES['Missing from contrib'], 'value': tree_dep_name}]
        for contrib_dir_name in contrib_dir_names:
            if contrib_dir_name not in tree_dep_names:
                mismatches += [{'type': self.MISMATCH_TYPES['Missing from tree'], 'value': contrib_dir_name}]

        if not mismatches:
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
            if self.get_dependency_path(dep.name).name() in contrib_dir_names:
                if not self._dep_content_equals(dep):
                    mismatches += [{'type': self.MISMATCH_TYPES['Modified content'], 'value': dep.name}]

        return mismatches
