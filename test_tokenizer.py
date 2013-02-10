import unittest
import Tokenizer

class TestTokenizer_split_id(unittest.TestCase):
    def test_at_sign(self):
        self.assertEqual(
                Tokenizer.split_id('@'),
                ['self']
                )

    def test_at_sign_field(self):
        self.assertEqual(
                Tokenizer.split_id('@next'),
                ['(', '->', 'self', 'next', ')']
                )

    def test_indirect_single(self):
        self.assertEqual(
                Tokenizer.split_id('self->next'),
                ['(', '->', 'self', 'next', ')']
                )

    def test_indirect_double(self):
        self.assertEqual(
                Tokenizer.split_id('self->next->data'),
                ['(', '->', 'self', 'next', 'data', ')']
                )

    def test_method(self):
        self.assertEqual(
                Tokenizer.split_id('a:append'),
                ['method', 'a', 'append']
                )

if __name__ == '__main__':
    unittest.main()

