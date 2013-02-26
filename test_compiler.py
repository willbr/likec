import unittest
import prefix_compiler
from prefix_tokenizer import Token
from prefix_parser import map_tree_to_values
from prefix_compiler import Compiler, parse


def parse_to_values(code):
    return map_tree_to_values(parse(code))


class TestPrefixCompiler(unittest.TestCase):

    def setUp(self):
        c = Compiler()
        #c.add_standard_code()
        c.read_files()
        c.parse_code()
        c.extract_type_information()
        self.compiler = c

    def test_parse(self):
        c = self.compiler
        self.assertEqual(
                parse_to_values('''
c-def hyphen-test
    prn "hello"
''')[0],
                ['c_def', 'hyphen_test', [], 'void', ['prn','"hello"']]
                )


    def test_compile_c_def(self):
        c = self.compiler
        c.compile_code('''
c-def main
    puts "hello"
''')

        f = c.functions['main']

        self.assertEqual(
                f.compiled(),
                [
                    'void main()',
                    '{',
                    [
                        'puts("hello");',
                        ],
                    '}',
                    ],
                )

    def test_compile_c_def(self):
        c = self.compiler
        c.compile_code('(def test () int 5)')

        f = c.functions['test']

        self.assertEqual(
                f.compile(),
                [
                    'int test()',
                    '{',
                    [
                        'return 5;',
                        ],
                    '}',
                    ],
                )

    def test_redefine_error(self):
        c = self.compiler
        self.assertRaises(
                SyntaxError,
                c.compile_code,
            '''
def main
    puts "hello"

def main
    puts "hello"
''',
                )

    def test_redefine_error_global_code(self):
        c = self.compiler

        c.compile_code(
            '''
def main
    puts "hello"

puts "hello"
''')
        self.assertRaises(
                SyntaxError,
                c.compile_main,
                )

    def test_compile_if(self):
        c = self.compiler
        head, *tail = prefix_compiler.parse('(if (> 1 0) 1 0)')[0]
        ce = c.compile_if(*tail)
        self.assertEqual(
                ce.pre,
                [
                    'if (1 > 0) {',
                    [
                        'if1000 = 1;',
                        ],
                    '} else {',
                    [
                        'if1000 = 0;',
                        ],
                    '}',
                    ],
                )
        self.assertEqual(
                ce.exp,
                'if1000',
                )

        self.assertTrue(
                'if1000' in c.current_scope(),
                )

    def test_compile_infix_and(self):
        c = self.compiler
        and_ast = prefix_compiler.parse('(and 1 0)')[0]
        ce = c.compile_expression(and_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '1 && 0',
                )

    def test_compile_infix_or(self):
        c = self.compiler
        or_ast = prefix_compiler.parse('(or 1 0)')[0]
        ce = c.compile_expression(or_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '1 || 0',
                )

    def test_compile_infix_not(self):
        c = self.compiler
        not_ast = prefix_compiler.parse('(not 1)')[0]
        ce = c.compile_expression(not_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '!1',
                )

    def test_compile_infix_eq(self):
        c = self.compiler
        eq_ast = prefix_compiler.parse('(eq? 1 0)')[0]
        ce = c.compile_expression(eq_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '1 == 0',
                )
if __name__ == '__main__':
    unittest.main()

