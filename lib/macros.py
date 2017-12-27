from naga import partition, mapv

from lib.destructure import destruct
from lib.symbols import def_, fn_, quote_, if_, Symbol, let_
from lib.utils import isa


def quote(sym):
    return [quote_, sym]


def defn(*args):
    name, *exps = args
    # @formatter:off
    if (len(exps) == 2 and
        isa(exps[0], list) and
        len(exps[0]) == 0):
        return [def_, name, [fn_, [[], exps[1]]]]
    # @formatter:on
    res = [def_, name, [fn_, *exps]]
    return res


def let(forms, exps):
    forms = mapv(list, partition(2, forms))
    return _let(forms, exps)


def _let(forms, exps):
    forms = destruct(*zip(*forms))[::-1]

    def _let_(forms, exps):
        for a, b in forms:
            return _let_(forms, [['fn', [a], exps], b])
        return exps

    return _let_(iter(forms), exps)


def and_(*args):
    if len(args) == 0:
        return True
    if len(args) == 1:
        return args[0]
    return [if_, args[0],
            [Symbol('and'), *args[1:]],
            args[0]]


def or_(*args):
    if len(args) == 0:
        return True
    if len(args) == 1:
        return args[0]
    return [if_, args[0],
            args[0],
            [Symbol('or'), *args[1:]]]


macro_table = {'defn': defn,
               'and': and_,
               'or': or_,
               'quote': quote,
               'let': let}  ## More macros can go here
