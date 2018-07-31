from servers.project_name_to_url import *


server_directory = os.path.dirname(os.path.realpath(__file__))


class MajorVersionMismatch(Exception):
    pass


class VersionFormatter:
    def __init__(self, prefix_format=''):
        self._prefix = prefix_format

    def get_as_tuple(self, version_str):
        assert version_str[:len(self._prefix)] == self._prefix, \
            "Version string is expected to start with the prefix '{}'".format(version_str)
        return tuple(map(int, version_str[len(self._prefix):].split(".")))

    def is_version(self, tag):
        try:
            self.get_as_tuple(str(tag))
        except (AssertionError, ValueError):
            return False
        return True

    def get_version_tags(self, tags):
        return filter(self.is_version, tags)

    def get_latest_version(self, tags):
        version_tags = self.get_version_tags(tags)
        max_version = max(map(self.get_as_tuple, map(str, version_tags)))
        return xfilter(lambda tag: self.get_as_tuple(str(tag)) == max_version, version_tags)

    def get_requested_version(self, tags, requested_version_tuple):
        version_tags = self.get_version_tags(tags)
        return xfilter(lambda tag: self.get_as_tuple(str(tag)) == requested_version_tuple, version_tags)

    def get_latest(self, version_strings):
        tuples = map(self.get_as_tuple, version_strings)
        max_version = max(tuples)

        # If there is a dependency with a different major number, raise an error
        # TODO: Remove comment
        # if any(version[0] < max_version[0] for version in tuples):
        #     raise MajorVersionMismatch

        return filter(lambda v: self.get_as_tuple(v) == max_version, version_strings)[0]


class CommitSupplier:
    TAGS_PREFIX_KEY = 'prefix'

    def __init__(self, conversion_json):
        with open(conversion_json, 'r') as f:
            self._converter = json.load(f)

    def get_commit(self, repo_name, version_str):
        if repo_name not in self._converter:
            return self._search_tags(repo_name, version_str)

        project_converter = self._converter[repo_name]
        if self.TAGS_PREFIX_KEY in project_converter:
            prefix = project_converter[self.TAGS_PREFIX_KEY]
            return self._search_tags(repo_name, version_str, tags_prefix=prefix)

        if version_str not in project_converter:
            raise KeyError("Requested version {} not found for {} repository".format(version_str, repo_name))

        return project_converter[version_str]

    @staticmethod
    def _search_tags(repo_name, version_str, tags_prefix=''):
        import git

        dst_path = os.path.join(server_directory, repo_name)

        remote = project_name_to_url(repo_name)
        repo = git.Repo.clone_from(remote, dst_path)

        req_version_tuple = VersionFormatter().get_as_tuple(version_str)
        commit = VersionFormatter(tags_prefix).get_requested_version(repo.tags, req_version_tuple)

        rmtree(dst_path)
        return commit


supplier = CommitSupplier(os.path.join(server_directory, 'versions.json'))


def get_commit(repo_name, version_str):
    # This should be a server with TCP requests instead
    return supplier.get_commit(repo_name, version_str)
