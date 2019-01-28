from combo_core import *
from .combo_nodes import *
import json


class ManifestNotFound(ComboException):
    pass


class InvalidManifest(ComboException):
    pass


class ComboDependencyMismatch(ComboException):
    pass


class Manifest:
    manifest_file_name = 'combo_manifest.json'
    output_dir_keyword = 'output_directory'

    name_keyword = 'name'
    version_keyword = 'version'
    dependencies_keyword = 'dependencies'
    required_manifest_keywords = [name_keyword, version_keyword, dependencies_keyword]

    dependency_name_keyword = 'name'
    required_dependency_keywords = [dependency_name_keyword]

    def __init__(self, dir_path, expected_combo_node=None):
        """
        :param dir_path: The path to the combo manifest json file
        :param expected_combo_node: The expected combo node value of the current manifest
        """

        self.base_path = dir_path
        self.file_path = self.base_path.join(self.manifest_file_name).path

        if not os.path.exists(self.file_path):
            raise ManifestNotFound('"{}" is not a combo repository'.format(self.base_path))

        with open(self.file_path, 'r') as f:
            self.manifest = json.load(f)

        for kw in self.required_manifest_keywords:
            if kw not in self.manifest:
                raise InvalidManifest('The manifest of "{}" missing keyword "{}"'.format(self.base_path, kw))

        self.name = self.manifest[self.name_keyword]
        self.version = self.manifest[self.version_keyword]

        dependencies_list = self.manifest[self.dependencies_keyword]
        self.dependencies = dict()
        for dep in dependencies_list:
            if not all(dep_kw in dep for dep_kw in self.required_dependency_keywords):
                raise InvalidManifest('Dependency "{}" is missing required attributes'.format(dep))
            self.dependencies[dep[self.dependency_name_keyword]] = dep

        if self.valid_as_root():
            self.output_dir = self.base_path.join(self.manifest[self.output_dir_keyword])

        if expected_combo_node is not False:
            self.validate(expected_combo_node if expected_combo_node is not None else dir_path.name())

    def validate(self, expected):
        if isinstance(expected, string_types):
            if ComboDep.normalize_name_dir(self.name) != expected:
                raise ComboDependencyMismatch('Manifest name mismatch for directory {}, found name {}'
                                              .format(expected, self.name))
        elif isinstance(expected, ComboNode):
            if isinstance(expected, ComboDep):
                if self.name != expected.name:
                    raise ComboDependencyMismatch('Manifest name mismatch. expected {}, found {}'
                                                  .format(expected.name, self.name))
                if self.version != str(expected.version):
                    raise ComboDependencyMismatch('Manifest "{}" version mismatch. expected {}, found {}'
                                                  .format(self.name, str(expected.version), self.version))
        else:
            raise UnhandledComboException('Could not validate manifest with value type {}'.format(type(expected)))

    @staticmethod
    def is_combo_repo(dir_path):
        try:
            Manifest(dir_path)
            return True
        except ManifestNotFound:
            return False
        # The rest of the exceptions wouldn't mean that this is not a combo repository
        except ComboException:
            return True

    def sons(self):
        return list(self.dependencies.values())

    def valid_as_root(self):
        return self.output_dir_keyword in self.manifest

    def valid_as_lib(self):
        return True  # TODO: In the future, this will be false for versions such as 1.*

    def __eq__(self, other):
        assert isinstance(other, type(self))
        return dicts_equal(self.manifest, other.manifest)

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return 'Manifest at {}'.format(self.file_path)
