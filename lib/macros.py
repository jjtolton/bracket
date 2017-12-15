from naga import partition

from lib.symbols import def_, fn_
from lib.utils import isa


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
    forms = (x for x in list(partition(2, forms))[::-1])

    def _let(forms, exps):
        for a, b in forms:
            return _let(forms, [['fn', [a], exps], b])
        return exps

    res = _let(forms, exps)
    return res


macro_table = {'defn': defn,
               'let': let}  ## More macros can go here
