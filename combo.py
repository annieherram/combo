from poc import *
import sys


def main():
    repo_dir = "C:\Combo\my_repos\my_exec"
    contrib_dir = os.path.join(repo_dir, "contrib")
    if os.path.exists(contrib_dir):
        rmtree(contrib_dir)

    my_path = sys.argv[1]
    urls = json.load(open("C:\Combo\my_repos\my_exec\urls.json", 'r'))

    Combo(my_path, urls).resolve()


if __name__ == '__main__':
    main()
