def main (argc int argv (CArray * char)) int
    = a (List 0 1 2 3 4)
    a append 5
    for (n int) in a
        printf "%d\n" n
    = b (Array 10 int ;hahahahahaha)
    ) ; comment
    = [b 0] 1234
    printf <<ENDS [b 0]
b[0] %d

ENDS
    ; comment
    for i in 0..5
        printf "range: %d\n" i
    return 0

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

