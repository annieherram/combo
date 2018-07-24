from poc import *


def main():
    repo_dir = "C:\Combo\combo\contrib"
    if os.path.exists(repo_dir):
        rmtree(repo_dir)

    manifest = json.load(open(sys.argv[1], 'r'))
    urls = json.load(open(sys.argv[2], 'r'))

    Combo(manifest, urls).sync()


if __name__ == '__main__':
    main()
