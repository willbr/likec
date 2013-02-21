import unittest
import prefix_compiler
from prefix_compiler import Compiler

class TestPrefixCompiler(unittest.TestCase):

    def setUp(self):
        c = Compiler()
        c.add_standard_code()
        c.read_files()
        c.parse_code()
        c.extract_type_information()
        self.compiler = c

    def test_parse(self):
        self.assertEqual(
                prefix_compiler.parse('''
def hyphen-test
    prn "hello"
                ''')[0],
                ['def', 'hyphen_test', [], 'void', ['prn','"hello"']]
                )

    def test_compile_range_end(self):
        self.assertEqual(
                prefix_compiler.compile_range('10'),
                ['0', '10', '1']
                )

    def test_compile_range_start_end(self):
        self.assertEqual(
                prefix_compiler.compile_range('1', '10'),
                ['1', '10', '1']
                )

    def test_compile_range_start_end_step(self):
        self.assertEqual(
                prefix_compiler.compile_range('1', '10', '2'),
                ['1', '10', '2']
                )


    def test_compile_each_range(self):
        self.assertEqual(
                prefix_compiler.compile_each('i', ['range', '5'],
                    ['prn', 'i']),
                [
                    'for (i = 0; i < 5; i += 1) {',
                    [
                        'printf("%d\\n", i);',
                        ],
                    '}',
                    ]
                )

    def test_List_constructor(self):
        c = self.compiler
        self.assertEqual(
            c.compile_assignment(
                    'a',
                    ['List', '1', '2'],
                    ),
            [
                '(a = List__new(NULL))',
                'List__append(a, Int__new(NULL, 1))',
                'List__append(a, Int__new(NULL, 2))',
                ]
                )

    def test_List_append(self):
        c = self.compiler
        c.compile_assignment(
                'a',
                ['List', '1', '2'],
                ),
        self.assertEqual(
            c.compile_call(
                'a', 'append', '3'
                    ),
                'List__append(a, Int__new(NULL, 3))',
                )


    def test_Array_constructor(self):
        c = self.compiler
        c.compile_assignment(
                'a',
                ['Array', '10', 'int'],
                ),
        self.assertEqual(
                c.current_scope()['a'],
            [['Array', '10', 'int'], 'local' ]
                )

    def test_Array_constructor_wth_initial_values(self):
        c = self.compiler
        a = c.compile_assignment(
                'a',
                ['Array', '10', 'int', '0', '1', '2'],
                ),
        self.assertEqual(
                c.current_scope()['a'],
            [['Array', '10', 'int', '0', '1', '2',], 'local' ]
                )

    def test_compile_each_list_variable(self):
        c = self.compiler
        c.compile_assignment(
                'a',
                ['List', '1', '2'],
                )
        self.assertEqual(
                c.compile_each('i', 'a',
                    ['prn', 'i']),
                [
                    'for ((List__iterator1000 = a); (List__iterator1000->next != NULL); (List__iterator1000 = List__iterator1000->next)) {',
                    [
                        'i = (*(Int_t *)(List__iterator1000->next->data));',
                        'printf("%d\\n", i);',
                        ],
                    '}',
                ]
                )


    def test_compile_each_in_range(self):
        c = self.compiler
        self.assertEqual(
                c.compile_each('i', ['range', '0', '5'],
                    ['prn', 'i']),
                [
                    'for (i = 0; i < 5; i += 1) {',
                    [
                        'printf("%d\\n", i);',
                        ],
                    '}',
                ]
                )

    def test_compile_for(self):
        c = self.compiler
        self.assertEqual(
                c.compile_for(
                    ['=', 'i', '0'],
                    ['<', 'i', '5'],
                    ['+=', 'i', '1'],
                    ['prn', 'i'],
                    ),
                [
                    'for ((i = 0); (i < 5); (i += 1)) {',
                    [
                        'printf("%d\\n", i);',
                        ],
                    '}',
                ]
                )

    def test_compile_print(self):
        c = self.compiler
        self.assertEqual(
                c.compile_print(
                    'i',
                    ),
                'printf("%d", i)'
                )

    def test_compile_code(self):
        c = self.compiler
        a = c.compile_code('''
= a 5
''')
        self.assertEqual(
                c.current_scope()['a'],
                [['Int'], 'local']
                )

    def test_prn(self):
        c = self.compiler
        out = c.compile_code('''
= a 5
prn a
''')
        self.assertEqual(
                out,
                [
                    'a = 5;',
                    'printf("%d\\n", a);',
                    ]
                )

    def test_print_variable(self):
        c = self.compiler
        out = c.compile_code('''
= a 5
pr a
''')
        self.assertEqual(
                out,
                [
                    'a = 5;',
                    'printf("%d", a);',
                    ]
                )

    def test_print_with_string_formater(self):
        c = self.compiler
        out = c.compile_code('''
= a 5
pr "{a}"
''')
        self.assertEqual(
                out,
                [
                    'a = 5;',
                    'printf("%d", a);',
                    ]
                )

    def test_print_with_string_formater_arguments(self):
        c = self.compiler
        out = c.compile_code('''
= a 5
pr "{a:+03d}"
''')
        self.assertEqual(
                out,
                [
                    'a = 5;',
                    'printf("%+03d", a);',
                    ]
                )

if __name__ == '__main__':
    unittest.main()

