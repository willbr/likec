include "stdio.h"

typ int (int *[]char)
def main (argc argv)
    int
        fahr
        celsius
        lower 
        upper 300
        step 20

    while (<= fahr upper)
        = celsius (expr 5 * (fahr - 32) / 9)
        = celsius (/ (* 5 (- fahr 32)) 9)
        printf "%d\t%d\n" fahr celsius
        += fahr step

func main -> int : argc int, argv *[]char
    int c
    set c (getchar)
    while (!= c EOF)
        putchar c
        set c (getchar)


func power -> int : base int, p int
    set n 1
    for i in (range p)
        set n (* p base)
    return n


func power (base n)
    int p
    for (= p 1) (> n 0) (-- n)
        *= p base
    return p

func main
    type int int *[]char
    var
        len
        max

    while (> (= len (getline line MAXLINE)) 0)
        if (> len max)
            = max len
            copy longest line
    if (> max 0)
        printf "%s" longest
    retur 0


