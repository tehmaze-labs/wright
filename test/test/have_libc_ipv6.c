#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

int main(int argc, char **argv)
{
    struct sockaddr_in6 sa;
    sa.sin6_family = PF_INET6;
    return 0;
}
