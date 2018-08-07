class RequestedVersionNotFound(BaseException):
    pass


class ProjectSource:
    def __init__(self, src_type, **kwargs):
        self.src_type = src_type

        if src_type == 'git':
            self.remote_url = kwargs['url']
            self.commit_hash = kwargs['commit_hash']
        elif src_type == 'local_path':
            self.local_path = kwargs['path']
        else:
            raise TypeError('Source type {} is not supported yet'.format(src_type))
