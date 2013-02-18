import unittest
from prefix_parser import ast

class TestPrefixParser(unittest.TestCase):

    def test_lexp_def_function(self):
        self.assertEqual(
                ast('''
def main
    prn "hello"
                ''')[0],
                ['def', 'main', [], 'void', ['prn','"hello"']]
                )

    def test_sexp_def_function(self):
        self.assertEqual(
                ast('''
(def main () void
    (prn "hello"))
                ''')[0],
                ['def', 'main', [], 'void', ['prn','"hello"']]
                )

if __name__ == '__main__':
    unittest.main()

