def main (argc int argv ([] * char)) int
    = a (new List 0 1 2 3 4)
    a:append 5
    return 0

obj List
    next (* List)
    data (* void)

    def append (new_element (* List))
        while (isnt self->next NULL)
            = self self->next
        = self->next new_element

typedef int Int_t
obj Int
    def new (n int)
        = (deref self ) n

    def append (list (* List) n int)
        = new_element (new List)
        = new_int (new Int n)
        = new_element->data new_int
        List:append list new_element
