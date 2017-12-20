from naga import partition

from lib.destructure import destructure
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
    try:
        forms = destructure(forms)
    except IndexError:
        forms = destructure([a for b in forms for a in b])

    def _let(forms, exps):
        for a, b in forms:
            return _let(forms, [['fn', [a], exps], b])
        return exps

    nforms = iter(list(partition(2, destructure(forms)))[::-1])
    return _let(nforms, exps)

def and_(*args):
    if len(args) == 1:
        return args[0]
    return [if_, args[0],
            [Symbol('and'), *args[1:]],
            args[0]]


def or_(*args):
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

