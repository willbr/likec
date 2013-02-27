#include <stdio.h>
#include <stdlib.h>

#define call(_fn, ...) local->_fn->cfn(local->_fn->env, ## __VA_ARGS__)
#define new(type, name) type *name = malloc(sizeof(type))
#define declare(name) local->name = name
#define declare_fn(name) local->name = new_fn_ ## name(local);

/*
 * Closure likec code
 * sea-lisp?
 *
 * (def main (argc int argv (* * char)) int
 *   (def arg-count () int
 *     (printf "%d\n" argc))
 *   (puts "hello")
 *   (arg-count)
 *   (-= argc 1)
 *   (arg-count))
 *
 */


/*
 * Declarations
 */

struct local_main;
struct fn_arg_count;

struct fn_arg_count *new_fn_arg_count(struct local_main *env);
int cfn_arg_count(struct local_main *closure);

/*
 * Structures
 */

struct local_main {
    int argc;
    char **argv;
    struct fn_arg_count *arg_count;
};

struct fn_arg_count {
    int (*cfn)(struct local_main *closure);
    struct local_main *env;
};

/*
 * Structure constructures
 */

struct fn_arg_count *
new_fn_arg_count(struct local_main *env)
{
    new(struct fn_arg_count, fn);
    fn->cfn = cfn_arg_count;
    fn->env = env;
    return fn;
}

/*
 * Functions
 */

int
cfn_arg_count(struct local_main *closure)
{
    printf("%d\n", closure->argc);
    return 0;
}

int
main (int argc, char **argv)
{
    new(struct local_main, local);
    declare(argc);
    declare(argv);
    declare_fn(arg_count);

    puts("hello");
    call(arg_count);
    local->argc -= 1;
    call(arg_count);
    return 0;
}

