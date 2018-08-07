from poc import *
import sys


def main():
    my_path = sys.argv[1]

    contrib_dir = os.path.join(my_path, "contrib")
    if os.path.exists(contrib_dir):
        rmtree(contrib_dir)
    metadata_dir = os.path.join(my_path, ".combo")
    if os.path.exists(metadata_dir):
        rmtree(metadata_dir)

    DependenciesManager(my_path).resolve()


if __name__ == '__main__':
    main()
