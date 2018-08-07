import pygit2
import gc
import os


def clone(remote_url, dst_path, ref=None):
    father_dir = os.path.join(*os.path.split(dst_path)[:-1])
    if not os.path.exists(father_dir):
        os.makedirs(father_dir)

    """, checkout_branch=self.dep_src.commit_hash"""
    repo = pygit2.clone_repository(remote_url, dst_path)

    # We must manually call the garbage collector to be able to delete the '.git' directory
    # TODO: Temp
    if ref:
        del repo
        gc.collect()
    else:
        print(repo)
        return repo
