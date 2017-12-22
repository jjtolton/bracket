import unittest

from bracket import Symbol, Definition
from lib.lang import parse, Procedure


class ParseTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_parse_definition(self):
        def_ = '[def a 5]'
        res = parse(def_)
        self.assertTrue(isinstance(res, Definition))
        assert isinstance(res, Definition)
        self.assertEqual(res.name, 'a')
        self.assertEqual(res.body.val, 5)

    def test_parse_fn_definition(self):
        d = '[def foo [fn [a b] a]]'
        res = parse(d)
        assert isinstance(res, Definition)
        assert isinstance(res.body, Procedure)
        self.assertTrue(isinstance(res, Definition))
        self.assertTrue(isinstance(res.body, Procedure))
        self.assertEqual(res.body.parms, ['a', 'b'])
        self.assertEqual(res.body.body, ['a'])
        for x in res.body.body + res.body.parms:
            self.assertTrue(isinstance(x, Symbol))


