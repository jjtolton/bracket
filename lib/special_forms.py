from naga import get, nil

from lib.utils import isa


class HashMap(dict):
    def __call__(self, x):
        return get(self, x)


class Set(set):
    def __call__(self, x):
        return Set.get(self, x)

    def __repr__(self):
        return repr(set(self))

    @staticmethod
    def get(x, k, not_found=nil):
        return k if k in x else None if not_found is nil else not_found


class KeyWord(str):
    def __repr__(self):
        return f'-{super().__repr__()[1:-1]}'

    def __str__(self):
        return f'-{super().__str__()}'

    def __call__(self, x):
        return get(x, self)
