from functools import wraps

class APISpec(object):

    def __init__(self, *args, **kwargs):
        self.metadata = kwargs
        self.registry = {}

    def to_dict(self):
        return self.metadata

    def annotate(self, webargs=None):
        def decorator(func):
            self.registry[func.__name__] = webargs
            self.metadata.update(self.registry)
            @wraps(func)
            def wrapper(func, *args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
