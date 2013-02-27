#include <stdio.h>
#include <stdlib.h>

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

struct main_local * new_main_local(int argc, char **argv);
struct fn_main_arg_count *new_fn_main_arg_count(struct main_local *env);

int cfn_main_arg_count(struct main_local *closure);

/*
 * Structures
 */

struct main_local {
    int argc;
    char **argv;
    struct fn_main_arg_count *arg_count;
};

struct fn_main_arg_count {
    int (*cfn)(struct main_local* closure);
    struct main_local *env;
};

/*
 * Structure constructures
 */

struct main_local *
new_main_local(int argc, char **argv)
{
    struct main_local *local = malloc(sizeof(struct main_local));
    local->argc = argc;
    local->argv = argv;
    local->arg_count = new_fn_main_arg_count(local);
    return local;
}

struct fn_main_arg_count *
new_fn_main_arg_count(struct main_local *env)
{
    struct fn_main_arg_count *fn =
        malloc(sizeof(struct fn_main_arg_count));
    fn->cfn = cfn_main_arg_count;
    fn->env = env;
    return fn;
}

/*
 * Functions
 */

int
cfn_main_arg_count(struct main_local *closure)
{
    printf("%d\n", closure->argc);
    return 0;
}

int
main (int argc, char **argv)
{
    struct main_local *local = new_main_local(argc, argv);
    puts("hello");
    local->arg_count->cfn(local->arg_count->env);
    local->argc -= 1;
    local->arg_count->cfn(local->arg_count->env);
    return 0;
}

