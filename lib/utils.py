def ara(x, y):
    return all(isa(e, y) for e in x)


def isa(x, y):
    return isinstance(x, y)


def to_string(x):
    return str(x)