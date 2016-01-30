#define _GNU_SOURCE
#include <stdio.h>
#include <sys/types.h>

int main()
{
    ssize_t count = 0;
    size_t n = 1024;
    char line[1024] = { 0, };
    FILE *stream = fopen(__FILE__, "r");

    count = getline(&line, &n, stream);
    return 0;
}
