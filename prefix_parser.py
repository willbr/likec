import pprint
from prefix_tokenizer import Tokenizer, Token
from sys import argv

pp = pprint.PrettyPrinter(indent=2).pprint

def main():
    input_text = open(argv[1]).read()
    #print(input_text)
    ts = Tokenizer(input_text)
    statements = parse_tokens(ts)
    #print('\n')
    for s in statements:
        print(indent(map_tree_to_values(s)))
        print()

def ast(text):
    return parse_tokens(Tokenizer(text))

def parse_tokens(token_stream):
    statements = []
    while token_stream.has_more_tokens:
        if token_stream.token.typ == 'OPEN_PAREN':
            s = parse_sexp(token_stream)
        else:
            s = parse_lexp(token_stream)
        if s:
            statements.append(s)
    return statements

def parse_lexp(token_stream):
    line = []
    while token_stream.token.typ != 'NEWLINE' and token_stream.has_more_tokens:
        if token_stream.token.typ == 'OPEN_PAREN':
            line.append(parse_sexp(token_stream))
        elif token_stream.token.typ == 'NEWLINE':
            pass
        elif token_stream.token.typ == 'COMMENT':
            token_stream.advance()
        else:
            line.append(token_stream.token)
            token_stream.advance()
    token_stream.advance()

    first_token = line[0] if line else None

    if not line:
        pass
    elif isinstance(first_token, list):
        pass
    elif first_token.value in ['c-def', 'def']:
        length = len(line)
        c_type = 'int' if first_token.value == 'def' else 'void'
        return_type = Token(
                'ID',
                c_type,
                first_token.line,
                first_token.column,
                )
        if length == 2:
            arguments = []
            line.extend((arguments, return_type))
        elif length == 3:
            line.append(return_type)
        else:
            pass

    if token_stream.token.typ == 'BLOCK_START':
        token_stream.advance()
        while token_stream.token.typ != 'BLOCK_END':
            lexp = parse_lexp(token_stream)
            if lexp:
                line.append(lexp)
        token_stream.advance()

    if line:
        return line
    else:
        return None

def parse_sexp(token_stream):
    token_stream.skip('OPEN_PAREN')
    sexp = []

    while token_stream.token.typ != 'CLOSE_PAREN' and token_stream.has_more_tokens:
        if token_stream.token.typ == 'NEWLINE':
            token_stream.advance()
        elif token_stream.token.typ == 'OPEN_PAREN':
            sexp.append(parse_sexp(token_stream))
        elif token_stream.token.typ == 'COMMENT':
            token_stream.advance()
        else:
            sexp.append(token_stream.token)
            token_stream.advance()

    token_stream.skip('CLOSE_PAREN')

    return sexp

def indent(e, level=0, start=''):
    if isinstance(e, list):
        try:
            if e[0] == 'def':
                head, name, args, return_value, *tail = e
                body = '%s %s %s %s %s' % (
                        head,
                        name,
                        to_string(args),
                        to_string(return_value),
                        ' '.join(indent(t, level + 1, '\n') for t in tail))
            elif e[0] == 'obj':
                head, name, *tail = e 
                s = []
                for a in tail:
                    if a[0] == 'def':
                        s.append(indent(a, level + 1, '\n'))
                    else:
                        s.append('\n%s%s' % ('  ' * (level + 1), to_string(a)))
                body = 'obj %s %s' % (name, ' '.join(s))
            else:
                body = ' '.join(indent(t, level + 1, '\n') for t in e)
        except IndexError:
            body = ''

        return '%s%s(%s)' %  (
                start,
                '  ' * level,
                body)
    else:
        return e

def to_string(e):
    if isinstance(e, list):
        return '(%s)' % ' '.join(to_string(t) for t in e)
    else:
        return e

def map_tree(fn, tree):
    if isinstance(tree, list):
        return [map_tree(fn, branch) for branch in tree]
    else:
        return fn(tree)

def map_tree_to_values(tree):
    return map_tree(
            lambda x: x.value,
            tree,
            )

if __name__ == '__main__':
    main()

