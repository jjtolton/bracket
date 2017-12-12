from naga import partition

from lib.symbols import def_, fn_


def defn(*args):

    # if len(args) == 2:
    #     name, *exps = args
    #     exps = sorted(exps, key=lambda x: len(x[0]))


    # if len(args) == 3:
    name, args, exps = args
    res = [def_, name, [fn_, args, exps]]
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


