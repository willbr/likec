def main (argc int argv ([] * char)) int
    = a (List 0 1 2 3 4)
    a:append 5
    return 0

obj List
    next (* List)
    data (* void)

    def append (new_element (* List)) (* List)
        while (isnt .next NULL)
            = . .next
        = .next new_element
        return new_element

obj Int
    def new () (* int)
        return (malloc (sizeof int))
