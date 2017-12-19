from naga import partition

from lib.destructure import destructure
from lib.symbols import def_, fn_, quote_
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
    forms = destructure(forms)

    def _let(forms, exps):
        for a, b in forms:
            return _let(forms, [['fn', [a], exps], b])
        return exps

    nforms = iter(list(partition(2, destructure(forms)))[::-1])
    return _let(nforms, exps)







macro_table = {'defn': defn,
               'quote': quote,
               'let': let}  ## More macros can go here


def tests():
    from bracket import parse

    print(str(parse('[let [[a b] /[1 2]] a]')).replace("'", '').replace(',', ''))


if __name__ == '__main__':
    tests()
