import json


def get_version_tuple(version_str, expected_prefix=''):
    assert version_str[:len(expected_prefix)] == expected_prefix, "Invalid version tag prefix: {}".format(version_str)
    return tuple(map(int, version_str[len(expected_prefix):].split(".")))


def is_version(tag, version_prefix=''):
    try:
        get_version_tuple(str(tag), version_prefix)
    except (AssertionError, ValueError):
        return False
    return True


def get_latest_version(tags, version_prefix=''):
    version_tags = [tag for tag in tags if is_version(tag, version_prefix)]
    max_version = max([get_version_tuple(str(version_tag), version_prefix) for version_tag in version_tags])
    latest_versions = filter(lambda tag: get_version_tuple(str(tag), version_prefix) == max_version, version_tags)
    assert len(latest_versions) == 1, "Multiple instances of version {} detected".format(max_version)
    return latest_versions[0]


def get_requested_version(tags, requested_version_tuple, version_prefix=''):
    version_tags = [tag for tag in tags if is_version(tag, version_prefix)]
    filtered = filter(lambda tag: get_version_tuple(str(tag), version_prefix) == requested_version_tuple, version_tags)
    assert len(filtered) == 1, "Multiple instances of version {} detected".format(requested_version_tuple)
    return filtered[0]


def version2commit(repo, name, version_str):
    json_file_name = name + '_versions.json'
    versions_dict = json.load(open(json_file_name, 'r'))

    commit = get_requested_version(repo.tags, get_version_tuple(version_str), versions_dict["prefix"])
    return commit


class MajorVersionMismatch(Exception):
    pass


def get_latest(version_strings):
    tuples = map(get_version_tuple, version_strings)
    max_version = max(tuples)

    # If there is a dependency with a different major number, raise an error
    if any(version[0] < max_version[0] for version in tuples):
        raise MajorVersionMismatch

    return filter(lambda v: get_version_tuple(v) == max_version, version_strings)[0]

