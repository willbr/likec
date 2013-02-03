struct Iterator_s
    finished int
    stage int
    *local *void
end
typedef struct Iterator_s Iterator_t

struct Tuple_s
    length int 
    element_size size_t
    data *void
end
typedef struct Tuple_s Tuple_t

func Tuple__new(length int, element_size size_t, data *void) -> Tuple_t
    var self *Tuple_t = malloc sizeof Tuple_t
    self->length = length
    self->element_size = element_size
    self->data = data
    return self
end

func Tuple__offset_get(self *Tuple_t, n int) -> *void
    if 0 < n < self->length
        return self->data + n * self->element_size
    end else
        return NULL
    end
end

func Tuple__offset_set(self *Tuple_t, n int, address *void) -> *void
    var ptr *void = NULL
    if 0 < n < self->length
        ptr = self->data + (n * self->element_size)
        memcpy ptr, address, self->element_size
        return ptr
    end else
        return NULL
    end
end

struct Tuple__iter_locals_s
    i int
    return_value *void
end
typedef struct Tuple__iter_locals_s Tuple__iter_locals_t

func Tuple__iter_new -> *Iterator_t
    var iter *Iterator_t = Iterator__new sizeof Tuple__iter_locals_t
    return iter
end

func Tuple__iter(self *Tuple_t, iter *Iterator_t) -> *void
    var local *Tuple__iter_locals_t = iter->local
    cswitch iter->stage
        case 0:
            if local->i < self->length
                local->return_value = self->data + (local->i * self->element_size)
                local->i += 1
                break
            end else
                iter->stage = 1
            end
        default:
            iter->finished = true
    end
    return local->return_value
end

func Int__new (n int) -> *void
    var ptr *int = malloc sizeof n
    *ptr = n
    return ptr
end

func Int__get (address *void) -> int
    return *(int*)address
end


func main(argc int, argv []*char) -> int
    var temp, n int = 0
    var a__length int = 5
    var a__data *int = calloc a__length, sizeof(int)
    var a__tuple *Tuple_t= Tuple__new a__length, sizeof(int), a__data

    a__data[0] = 0
    a__data[1] = 1
    a__data[2] = 2
    a__data[3] = 3
    a__data[4] = 4

    var a__iterator *Iterator_t= Tuple__iter_new

    n = Int__get(Tuple__iter(a__tuple, a__iterator))
    while not a__iterator->finished
        printf"n: %d\n", n
        n = Int__get Tuple__iter(a__tuple, a__iterator)
    end

    puts "---"
    temp = 6
    Tuple__offset_set a__tuple, 2, &temp
    n = Int__get Tuple__offset_get a__tuple, 2
    printf "n: %d\n", n
    return 0
end

func Iterator__new(size_t size_of_locals) -> *Iterator_t
    var self *Iterator_t = malloc sizeof Iterator_t
    self->finished = false
    self->stage = 0
    self->local = malloc size_of_locals
    memset self->local, 0, size_of_locals
    return self
end

