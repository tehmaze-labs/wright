#include <stdlib.h>
#include <string.h>

int main()
{
    char *str = NULL, *delim = NULL, *saveptr = NULL;
    strtok_r(str, delim, &saveptr);
    return 0;
}
