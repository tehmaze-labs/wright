int main() {
#if defined(__MINGW32__) || defined(__MINGW64__)
    return 0;
#else
    return 1;
#endif
}
