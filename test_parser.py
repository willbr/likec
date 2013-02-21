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

    def test_ast_empty(self):
        self.assertEqual(
                ast('''
'''),
                []
                )

    def test_ast_single_statement(self):
        self.assertEqual(
                ast('''
= a 5
'''),
                [['=', 'a', '5']]
                )

    def test_ast_block(self):
        self.assertEqual(
                ast('''
def test
    return 5
'''),
                [['def', 'test', [], 'void',
                    ['return', '5']]]
                )

if __name__ == '__main__':
    unittest.main()

