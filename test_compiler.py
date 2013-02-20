import unittest
import prefix_compiler
from prefix_compiler import Compiler

class TestPrefixCompiler(unittest.TestCase):

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

    def test_compile_each_list_variable(self):
        c = Compiler()
        c.add_standard_code()
        c.read_files()
        c.parse_code()
        c.extract_type_information()
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

if __name__ == '__main__':
    unittest.main()

