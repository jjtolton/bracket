from naga import partition, rest, first


def defn(name, args, exps):
    res = ['def', name, ['fn', args, exps]]
    return res


def let(forms, exps):
    forms = (x for x in list(partition(2, forms))[::-1])

    def _let(forms, exps):
        for a, b in forms:
            return _let(forms, [['fn', [a], exps], b])
        return exps

    res = _let(forms, exps)
    return res


