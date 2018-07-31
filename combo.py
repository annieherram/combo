from poc import *
import sys


def main():
    my_path = sys.argv[1]

    contrib_dir = os.path.join(my_path, "contrib")
    if os.path.exists(contrib_dir):
        rmtree(contrib_dir)

    Combo(my_path).resolve()


if __name__ == '__main__':
    main()
