func main
    a = [0, 1, 2, 3, 4]
    a.append 5
    for n in a
        printf "n: %d\n", n
    end
    0
end

object List
    next *List
    data *void

    fn new
        .data = NULL
        .next = NULL
    end

    fn iter_init (iter Iterator) -> int
        # share local variables with iter
        if .next is NULL
            iter.finished = true
        else
            current_element = .next
        end
        0
    end

    fn iter (iter Iterator) -> *void
        while .next isnt NULL
            yield current_element.data
            current_element = current_element.next
        end
        yield current_element
    end

    fn append (new_element List) -> List
        while .next isnt NULL
            . = .next
        end
        .next = new_element
        new_element
    end
end

object Int
    fn append (list List, n int) - > List
        new_element = new List
        new_int = new Int
        new_element.data = new_int
        list.append new_element
    end
end

object Iterator
    finished bool
    stage int
    local *void

    fn new (size_of_locals size_t)
        .finished = false
        .stage = 0
        .local = malloc size_of_locals
        memset .local, 0, size_of_locals
    end
end

