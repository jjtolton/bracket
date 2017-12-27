from naga import partition, first, second, rest, filterv

from lib.special_forms import KeyWord
from lib.symbols import Symbol, quote_
from lib.utils import isa, AutoGenSym


def destruct(bindings, args, ag=None):
    ag = ag or AutoGenSym()

    def vector_bindings(b, v):
        res = []
        if isa(b, (Symbol, str)):
            res.extend(symbol_binding(b, v))
        if isa(b, list):
            nb = ag('vec_')
            res.extend(symbol_binding(nb, v))

            # "-as" directive
            if len(b) >= 3 and b[-2] == KeyWord('as') and isa(b[-1], Symbol):
                ba = b[-1]
                b = b[:-2]
                res.extend(symbol_binding(ba, nb))

            # variable arrity directive
            if len(b) >= 2 and b[-2] == '.' and isa(b[-1], Symbol):
                vargsn = b[-1]
                b = b[:-2]
                res.extend(symbol_binding(vargsn, [Symbol('dropv'), len(b), nb]))

            res.extend([[x, [Symbol('get'), nb, i]] for i, x in enumerate(b)])
            res = res[:1] + destruct(*zip(*res[1:]), *[ag])

        return res

    def symbol_binding(b, v):
        return [[b, v]]

    if isa(bindings, (Symbol, str)):
        return symbol_binding(bindings, args)

    if len(bindings) == 0 or len(args) == 0:
        return []

    if isa(bindings, (Symbol, str)):
        b = bindings
    else:
        b = first(bindings)

    v = first(args)

    if b == '.':
        # TODO: trouble spot
        return destruct(first(rest(bindings)), list(args), ag)

    if isa(b, list):
        # print('vector_binding: ', b, v, rest(bindings), rest(args))
        return vector_bindings(b, v) + destruct(rest(bindings), rest(args), ag)

    if isa(b, (Symbol, str)):
        # print('symbol_binding: ', b, v, rest(bindings), rest(args))
        return symbol_binding(b, v) + destruct(rest(bindings), rest(args), ag)


def tests():
    # print(destruct('a', 1))
    # print(destruct(['a'], [1]))
    # print(destruct(['a', 'b'], [1, 2]))
    # print(destruct([['a', 'b']], [[1, 2]]))
    # print(destruct([['a', 'b', Symbol('as'), Symbol('x')]], [[1, 2]]))

    # for a, b in destruct([['a', 'b'], 'c'], [[1, 2], 3]):
    #     print(a, b)


    # for a, b in destruct([['a', 'b']], [[1, 2]]):
    #     print(a, b)

    # for x in destruct([[['a', 'b'], 'c']], [[[1, 2], 3]]):
    #     print(x)

    # for a, b in destruct([[['a', 'b'], 'c'], [['d', 'e']]], [[[1, 2], 3], [[4, 5]]]):
    #     print(a, b)

    # for a, b in destruct(['xs', ['a', 'b']], [[1, 2, 3], 'xs']):
    #     print(a, b)

    for a, b in destruct(
            [['a', 'b', '.', 'xs'],
             ['d', 'e']],

            [[1, 2, 3, 4, 5],
             'xs']):
        print(a, b)


if __name__ == '__main__':
    tests()
