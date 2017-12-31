from naga import get


class HashMap(dict):

    def __call__(self, x):
        return get(self, x)


class KeyWord(str):
    def __repr__(self):
        return f'-{super().__repr__()}'

    def __str__(self):
        return f'-{super().__str__()}'

    def __call__(self, x):
        return get(x, self)
