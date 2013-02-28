#include <stdio.h>
#include <stdlib.h>

#define call(_fn, ...) local->_fn->cfn(local->_fn->env, ##__VA_ARGS__)
#define new(type, name) type *name = malloc(sizeof(type))

/*
 *
 * Closure likec code
 * sea-lisp?
 *
 * (def main () int
 *   (def make-counter (start-value int) (fn () int)
 *     (= count start-value)
 *     (def counter () int
 *       (post-inc count))
 *     counter)
 *   (= counter-a  (make-counter  0))
 *   (= counter-b  (make-counter 1000))
 *   (printf "a: %d\n" (counter-a))
 *   (printf "b: %d\n" (counter-b))
 *   0)
 *
 */



/*
 * Structures
 */

struct local_main
{
    struct fn_make_counter *make_counter;
    struct fn_counter *counter_a;
    struct fn_counter *counter_b;
};

struct local_make_counter
{
    int initial_value;
    int count;
    struct fn_counter *counter;
};

struct fn_make_counter
{
    struct fn_counter * (*cfn)(struct local_main *closure, int);
    struct local_main *env;
};

struct fn_counter
{
    int (*cfn)(struct local_make_counter *closure);
    struct local_make_counter *env;
};


/*
 * Declarations
 */

struct fn_counter * cfn_make_counter(struct local_main *closure,
                                     int initial_value 
                                     );
int cfn_counter(struct local_make_counter *closure);


/*
 * Structure constructures
 */

struct fn_make_counter *
new_fn_make_counter(struct local_main *env)
{
    new(struct fn_make_counter, fn);
    fn->cfn = cfn_make_counter;
    fn->env = env;
    return fn;
};

struct fn_counter *
new_fn_counter(struct local_make_counter *env)
{
    new(struct fn_counter, fn);
    fn->cfn = cfn_counter;
    fn->env = env;
    return fn;
};


/*
 * Functions
 */

int
cfn_counter(struct local_make_counter *closure)
{
    return (closure->count)++;
}


struct fn_counter *
cfn_make_counter(struct local_main *closure, int initial_value)
{
    new(struct local_make_counter, local);
    local->initial_value = initial_value;

    local->count = initial_value;
    local->counter = new_fn_counter(local);
    return local->counter;
}

int
main ()
{
    new(struct local_main, local);

    local->make_counter = new_fn_make_counter(local);

    local->counter_a = call(make_counter, 0);
    local->counter_b = call(make_counter, 1000);

    printf("a: %d\n", call(counter_a));
    printf("a: %d\n", call(counter_a));
    printf("a: %d\n", call(counter_a));

    printf("b: %d\n", call(counter_b));
    printf("b: %d\n", call(counter_b));
    printf("b: %d\n", call(counter_b));

    printf("a: %d\n", call(counter_a));
    printf("a: %d\n", call(counter_a));

    printf("b: %d\n", call(counter_b));
    printf("b: %d\n", call(counter_b));

    return 0;
}

