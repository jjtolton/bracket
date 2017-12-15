from lib.macros import let
from lib.symbols import Symbol
from lib.utils import isa


def prestruct(parms, args):
    if isa(parms, (Symbol, str)):
        return [parms, args]

    if len(parms) == 0:
        return []

    if len(parms) == 1:
        p = parms[0]
        a = args[0]

        if isa(p, list):
            if len(p) == 0:
                return []
            elif p[0] == '.':
                return prestruct([p[1]], a)

            return prestruct(p[0], a[0]) + prestruct(p[1:], a[1:])

        if isa(p, set):
            p = list(p)
            if len(p) == 0:
                return []
            return prestruct(p[0], a[p[0]]) + prestruct([set(p[1:])], [a])

        if isa(p, dict):
            items = list(p.items())
            if len(items) == 0:
                return []
            k, v = items[0]
            return prestruct([k], [a[v]]) + prestruct([dict(items[1:])], [a])

        res = prestruct(p, a)
        return res

    else:
        return prestruct(parms[:1], args[:1]) + prestruct(parms[1:], args[1:])


def destruct(parms, args, exps):
    destruct = prestruct(parms, args)
    return let(destruct, exps)


def tests():
    assert prestruct(['a'], [1]) == ['a', 1]
    assert prestruct(['a', 'b'], [1, 2]) == ['a', 1, 'b', 2]
    assert prestruct([['a', 'b']], [[1, 2]]) == ['a', 1, 'b', 2]
    assert prestruct([['a', 'b']], [[1, 2, 3]]) == ['a', 1, 'b', 2]
    assert prestruct([['a', 'b'], 'c'], [[1, 2, 3], 4]) == ['a', 1, 'b', 2, 'c', 4]
    assert prestruct([{'a'}], [{'a': 1}]) == ['a', 1]
    assert prestruct([{'a'}], [{'a': 1}]) == ['a', 1]
    assert prestruct([{'a', 'b'}], [{'a': 1, 'b': 2}]) in [['a', 1, 'b', 2], ['b', 2, 'a', 1]]
    assert prestruct([{'a': 'a'}], [{'a': 1}]) == ['a', 1]
    assert (destruct([['a', 'b'], 'c'], [[1, 2], 3], 'b') ==
            [['fn', ['a'], [['fn', ['b'], [['fn', ['c'], 'b'], 3]], 2]], 1])


if __name__ == '__main__':
    tests()
