import atexit
import datetime
import platform
import sys


class Logger(object):
    def __init__(self, filename):
        self.filename = filename
        self.fd = open(filename, 'w')
        atexit.register(self.close)
        self.write('starting: on {}\n'.format(platform.uname()[3]))
        self.write('called as: {}\n'.format(' '.join(sys.argv)))

    def close(self):
        self.fd.close()

    def fileno(self):
        return self.fd.fileno()

    def flush(self):
        self.fd.flush()

    def write(self, data):
        self.writeraw(datetime.datetime.now().strftime('%FT%TZ '))
        self.writeraw(data)

    def writeraw(self, data):
        self.fd.write(data)
