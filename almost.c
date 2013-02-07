def main (argc int argv ([] * char)) int
    = a (List 0 1 2 3 4)
    a:append 5
    return 0

obj List
    next (* List)
    data (* void)

    def append (new_element (* List)) (* List)
        while (isnt (-> self next) NULL)
            = self (-> self next)
        = (-> self next) new_element
        return new_element

typedef int Int_t
obj Int
    def new () (* int)
        = i-pointer (cast (* int) (malloc (sizeof int))) 
        = (deref i-pointer) 0
        return i-pointer 

    def append (list (* List) n int)
        = new_element (new List)
        = new_int (new Int)
        = (-> new_element data) new_int
        list:append new_element

obj Iterator
    finished bool
    stage int
    local (* void)

    def new (size_of_locals size_t)
        = (-> self finished) false
        = (-> self stage) 0
        = (-> self local) (malloc size_of_locals)
        memset (-> self local) 0 size_of_locals

