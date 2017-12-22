import unittest

from lib.lang import parse, eval


class EvalTest(unittest.TestCase):


    def test_nested_procedures(self):
        s = '[[fn [a] [[fn [b] a] 2]] 1]'
        p = parse(s)
        res = eval(p, {})
        exp = 1
        self.assertEqual(exp, res)


if __name__ == '__main__':
    unittest.main()