from utils import *
import json


class ManifestDetails:
    manifest_file_name = 'combo_manifest.json'

    def __init__(self, dir_path):
        self.base_path = dir_path
        self.file_path = os.path.join(dir_path, ManifestDetails.manifest_file_name)
        if not self.exists():
            return

        with open(self.file_path, 'r') as f:
            self.manifest = json.load(f)

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

    def __eq__(self, other):
        assert isinstance(other, type(self))
        return dicts_equal(self.manifest, other.manifest)

    def __ne__(self, other):
        return not self == other
