#include <sys/types.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>

int main()
{
  struct pollfd x;

  x.fd = open(__FILE__, O_RDONLY);
  if (x.fd == -1) {
      _exit(1);
  }
  x.events = POLLIN;
  if (poll(&x,1,10) == -1) {
      _exit(1);
  }
  if (x.revents != POLLIN) {
      _exit(1);
  }

  /* XXX: try to detect and avoid poll() imitation libraries */

  _exit(0);
}
