def main (argc int argv ([] * char)) int
    = a (List 0 1 2 3 4)
    ; append 5 to a
    for (n int) in a
        printf "%d\n" n
    = b (Array 10 0 ;hahahahahaha)
    )
    = (array-offset b 0) 1234
    printf <<ENDS (array-offset b 0)
b[0] %d

ENDS
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
        = (deref @) n

