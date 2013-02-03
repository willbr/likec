unsigned hash(char *s)
{
    unsigned hashval;
    for (hashval = 0; *s != '\0'; s++)
        hashval = *s + 31 * hashval;
    return hashval % HASHSIZE;
}


unsigned hash(char *s)
    unsigned hashval
    for hashval = 0; *s != '\0'; s++
        hashval = *s + 31 * hashval
    return hashval % HASHSIZE


object point
    int x, y
    point new()


def thing
    for i in range(10)
        println "num: %d", i

obj Point
    int
        x 0
        y 0
    def invert
        = x -x
        = y -y

def Point : -> Point

def Point_invert : self Point -> Point
    = self.x -x
    = self.y -y

def main : argc int, argv *[]char -> int
    Point  p
    p:invert
    int x 0
    puts "hello world"
    puts "#{argc:d}"
    printf "%d" argc
    printf "%d" (+ 1 5)

