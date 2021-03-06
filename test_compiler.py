import unittest
import textwrap
from prefix_tokenizer import Token
from prefix_parser import map_tree_to_values
from prefix_compiler import Compiler, parse, parse_type, indent_code


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
        ast = parse('(if 1 1 0)')[0]
        ce = c.compile_if(*ast)
        self.assertEqual(
                ce.pre,
                [
                    'if (1) {',
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

    def test_compile_if_comparison(self):
        c = self.compiler
        ast = parse('(if (< 1 2) 1 0)')[0]
        ce = c.compile_if(*ast)
        self.assertEqual(
                ce.pre,
                [
                    'if (1 < 2) {',
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

    def test_compile_if_default_alternative(self):
        c = self.compiler
        ast = parse('(if 1 1)')[0]
        ce = c.compile_if(*ast)
        self.assertEqual(
                ce.pre,
                [
                    'if (1) {',
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

    def test_compile_cond(self):
        c = self.compiler
        ast = parse('''
(cond (true 1)
      (true 2)
      (true 3)
      (else 4))
''')[0]
        ce = c.compile_cond(*ast)
        self.assertEqual(
                ce.pre,
                [
                    'if (true) {',
                    [
                        'cond1000 = 1;',
                        ],
                    '} else if (true) {',
                    [
                        'cond1000 = 2;',
                        ],
                    '} else if (true) {',
                    [
                        'cond1000 = 3;',
                        ],
                    '} else {',
                    [
                        'cond1000 = 4;',
                        ],
                    '}',
                    ],
                )

        self.assertEqual(
                ce.exp,
                'cond1000',
                )

        self.assertTrue(
                'cond1000' in c.current_scope(),
                )

    def test_compile_infix_and(self):
        c = self.compiler
        and_ast = parse('(and 1 0)')[0]
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
        or_ast = parse('(or 1 0)')[0]
        ce = c.compile_expression(or_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '1 || 0',
                )

    def test_compile_prefix_not(self):
        c = self.compiler
        not_ast = parse('(not 1)')[0]
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
        eq_ast = parse('(= 1 0)')[0]
        ce = c.compile_expression(eq_ast)

        self.assertEqual(
                ce.pre,
                []
                )

        self.assertEqual(
                ce.exp,
                '1 == 0',
                )

    def test_compile_infix_pre(self):
        c = self.compiler
        eq_ast = parse('(+ 1 (if 1 1 1))')[0]
        ce = c.compile_expression(eq_ast)

        self.assertEqual(
                ce.pre,
                [
                    'if (1) {',
                    ['if1000 = 1;'],
                    '} else {',
                    ['if1000 = 1;'],
                    '}',
                    ]
                )

        self.assertEqual(
                ce.exp,
                '1 + (if1000)',
                )

    def test_compile_variable(self):
        c = self.compiler

        tests = (
                ('argc int', 'int argc'),
                ('argv (* * char)', 'char **argv'),
                ('argv (* CArray char)', 'char (*argv)[]'),
                )

        for code_input, c_output in tests:
            token_name, tokens_type = parse(code_input)[0]
            var_name = token_name.value
            var_type = parse_type(tokens_type)

            self.assertEqual(
                    c.compile_variable_declaration(var_name, var_type),
                    c_output,
                    )

    def test_global_code(self):
        c = self.compiler
        c.add_code('''
puts "hello"
''')
        c.compile()

        self.assertEqual(
                c.functions['main'].compile(),
                [
                    'int main()',
                    '{',
                    [
                        'return puts("hello");',
                        ],
                    '}',
                    ]
                )

    def test_compile_subtitution_single_argument(self):
        c = self.compiler
        eq_ast = parse('(- 5)')[0]
        ce = c.compile_expression(eq_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '-5',
                )

    def test_compile_subtitution_two_arguments(self):
        c = self.compiler
        eq_ast = parse('(- 5 5)')[0]
        ce = c.compile_expression(eq_ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '5 - 5',
                )

    def test_chained_assignment(self):
        c = self.compiler
        ast = parse('(set a b 5)')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                'a = b = 5',
                )

    def test_comparison_operator(self):
        c = self.compiler
        ast = parse('(< 0 1)')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '0 < 1',
                )

    def test_comparison_operator_many_arguments(self):
        c = self.compiler
        ast = parse('(< 0 1 2)')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '(0 < 1) && (1 < 2)',
                )

    def test_comparison_operator_many_arguments_expression(self):
        c = self.compiler
        ast = parse('(< 0 (+ 0 1) 2)')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                ['comp_exp1000 = (0 + 1);'],
                )

        self.assertEqual(
                ce.exp,
                '(0 < comp_exp1000) && (comp_exp1000 < 2)',
                )

    def test_addition(self):
        c = self.compiler
        ast = parse('(+ 0 1 2)')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '0 + 1 + 2',
                )

    def test_substitution(self):
        c = self.compiler
        ast = parse('(- 0 1 2)')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [],
                )

        self.assertEqual(
                ce.exp,
                '0 - 1 - 2',
                )


    def test_comparison(self):
        c = self.compiler

        ast = parse('< 0')[0]
        with self.assertRaises(SyntaxError):
            c.compile_expression(ast)

    def test_invalid_variable_reference(self):
        c = self.compiler

        ast = parse('+ n 0')[0]
        with self.assertRaises(SyntaxError):
            c.compile_expression(ast)

        ast = parse('< n 0')[0]
        with self.assertRaises(SyntaxError):
            c.compile_expression(ast)

    def test_compile_while(self):
        c = self.compiler
        ast = parse('''
(while 1
  1)
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    'while (1) {',
                    [
                        'while1000 = 1;',
                        ],
                    '}',
                    ],
                )

        self.assertEqual(
                ce.exp,
                'while1000',
                )

    def test_compile_prefix(self):
        c = self.compiler

        ast = parse('(set i 0)')[0]
        ce = c.compile_expression(ast)

        ast = parse('(inc i)')[0]
        ce = c.compile_expression(ast)
        self.assertEqual(ce.pre, [],)
        self.assertEqual(ce.exp, '++i',)

        ast = parse('(dec i)')[0]
        ce = c.compile_expression(ast)
        self.assertEqual(ce.pre, [],)
        self.assertEqual(ce.exp, '--i',)


        ast = parse('(post-inc i)')[0]
        ce = c.compile_expression(ast)
        self.assertEqual(ce.pre, [],)
        self.assertEqual(ce.exp, 'i++',)

        ast = parse('(post-dec i)')[0]
        ce = c.compile_expression(ast)
        self.assertEqual(ce.pre, [],)
        self.assertEqual(ce.exp, 'i--',)

        ast = parse('(not (+ 1 1))')[0]
        ce = c.compile_expression(ast)
        self.assertEqual(ce.pre, [],)
        self.assertEqual(ce.exp, '!(1 + 1)',)

    def test_compile_for(self):
        c = self.compiler
        ast = parse('''
(for (set i 1) (< i 10) (inc i)
  (printf "%d\n" i))
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    'i = 1;',
                    'while (i < 10) {',
                    [
                        'for1000 = (printf("%d\n", i));',
                        '++i;',
                        ],
                    '}',
                    ],
                )

        self.assertEqual(
                ce.exp,
                'for1000',
                )


    def test_compile_case(self):
        c = self.compiler
        ast = parse('''
(case '1'
  ('0' 0)
  ('1' 1)
  ('2' (+ 1 1))
  (default -1))
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    "switch ('1') {",
                    [
                        "case '0':",
                        [
                            'case1000 = (0);',
                            'break;',
                            ],
                        "case '1':",
                        [
                            'case1000 = (1);',
                            'break;',
                            ],
                        "case '2':",
                        [
                            'case1000 = (1 + 1);',
                            'break;',
                            ],
                        'default:',
                        [
                            'case1000 = (-1);',
                            'break;',
                            ],
                    ],
                    '}',
                    ]
                )

        self.assertEqual(
                ce.exp,
                'case1000',
                )

    def test_compile_case_fallthrough(self):
        c = self.compiler
        ast = parse('''
(case '1'
  ('0')
  ('1')
  ('2' 5)
  (default -1))
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    "switch ('1') {",
                    [
                        "case '0':",
                        "case '1':",
                        "case '2':",
                        [
                            'case1000 = (5);',
                            'break;',
                            ],
                        'default:',
                        [
                            'case1000 = (-1);',
                            'break;',
                            ],
                    ],
                    '}',
                    ]
                )

        self.assertEqual(
                ce.exp,
                'case1000',
                )

    def test_compile_each(self):
        c = self.compiler
        ast = parse('''
each n (range 10)
    printf "%d\n" n
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    'n = 0;',
                    'while (n < 10) {',
                    [
                        'each1000 = (printf("%d\n", n));',
                        'n += 1;',
                        ],
                    '}',
                    ]
                )

        self.assertEqual(
                ce.exp,
                'each1000',
                )

    def test_compile_begin(self):
        c = self.compiler
        ast = parse('''
(begin
    (set i 0)
    (while (< i 5)
        (puts "hello")
        (inc i)))
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    'i = 0;',
                    'while (i < 5) {',
                    [
                        'puts("hello");',
                        'while1000 = (++i);',
                        ],
                    '}',
                    ]
                )

        self.assertEqual(
                ce.exp,
                'while1000',
                )

    def test_compile_begin(self):
        c = self.compiler
        ast = parse('''
(begin
    (set i 0)
    (while (< i 5)
        (puts "hello")
        (inc i))
    0)
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                [
                    'i = 0;',
                    'while (i < 5) {',
                    [
                        'puts("hello");',
                        'while1000 = (++i);',
                        ],
                    '}',
                    ]
                )

        self.assertEqual(
                ce.exp,
                '0',
                )

    def test_compile_in_range(self):
        c = self.compiler
        ast = parse('''
in 1 (range 10)
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                []
                )

        self.assertEqual(
                ce.exp,
                '(0 <= 1) && (1 < 10)',
                )

    def test_compile_in_string(self):
        c = self.compiler
        ast = parse('''
in 'c' "abc"
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                []
                )

        self.assertEqual(
                ce.exp,
                "('c' == 'a') || ('c' == 'b') || ('c' == 'c')"
                )

    def test_compile_exp_in_range(self):
        c = self.compiler
        ast = parse('''
in (+ 1 2) (range 10)
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                ['in1000 = (1 + 2);']
                )

        self.assertEqual(
                ce.exp,
                '(0 <= in1000) && (in1000 < 10)',
                )

    def test_compile_exp_in_string(self):
        c = self.compiler
        ast = parse('''
in (+ 'a' 1) "abc"
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                ["in1000 = ('a' + 1);"]
                )

        self.assertEqual(
                ce.exp,
                "(in1000 == 'a') || (in1000 == 'b') || (in1000 == 'c')"
                )

    def test_compile_identity(self):
        c = self.compiler
        ast = parse('''
puts
    $ "hello"
''')[0]
        ce = c.compile_expression(ast)

        self.assertEqual(
                ce.pre,
                []
                )

        self.assertEqual(
                ce.exp,
                'puts("hello")'
                )
        
    def test_compile_macro(self):
        c = self.compiler
        c.compile_code('''
macro square (x)
    * x x

printf "%d\n" (square 2)
$ 0
''')
        c.compile_main()
        f = c.functions['main']

        self.assertEqual(
                f.compile(),
                [
                    'int main()',
                    '{',
                    [
                        'int macro__square__x1000 = 0;',
                        'true;',
                        'macro__square__x1000 = 2;',
                        'printf("%d\n", macro__square__x1000 * macro__square__x1000);',
                        'return 0;',
                        ],
                    '}',
                    ],
                )

    def test_compile_global_macro(self):
        c = self.compiler
        c.compile_code('''
def test
    square 5
    
macro square (x)
    * x x

printf "%d\n" (square 2)
$ 0
''')
        c.compile_main()
        f = c.functions['main']

        self.assertEqual(
                f.compile(),
                [
                    'int main()',
                    '{',
                    [
                        'int macro__square__x1001 = 0;',
                        'true;',
                        'macro__square__x1001 = 2;',
                        'printf("%d\n", macro__square__x1001 * macro__square__x1001);',
                        'return 0;',
                        ],
                    '}',
                    ],
                )

        f = c.functions['test']

        self.assertEqual(
                f.compile(),
                [
                    'int test()',
                    '{',
                    [
                        'int macro__square__x1000 = 0;',
                        'macro__square__x1000 = 5;',
                        'return macro__square__x1000 * macro__square__x1000;',
                        ],
                    '}',
                    ],
                )

    def test_indent_code(self):
        code = [
            'int main()',
            '{',
            [
                'puts("hello");',
                'return 0;',
                ],
            '}',
            ]

        indented_code = '\n'.join(indent_code(code))
        
        self.assertEqual(
                indented_code, textwrap.dedent('''\
                int main()
                {
                    puts("hello");
                    return 0;
                }'''))

if __name__ == '__main__':
    unittest.main()

