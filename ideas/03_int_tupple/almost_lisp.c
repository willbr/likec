(fn main
    (var a (0 1 2 3 4))
    (for n in a
        (printf "n: %d\n" n))
    (return 0))

(obj Iterator
    (finished bool)
    (stage int)
    (local *void)

    (fn new (size_of_locals size_t)
        (= .finished false)
        (= .stage 0)
        (= .local (malloc size_of_locals))
        (memset .local 0 size_of_locals)))


(obj Tuple
    (length int)
    (element_size size_t)
    (data *void)

    (fn new (length int element_size size_t data *void)
        (= .length length)
        (= .element_size element_size)
        (= .data data)
        (return self))

    (fn offset_get (n int) -> *void
        (if (< 0 n .length)
            (return (+ .data (* n .element_size))))
        (else
            (return NULL)))

    (fn offset_set (n int address *void) *void
        (if (< 0 n .length)
            (= ptr (+ .data (* n .element_size)))
            (memcpy ptr address .element_size)
            (return ptr))
        (else
            (return NULL)))

    (fn iter (iter Iterator) *void
        (= i 0)
        (while (< i .length)
            (yield (+ .data (* i .element_size))))))

