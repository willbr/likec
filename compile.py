import pprint

from pf_parser import parse_tokens
from Tokenizer import Tokenizer
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def main():
    input_text = open(argv[1]).read()
    ts = Tokenizer(input_text)
    statements = parse_tokens(ts)
    print('\n')
    for command in statements:
        head, *tail = command
        print(head, tail)
    print('\n')
    pp (statements)


if __name__ == '__main__':
    main()

