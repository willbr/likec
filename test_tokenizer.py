import unittest
import prefix_tokenizer
from prefix_tokenizer import split_id

class TestTokenizer_split_id(unittest.TestCase):

    def test_at_sign(self):
        self.assertEqual(
                split_id('@'),
                ['self']
                )

    def test_at_sign_field(self):
        self.assertEqual(
                split_id('@next'),
                ['(', '->', 'self', 'next', ')']
                )

    def test_indirect_single(self):
        self.assertEqual(
                split_id('self->next'),
                ['(', '->', 'self', 'next', ')']
                )

    def test_indirect_double(self):
        self.assertEqual(
                split_id('self->next->data'),
                ['(', '->', 'self', 'next', 'data', ')']
                )

    def test_method(self):
        self.assertEqual(
                split_id('a:append'),
                ['method', 'a', 'append']
                )

    def test_Tokenizer_single_line(self):
        t = prefix_tokenizer.Tokenizer('''
= a 5
''')
        tokens = values(t.tokens)

        self.assertEqual(
                tokens,
                ['=', 'a', '5', '\n']
                )

    def test_Tokenizer_heredoc(self):
        t = prefix_tokenizer.Tokenizer('''
= a <<MSG
hello
world
MSG
''')
        tokens = values(t.tokens)

        self.assertEqual(
                tokens,
                ['=', 'a', '"hello\\nworld"', '\n']
                )

    def test_Tokenizer_anonymous(self):
        t = prefix_tokenizer.Tokenizer('''
reduce {+ $ $} a
''')
        tokens = values(t.tokens)

        self.assertEqual(
                tokens,
                [
                    'reduce',
                    '(',
                    'fn-shorthand',
                    '+',
                    '$',
                    '$',
                    ')',
                    'a',
                    '\n'
                    ]
                )

def values(tokens):
    return [t.value for t in tokens]

def types(tokens):
    return [t.typ for t in tokens]

if __name__ == '__main__':
    unittest.main()

