#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>

struct Iterator_s {
    int finished;
    int stage;
    void *local;
};

struct Iterator_s* Iterator__new(size_t size_of_locals);


struct String_s {
    char *data;
    size_t length;
};

struct String__iter_locals_s {
    int i;
    char return_value;
};


struct String_s* String__new(char *str);
char String__iter(struct String_s *self, struct Iterator_s *iter);

char print_char(struct String_s *s);


int main(int argc, char *argv[]) {
    struct String_s *s = String__new("hello");
    print_char(s);
    return 0;
}


char print_char(struct String_s *s) {
    char c;
    struct Iterator_s *s_iterator = Iterator__new(sizeof(struct String__iter_locals_s));
    c = String__iter(s, s_iterator);
    while (!s_iterator->finished) {
        printf("c: %c\n", c);
        c = String__iter(s, s_iterator);
    }
    return c;
}


struct Iterator_s* Iterator__new(size_t size_of_locals) {
    struct Iterator_s *self = malloc(sizeof(struct Iterator_s));
    self->finished = false;
    self->stage = 0;
    self->local = malloc(size_of_locals);
    memset(self->local, 0, size_of_locals);
    return self;
}


struct String_s* String__new(char *str) {
    size_t str_length = strlen(str);
    struct String_s *self = malloc(sizeof(struct String_s));

    self->length = str_length;

    self->data = malloc(sizeof(str_length) + 1);
    strncpy(self->data, str, str_length);

    return self;
}


char String__iter(struct String_s *self, struct Iterator_s *iter) {
    struct String__iter_locals_s *local = iter->local;

    switch (iter->stage) {
        case 0:
            if (local->i < self->length) {
                local->return_value = self->data[local->i];
                local->i += 1;
                break;
            } else {
                local->i = self->length - 1;
                iter->stage = 1;
            }
        case 1:
            if (local->i >= 0) {
                local->return_value = self->data[local->i];
                local->i -= 1;
                break;
            } else {
                iter->stage = 2;
            }
        default:
            iter->finished = true;
    }

    return local->return_value;
}

char String__offset(struct String_s *self, int i) {
    if (i < self->length) {
        return self->data[i];
    } else {
        return -1;
    }
}

