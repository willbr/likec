import unittest
from prefix_parser import ast, map_tree_to_values

class TestPrefixParser(unittest.TestCase):

    def test_lexp_def_function(self):
        a = map_tree_to_values(ast('''
c-def main
    prn "hello"
                ''')[0])

        self.assertEqual(
                a,
                ['c-def', 'main', [], 'void', ['prn','"hello"']]
                )

    def test_sexp_def_function(self):
        self.assertEqual(
                map_tree_to_values(ast('''
(c-def main () void
    (prn "hello"))
                ''')[0]),
                ['c-def', 'main', [], 'void', ['prn','"hello"']]
                )

    def test_sexp_def_function(self):
        self.assertEqual(
                map_tree_to_values(ast('''
def test
    + 5 5
                ''')[0]),
                ['def', 'test', [], 'int', ['+','5', '5']]
                )

    def test_ast_empty(self):
        self.assertEqual(
                ast('''
'''),
                []
                )

    def test_ast_single_statement(self):
        self.assertEqual(
                map_tree_to_values(ast('''
= a 5
''')),
                [['=', 'a', '5']]
                )

    def test_ast_block(self):
        self.assertEqual(
                map_tree_to_values(ast('''
c-def test
    return 5
''')),
                [['c-def', 'test', [], 'void',
                    ['return', '5']]]
                )

if __name__ == '__main__':
    unittest.main()

