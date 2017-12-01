import unittest

from lib.classes import Env


class EvalTest(unittest.TestCase):

    def test_env_nesting(self):
        env = Env()
        env['a'] = 'a'
        env2 = Env(outer=env)
        env2['b'] = 'b'
        self.assertEqual(env['a'], 'a')
        self.assertEqual(env2['a'], 'a')
        with self.assertRaises(TypeError):
            env['b']
        self.assertEqual(env2['b'], 'b')


if __name__ == '__main__':
    unittest.main()

