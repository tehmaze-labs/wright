static int foo(void *restrict ptr)
{
    return *((int *)ptr);
}

int main(int argc, char **argv)
{
    int bar = 0;
    return foo(&bar);
}
