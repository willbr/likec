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


struct List_s {
    void *data;
    struct List_s *next;
};
typedef struct List_s List_t;

struct List__iter_locals_s {
    List_t *current_elemement;
    void *return_value;
};
typedef struct List__iter_locals_s List__iter_locals_t;

List_t* List__new() {
    List_t *self;
    self = malloc(sizeof(List_t));
    self->data = NULL;
    self->next = NULL;
    return self;
}

int List__iter_init(List_t *self, Iterator_t *iter) {
    List__iter_locals_t *local = iter->local;
    if (self->next == NULL) {
        iter->finished = true;
    } else {
        // first item is just he list head
        local->current_elemement = self->next;
    }
    return 0;
}

void* List__iter(List_t *self, Iterator_t *iter) {
    List__iter_locals_t *local = iter->local;
    List_t *list = local->current_elemement;

    switch (iter->stage) {
        case 0:
            local->return_value = list->data;
            if (list->next != NULL) {
                local->current_elemement = list->next;
                break;
            } else {
                iter->stage = 1;
            }
        case 1:
            // last item
            if (list->data != NULL) {
                iter->stage = 2;
                break;
            }
        default:
            iter->finished = true;
    }

    return local->return_value;
}

List_t* List__append(List_t *self, List_t *new_elemement) {
    while (self->next != NULL) {
        self = self->next;
    }
    self->next = new_elemement;
    return new_elemement;
}

List_t* Int__append(List_t *list, int n) {
    List_t *new = malloc(sizeof(List_t));
    int *new_int = malloc(sizeof(int));
    *new_int = n;
    new->data = new_int;
    List__append(list, new);
    return new;
}

int main() {
    int n = 0;
    List_t *a__list = List__new();
    List_t *a__list_end = a__list;
    a__list_end = Int__append(a__list_end, 0);
    a__list_end = Int__append(a__list_end, 1);
    a__list_end = Int__append(a__list_end, 2);
    a__list_end = Int__append(a__list_end, 3);
    a__list_end = Int__append(a__list_end, 4);
    a__list_end = Int__append(a__list_end, 5);

    Iterator_t *a__iterator = Iterator__new(sizeof(List__iter_locals_t));
    List__iter_init(a__list, a__iterator);
    n = *(int*)List__iter(a__list, a__iterator);
    while (!a__iterator->finished) {
        printf("n: %d\n", n);
        n = *(int*)List__iter(a__list, a__iterator);
    }
    return 0;
}

struct Iterator_s* Iterator__new(size_t size_of_locals) {
    struct Iterator_s *self = malloc(sizeof(struct Iterator_s));
    self->finished = false;
    self->stage = 0;
    self->local = malloc(size_of_locals);
    memset(self->local, 0, size_of_locals);
    return self;
}

