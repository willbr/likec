import pprint
from Tokenizer import Tokenizer
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def main():
    input_text = open(argv[1]).read()
    ts = Tokenizer(input_text)
    statements = parse_tokens(ts)
    print('\n')
    print(input_text)
    print('\n')
    pp (statements)

def ast(text):
    return parse_tokens(Tokenizer(text))

def parse_tokens(token_stream):
    statements = []
    while token_stream.has_more_tokens:
        statements.append(parse_lexp(token_stream))
    return statements

def parse_lexp(token_stream):
    line = []
    while token_stream.token.typ != 'NEWLINE':
        if token_stream.token.typ == 'OPEN_PAREN':
            line.append(parse_sexp(token_stream))
        elif token_stream.token.typ == 'NEWLINE':
            pass
        else:
            line.append(token_stream.token.value)
            token_stream.advance()
    token_stream.advance()

    if line[0] == 'def':
        length = len(line)
        if length == 2:
            line.extend(([], 'void'))
            pass
        elif length == 3:
            line.append('void')
        else:
            pass

    if token_stream.token.typ == 'BLOCK_START':
        token_stream.advance()
        while token_stream.token.typ != 'BLOCK_END':
            line.append(parse_lexp(token_stream))
        token_stream.advance()

    return line

def parse_sexp(token_stream):
    token_stream.skip('OPEN_PAREN')
    sexp = []
    while token_stream.token.typ != 'CLOSE_PAREN':
        if token_stream.token.typ == 'NEWLINE':
            token_stream.advance()
        elif token_stream.token.typ == 'OPEN_PAREN':
            sexp.append(parse_sexp(token_stream))
        else:
            sexp.append(token_stream.token.value)
            token_stream.advance()

    token_stream.skip('CLOSE_PAREN')

    return sexp

if __name__ == '__main__':
    main()

