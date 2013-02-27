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
 *   (def make-inc (x) (fn (int) int)
 *     (def inc (y) int
 *       (+ x y))
 *     inc)
 *   (= inc5  (make-inc  5))
 *   (= inc10 (make-inc 10))
 *   (printf "%d\n" (inc5  5))
 *   (printf "%d\n" (inc10 5))
 *   0)
 *
 */



/*
 * Structures
 */

struct local_main
{
    struct fn_make_inc *make_inc;
    struct fn_inc *inc5;
    struct fn_inc *inc10;
};

struct local_make_inc
{
    int x;
    struct fn_inc *inc;
};

struct local_inc
{
    int y;
};

struct fn_make_inc
{
    struct fn_inc * (*cfn)(struct local_main *closure, int x);
    struct local_main *env;
};

struct fn_inc
{
    int (*cfn)(struct local_make_inc *closure, int y);
    struct local_make_inc *env;
};


/*
 * Declarations
 */

struct fn_inc * cfn_make_inc(struct local_main *closure, int x);
int cfn_inc(struct local_make_inc *closure, int y);


/*
 * Structure constructures
 */

struct fn_make_inc *
new_fn_make_inc(struct local_main *env)
{
    new(struct fn_make_inc, fn);
    fn->cfn = cfn_make_inc;
    fn->env = env;
    return fn;
};

struct fn_inc *
new_fn_inc(struct local_make_inc *env)
{
    new(struct fn_inc, fn);
    fn->cfn = cfn_inc;
    fn->env = env;
    return fn;
};


/*
 * Functions
 */

int
cfn_inc(struct local_make_inc *closure, int y)
{
    new(struct local_inc, local);
    local->y = y;

    return closure->x + local->y;
}


struct fn_inc *
cfn_make_inc(struct local_main *closure, int x)
{
    new(struct local_make_inc, local);
    local->x = x;

    local->inc = new_fn_inc(local);
    return local->inc;
}

int
main ()
{
    new(struct local_main, local);

    local->make_inc = new_fn_make_inc(local);
    local->inc5 = call(make_inc, 5);
    local->inc10 = call(make_inc, 10);
    printf("%d\n", call(inc5, 5));
    printf("%d\n", call(inc10, 5));
    return 0;
}

