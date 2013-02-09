def main (argc int argv ([] * char)) int
    = a (new List 0 1 2 3 4)
    a:append 5
    for (n int) in a
        printf "%d\n" n
    return 0

obj List
    next (* List)
    data (* void)

    def append (new_data (* void))
        = new_element (new List)
        = new_element->data new_data
        while (isnt self->next NULL)
            = self self->next
        = self->next new_element

typedef Int_t int
obj Int
    def new (n int)
        = (deref self ) n

