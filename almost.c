def main (argc int argv ([] * char)) int
    = a (array 0 1 2 3 4)
    = b (+ 1 2 (* 3 4))
    = c 0
    printf "b: %d\n" b
    for n in a
        printf "n: %d\n" n
    yell "TIM"
    return 0

def yell (msg *char)
    printf "HEY! "
    puts msg

def beep
    puts "beep!"

