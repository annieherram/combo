class ComboDep:
    def __init__(self, project_name, version):
        self.name = project_name
        self.version = version

    def as_tuple(self):
        return self.name, self.version

    def __str__(self):
        return "Project name: {}\n" \
               "Version number: {}".format(self.name, self.version)


if __name__ == '__main__':
    first = ComboDep(1, 2)
    print first
    second = ComboDep(*first.as_tuple())
    print second
