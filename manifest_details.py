from combo_core import *
from combo_core.version import *
from combo_dependnecy import *
import json


class ManifestNotFound(ComboException):
    pass


class InvalidManifest(ComboException):
    pass


class ComboDependencyMismatch(ComboException):
    pass


class ManifestDetails:
    manifest_file_name = 'combo_manifest.json'
    output_dir_keyword = 'output_directory'

    name_keyword = 'name'
    version_keyword = 'version'
    dependencies_keyword = 'dependencies'
    required_manifest_keywords = [name_keyword, version_keyword, dependencies_keyword]

    dependency_name_keyword = 'name'
    required_dependency_keywords = [dependency_name_keyword]

    def __init__(self, dir_path, expected_manifest_value):
        assert isinstance(expected_manifest_value, ComboNode), 'Invalid expected manifest value type'

        self.base_path = dir_path if isinstance(dir_path, Directory) else Directory(dir_path)
        self.file_path = self.base_path.join(self.manifest_file_name).path

        if not os.path.exists(self.file_path):
            raise ManifestNotFound('{} is not a combo repository'.format(self.base_path))

        with open(self.file_path, 'r') as f:
            self.manifest = json.load(f)

        for kw in self.required_manifest_keywords:
            if kw not in self.manifest:
                raise InvalidManifest('Manifest "{}" missing keyword "{}"'.format(expected_manifest_value, kw))

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

        self.validate(expected_manifest_value)

    def validate(self, expected_manifest_value):
        if isinstance(expected_manifest_value, ComboDep):
            if self.name != expected_manifest_value.name:
                raise ComboDependencyMismatch('Manifest name mismatch. expected {}, found {}'
                                              .format(expected_manifest_value.name, self.name))
            if self.version != str(expected_manifest_value.version):
                raise ComboDependencyMismatch('Manifest {} version mismatch. expected {}, found {}'
                                              .format(self.name, str(expected_manifest_value.version), self.version))

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
