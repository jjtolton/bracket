from naga import partition, mapv, partial

from lib.destructure import destruct
from lib.symbols import def_, fn_, quote_, do_, Symbol, quasiquote_, unquotesplicing_, unquote_
from lib.utils import isa, AutoGenSym


def quote(sym):
    return [quote_, sym]


def defn(name, *exps):
    res = [def_, name, [fn_, name, *exps]]
    return res


def let(forms, *exps):
    if forms == []:
        return _let([], [], exps)
    forms = mapv(list, partition(2, forms))
    return _let(*zip(*forms), [do_, *exps])


def _let(bindings, args, exps):
    forms = destruct(bindings, args)[::-1]

    def _let_(forms, exps):
        for a, b in forms:
            return _let_(forms, [['fn', [a], exps], b])
        return exps

    if forms == []:
        return exps

    return _let_(iter(forms), exps)


def letfn(bindings, body):
    return [Symbol('do'), *[[Symbol('defn'), fname, args, *fbody] for fname, args, *fbody in bindings], body]



def loop(bindings, body):
    g = AutoGenSym()
    fname = g('f__')

    def recur_replace(exp):
        if str(exp) == 'recur':
            return Symbol('loop')
        elif isinstance(exp, list) and len(exp) >= 1:
            v = recur_replace(exp[0])
            if v == Symbol('loop'):
                return [Symbol(fname), *exp[1:]]
            else:
                return [v] + recur_replace(exp[1:])
        else:
            return exp

    rbody = recur_replace(body)
    args, parms = zip(*partition(2, bindings))
    return [Symbol('letfn'), [[fname, list(args), rbody]], [Symbol('let'), bindings, rbody]]


if __name__ == '__main__':
    print(loop(['a', 'a'], ['if', ['=', 'a', 1], 'a', ['recur', ['dec', 'a']]]))

macro_table = {'defn': defn,
               'quote': quote,
               'letfn': letfn,
               'loop': loop,
               # 'recur': recur,
               'let': let}  ## More macros can go here
