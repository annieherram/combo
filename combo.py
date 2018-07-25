from poc import *
import sys


def main():
    base_dir = os.path.join(os.path.curdir, "../")
    repo_dir = os.path.abspath(os.path.join(base_dir, 'my_repo'))
    if os.path.exists(repo_dir):
        rmtree(repo_dir)

    repo_dir = "C:\Combo\combo\contrib"
    if os.path.exists(repo_dir):
        rmtree(repo_dir)

    manifest = json.load(open(sys.argv[1], 'r'))
    urls = json.load(open(sys.argv[2], 'r'))
    my_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    Combo(my_path, manifest, urls).apply()


if __name__ == '__main__':
    main()
