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
    return 0



def add (a int b int) int
    return (+ a b)

def car (l (* List)) (* void)
    return (-> l next data)

def cdr (l (* List)) (* List)
    return (? (== (-> l next) NULL)
              NULL
              (-> l next))


obj List
    next (* List)
    data (* void)

    def append (new_data (* void))
        = new_element (List)
        = new_element->data new_data
        while (isnt @next NULL)
            = @ @next
        = @next new_element

typedef Int_t int
obj Int
    def new (n int)
        = [@] n

    def die
        free @

typedef String_t (* char)
obj String
    def new (s (* char))
        = @ (malloc (+ (strlen s) 1))
        strcpy [@] s

    def die
        free @

