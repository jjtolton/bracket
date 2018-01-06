from naga import partition, mapv

from lib.destructure import destruct
from lib.symbols import def_, fn_, quote_, begin_
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


def let(forms, *exps):
    if forms == []:
        return _let([], [], exps)
    forms = mapv(list, partition(2, forms))
    return _let(*zip(*forms), [begin_, *exps])


def _let(bindings, args, exps):
    forms = destruct(bindings, args)[::-1]

    def _let_(forms, exps):
        for a, b in forms:
            return _let_(forms, [['fn', [a], exps], b])
        return exps

    if forms == []:
        return exps

    return _let_(iter(forms), exps)


macro_table = {'defn': defn,
               'quote': quote,
               'let': let}  ## More macros can go here
