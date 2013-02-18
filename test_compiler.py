import unittest
from prefix_compiler import parse

class TestPrefixCompiler(unittest.TestCase):

    def test_parse(self):
        self.assertEqual(
                parse('''
def hyphen-test
    prn "hello"
                ''')[0],
                ['def', 'hyphen_test', [], 'void', ['prn','"hello"']]
                )

if __name__ == '__main__':
    unittest.main()

