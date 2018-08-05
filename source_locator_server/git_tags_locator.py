from .source_locator_general import *
from version import *


class GitTagsVersionFormatter:
    def __init__(self, tags_prefix):
        self._tags_prefix = tags_prefix

    def is_version(self, tag):
        try:
            Version(str(tag), self._tags_prefix)
        except:
            return False
        return True

    def get_version_tags(self, tags):
        return filter(self.is_version, tags)

    def find_tag(self, tags, requested_version):
        version_tags = self.get_version_tags(tags)
        try:
            return xfilter(lambda tag: Version(str(tag), self._tags_prefix) == requested_version, version_tags)
        except ObjectNotFound as e:
            raise RequestedVersionNotFound(e)

    def latest_tag(self, tags):
        version_tags = self.get_version_tags(tags)
        versions = (Version(str(tag), self._tags_prefix) for tag in tags)
        max_version = max(versions)
        return xfilter(lambda tag: str(tag) == max_version.as_string(), version_tags)


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

        requested_version = Version(version_str)
        selected_tag = GitTagsVersionFormatter(self._tags_prefix).find_tag(repo.tags, requested_version)

        # The commit hash has to be stored now, because after folder deletion there is no way to get it
        commit_hash = str(selected_tag.commit)

        del selected_tag, repo
        rmtree(dst_path)
        return commit_hash
