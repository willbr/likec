#include <stdio.h>

int main() {
    int a[] = {0, 1, 2, 3, 4};
    int a__length = sizeof(a) / sizeof(int);
    int n = 0;
    int i = 0;

    for (i = 0; i < a__length; i += 1) {
        n = a[i];
        printf("n: %d\n", n);
    }
    return 0;
}

