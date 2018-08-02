from utils import *
from .source_locator_general import *


class GitTagsVersionFormatter(VersionFormatter):
    def __init__(self, prefix_format):
        VersionFormatter.__init__(self, prefix_format)

    def is_version(self, tag):
        try:
            self.get_as_tuple(str(tag))
        except (AssertionError, ValueError):
            return False
        return True

    def get_version_tags(self, tags):
        return filter(self.is_version, tags)

    def get_requested_version(self, tags, requested_version_tuple):
        version_tags = self.get_version_tags(tags)
        try:
            return xfilter(lambda tag: self.get_as_tuple(str(tag)) == requested_version_tuple, version_tags)
        except ObjectNotFound as e:
            raise RequestedVersionNotFound(e)

    def get_latest_from_tags(self, tags):
        version_tags = self.get_version_tags(tags)
        max_version = max(map(self.get_as_tuple, map(str, version_tags)))
        return xfilter(lambda tag: self.get_as_tuple(str(tag)) == max_version, version_tags)


class GitTagsSourceSupplier:
    def __init__(self, project_name, project_details):
        self._project_name = project_name
        self._remote_url = project_details['url']
        self._tags_prefix = project_details.get('tags_prefix') or ''  # If there is no prefix key, use empty string

    def get_source(self, version_str):
        commit_hash = self._search_tags(version_str)
        source = ProjectSource('git', url=self._remote_url, commit_hash=commit_hash)
        return source

    def _search_tags(self, version_str):
        import git

        working_dir = os.path.dirname(os.path.realpath(__file__))
        dst_path = os.path.join(working_dir, self._project_name.lower().replace(' ', '_'))

        repo = git.Repo.clone_from(self._remote_url, dst_path)

        requested_version_tuple = VersionFormatter().get_as_tuple(version_str)
        selected_tag = GitTagsVersionFormatter(self._tags_prefix).\
            get_requested_version(repo.tags, requested_version_tuple)

        # The commit hash has to be stored now, because after folder deletion there is no way to get it
        commit_hash = str(selected_tag.commit)

        del selected_tag, repo
        rmtree(dst_path)
        return commit_hash
