import os
import git
import stat


def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


base_dir = os.path.join(os.path.curdir, "../")
repo_dir = os.path.abspath(os.path.join(base_dir, 'my_repo'))
if os.path.exists(repo_dir):
    rmtree(repo_dir)

pygit2_url = "https://github.com/libgit2/pygit2.git"
repo = git.Repo.clone_from(pygit2_url, repo_dir)
# repo = git.Repo(local_url)

# heads = repo.heads
# master = heads.master       # lists can be accessed by name for convenience
# print master.commit         # the commit pointed to by head called master
# master.rename('new_name')   # rename heads
# master.rename('master')


def get_version_tuple(tag):
    prefix = 'v'
    assert str(tag)[:len(prefix)] == prefix, "Invalid version tag prefix"
    return tuple(map(int, str(tag)[len(prefix):].split(".")))


def is_version(tag):
    try:
        get_version_tuple(tag)
    except (AssertionError, ValueError):
        return False
    return True


def get_latest_version(tags):
    version_tags = filter(is_version, tags)
    max_version = max(map(get_version_tuple, version_tags))
    latest_versions = filter(lambda tag: get_version_tuple(tag) == max_version, version_tags)
    assert len(latest_versions) == 1, "Multiple instances of version {} detected".format(max_version)
    return latest_versions[0]


# repo.create_tag("test")
real_version = get_latest_version(repo.tags)
fake_version = get_latest_version(["v2.9.1000", "v3.100.1"])
print "The newest version is {}, commit {}".format(real_version, real_version.commit)
