def main (argc int argv (CArray * char)) int
    = a (List 0 1 2 3 4)
    a append 5
    = sum 0
    for (n int) in a
        += sum n
    prn "sum: {sum}"

    = b (Array 10 int ;hahahahahaha)
    ) ; comment
    = [b 0] 1234
    printf <<ENDS [b 0]
b[0] %d

ENDS
    ; comment
    for i in 0..3
        pr "range: {i}\n"

    prn

    pr "reduce: a, "
    prn (reduce add a)
    prn

    pr "(map doubleit a)\n=>"
    = c (map doubleit a)
    print-list "c" c


    = d (map (fn (n int) int (return (+ n 1))) a)

    prn "anon function"
    print-list "d" d


    = e (reduce {+ $1 $2} a 0)
    prn "e: {e}"

    = f (filter {> $ 2} a)
    print-list "f" f

    = my-name (String "William")

    prn "goodbye {my-name}"

    return 0

def print-list (name String l (* List))
    pr "{name}:"
    for (n int) in l
        pr " {n}"
    prn


def doubleit (n Int) Int
    return (+ n n)

def add (a int b int) int
    return (+ a b)


