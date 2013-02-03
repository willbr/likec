func main
    s = "hello"
    print_char s
    0
end

func print_char (s String) ->
    for c in s
        printf "%c\n", c
    end
end

object Iterator
    not_finished int
    that *void
    local *void

    fn new (that *void, size_of_local size_t) -> Iterator
    end
end

object String
    length int
    data []char

    fn new (c *char) -> String
        .data = c
        .length = strlen c
    end

    fn iter (iter Iterator) -> char
        i = 0
        while i < length
            yield data[i]
        end
        while i >= 0
            yield data[i]
        end
    end

    fn offset (i int) -> char
        if i < length
            data[i]
        else
            -1
        end
    end
end


const HASH-SIZE = 123

func hash (s string) -> unsigned int
    var hashval unsigned
    for i in range s.length
        hashval *= 31
        hashval += s[i]
    end
    hashval % HASH-SIZE
end

unsigned int hash(string s) {
    unsigned hashval;
    int i;
    for (i = 0; i < s.length; i += 1) {
        hashval *= 31;
        hashval += s.offset(i);
    }
    return hashval % HASH-SIZE;
}

