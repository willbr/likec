def main (argc int argv (CArray * char)) int
    = a (List 0 1 2 3 4)
    a append 5
    for (n int) in a
        prn n
    = b (Array 10 int ;hahahahahaha)
    ) ; comment
    = [b 0] 1234
    printf <<ENDS [b 0]
b[0] %d

ENDS
    ; comment
    for i in 0..5
        pr "range: {i}\n"

    prn

    pr "reduce: a, "
    prn (reduce add a)
    prn

    pr "(map doubleit a)\n=>"
    = c (map doubleit a)
    print-list c
    prn
    return 0

def print-list (l (* List))
    for (n int) in l
        pr " {n}"


def doubleit (n Int) Int
    return (+ n n)

def add (a int b int) int
    return (+ a b)

def car (l (* List)) (* void)
    return (-> l next data)

typedef String_t (* char)
obj String
    def new (s (* char))
        = @ (malloc (+ (strlen s) 1))
        strcpy [@] s

    def die
        free @

