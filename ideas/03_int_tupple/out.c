#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>

struct Iterator_s {
    int finished;
    int stage;
    void *local;
};
typedef struct Iterator_s Iterator_t;

Iterator_t* Iterator__new(size_t size_of_locals);


struct Tuple_s {
    int length;
    size_t element_size;
    void *data;
};
typedef struct Tuple_s Tuple_t;

Tuple_t* Tuple__new(int length, size_t element_size, void *data) {
    Tuple_t *self = malloc(sizeof(Tuple_t));
    self->length = length;
    self->element_size = element_size;
    self->data = data;
    return self;
}

void* Tuple__offset_get(Tuple_t *self, int n) {
    if ((0 < n) && (n < self->length)) {
        return self->data + n * self->element_size;
    } else {
        return NULL;
    }
}

void* Tuple__offset_set(Tuple_t *self, int n, void *address) {
    void *ptr = NULL;
    if ((0 < n) && (n < self->length)) {
        ptr = self->data + (n * self->element_size);
        memcpy(ptr, address, self->element_size);
        return ptr;
    } else {
        return NULL;
    }
}

struct Tuple__iter_locals_s {
    int i;
    void *return_value;
};
typedef struct Tuple__iter_locals_s Tuple__iter_locals_t;

Iterator_t* Tuple__iter_new() {
    Iterator_t *iter = Iterator__new(sizeof(Tuple__iter_locals_t));
    return iter;
}

void* Tuple__iter(Tuple_t *self, Iterator_t *iter) {
    Tuple__iter_locals_t *local = iter->local;
    switch (iter->stage) {
        case 0:
            if (local->i < self->length) {
                local->return_value = self->data + (local->i * self->element_size);
                local->i += 1;
                break;
            } else {
                iter->stage = 1;
            }
        default:
            iter->finished = true;
    }
    return local->return_value;
}

void* Int__new(int n) {
    int *ptr = malloc(sizeof(n));
    *ptr = n;
    return ptr;
}

int Int__get(void *address) {
    return *(int*)address;
}


int main() {
    int temp = 0;
    int n = 0;
    int a__length = 5;
    int *a__data = calloc(a__length, sizeof(int));
    a__data[0] = 0;
    a__data[1] = 1;
    a__data[2] = 2;
    a__data[3] = 3;
    a__data[4] = 4;
    Tuple_t *a__tuple = Tuple__new(a__length, sizeof(int), a__data);

    Iterator_t *a__iterator = Tuple__iter_new();

    n = Int__get(Tuple__iter(a__tuple, a__iterator));
    while (!a__iterator->finished) {
        printf("n: %d\n", n);
        n = Int__get(Tuple__iter(a__tuple, a__iterator));
    }

    puts("---");
    temp = 6;
    Tuple__offset_set(a__tuple, 2, &temp);
    n = Int__get(Tuple__offset_get(a__tuple, 2));
    printf("n: %d\n", n);
    return 0;
}

Iterator_t* Iterator__new(size_t size_of_locals) {
    struct Iterator_s *self = malloc(sizeof(struct Iterator_s));
    self->finished = false;
    self->stage = 0;
    self->local = malloc(size_of_locals);
    memset(self->local, 0, size_of_locals);
    return self;
}

