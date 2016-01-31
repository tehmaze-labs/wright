import atexit
import json
import os
import pickle
import platform as pyplatform


class Cache(object):
    def __init__(self, platform, marshaler='json'):
        self.marshaler = marshaler or 'json'
        # We use platform.uname here, because os.uname is not available on
        # all supported platforms.
        self.prefix = ':'.join([pyplatform.uname()[1], platform])
        self.cached = {}

    def _key(self, item):
        if isinstance(item, (tuple, list)):
            return '-'.join(self._key(part) for part in item if part)
        return str(item)

    def __contains__(self, item):
        try:
            return self._key(item) in self.cached[self.prefix]
        except KeyError:
            return False

    def __delitem__(self, item):
        del self.cached[self.prefix][self._key(item)]

    def __getitem__(self, item):
        return self.cached[self.prefix][self._key(item)]

    def __setitem__(self, item, value):
        if not self.prefix in self.cached:
            self.cached[self.prefix] = {}
        self.cached[self.prefix][self._key(item)] = value

    def __iter__(self):
        raise NotImplementedError()

    def keys(self):
        raise NotImplementedError()

    def values(self):
        raise NotImplementedError()

    def open(self, filename):
        self.load(filename)
        atexit.register(lambda: self.save(filename))

    def pop(self, key, default=None):
        try:
            value = self[key]
            del self[key]
        except KeyError:
            value = default
        return value

    def load(self, filename):
        if not os.path.isfile(filename):
            return
        with open(filename, 'rb') as fp:
            if self.marshaler == 'json':
                self.cached.update(json.load(fp))
            elif self.marshaler == 'pickle':
                self.cached.update(pickle.load(fp))
            else:
                raise TypeError('Marshaler "{}" not supported'.format(
                    self.marshaler))

    def save(self, filename):
        with open(filename, 'wb') as fp:
            if self.marshaler == 'json':
                json.dump(self.cached, fp, indent=2, sort_keys=True)
            elif self.marshaler == 'pickle':
                pickle.dump(self.cached, fp)
            else:
                raise TypeError('Marshaler "{}" not supported'.format(
                    self.marshaler))
