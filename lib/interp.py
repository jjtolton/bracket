import io

from bracket import read, parse


def reflect(x):
    return x


def reader(x):
    return read(io.StringIO(x))


def parser(x):
    return parse(reader(x))
