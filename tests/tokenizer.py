import io
import unittest

from lib.classes import InPort


class TokenTest(unittest.TestCase):
    def setUp(self):
        self.easy_token = '[def a 5]'
        self.fexp = '[def foo [fn [x] x]]'
        self.string = "'abcdef blah blah [sref] [sef [sef] ] !@$#@$ qq4wtgdfsdfg'"
        self.fstring = '[def pfoo [fn [f] [fn [x] [print \'pfoo\'] [apply f x]]]]'
        self.comment = r'[foo \\* hey *\\ 1]'

    @staticmethod
    def port(x):
        return InPort(io.StringIO(x))

    def test_parse_easy_token(self):
        t = io.StringIO(self.easy_token)
        p = InPort(t)

        expected = ['[', 'def', 'a', '5', ']']
        res = list(p)
        self.assertEqual(expected, res)

    def test_nested_token(self):
        t = io.StringIO(self.fexp)
        p = InPort(t)
        expected = ['[', 'def', 'foo', '[', 'fn', '[', 'x', ']', 'x', ']', ']']
        res = list(p)
        self.assertEqual(expected, res)

    def test_parse_string(self):
        t = io.StringIO(self.string)
        p = InPort(t)
        res = list(p)
        expected = ["'abcdef blah blah [sref] [sef [sef] ] !@$#@$ qq4wtgdfsdfg'"]
        self.assertEqual(expected, res)

    def test_string_in_fn(self):
        p = InPort(io.StringIO(self.fstring))
        expected = ['[', 'def', 'pfoo', '[', 'fn', '[', 'f', ']', '[', 'fn', '[', 'x', ']', '[', 'print', "'pfoo'", ']',
                    '[', 'apply', 'f', 'x', ']', ']', ']', ']']
        res = list(p)
        self.assertEqual(expected, res)


if __name__ == '__main__':
    unittest.main()
