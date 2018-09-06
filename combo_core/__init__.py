from .utils import *


class ComboException(BaseException):
    pass


class RequestedVersionNotFound(ComboException):
    pass
