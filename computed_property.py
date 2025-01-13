class computed_property():
    def __init__(self, *dependencies):
        super().__init__()
        self.dependencies = dependencies
        self.cache_name = f"_computed_cache_{id(self)}"
        self.state_name = f"_dependency_state_{id(self)}"

    def __call__(self, func):
        self.fget = func
        self.__doc__ = func.__doc__
        return self

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        # Initialize the cache and state if not already done
        if not hasattr(obj, self.cache_name):
            setattr(obj, self.cache_name, None)
            setattr(obj, self.state_name, {})

        cache = getattr(obj, self.cache_name)
        state = getattr(obj, self.state_name)

        # Check current state of dependencies
        current_state = {
            dep: getattr(obj, dep, None) for dep in self.dependencies
        }

        # Recalculate if state has changed
        if state != current_state:
            if self.fget is None:
                raise AttributeError("Unreadable attribute")

            cache = self.fget(obj)
            setattr(obj, self.cache_name, cache)
            setattr(obj, self.state_name, current_state)

        return cache

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("Can't set attribute")
        self.fset(obj, value)

        # Clear cache and state when the property is set
        if hasattr(obj, self.cache_name):
            delattr(obj, self.cache_name)
        if hasattr(obj, self.state_name):
            delattr(obj, self.state_name)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("Can't delete attribute")
        self.fdel(obj)

        # Clear cache and state when the property is deleted
        if hasattr(obj, self.cache_name):
            delattr(obj, self.cache_name)
        if hasattr(obj, self.state_name):
            delattr(obj, self.state_name)

    def getter(self, fget):
        self.fget = fget
        self.__doc__ = fget.__doc__
        return self

    def setter(self, fset):
        self.fset = fset
        return self

    def deleter(self, fdel):
        self.fdel = fdel
        return self