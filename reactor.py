import socket
import select

try:
    from . import msg
    from .. import editor
    assert msg
except (ImportError, ValueError):
    import editor
    import msg


class _Reactor(object):
    ''' Simple chat server using select '''
    MAX_RETRIES = 20
    INITIAL_RECONNECT_DELAY = 500

    def __init__(self):
        self._fds = []
        self.handlers = []

    def connect(self, factory, host, port, secure):
        fd = factory.build_protocol(host, port, secure)
        self._fds.append(fd)
        fd.connect()
        self.handlers.append(factory)

    def stop(self):
        for _conn in self._fds:
            _conn.stop()

        self._fds = []
        self.handlers = []
        msg.log('Disconnected.')
        editor.status_message('Disconnected.')

    def is_ready(self):
        if not self.handlers:
            return False
        for f in self.handlers:
            if not f.is_ready():
                return False
        return True

    def _reconnect(fd, *fd_sets):
        for fd_set in fd_sets:
            fd_set.remove(fd)
        fd.reconnect()

    def tick(self):
        for factory in self.handlers:
            factory.tick()
        self.select()

    def select(self):
        if not self.handlers:
            return

        readable = []
        writeable = []
        errorable = []
        fd_map = {}

        for fd in self._fds:
            fd.fd_set(readable, writeable, errorable)
            fd_map[fd.fileno()] = fd

        if not readable and not writeable:
            return

        try:
            _in, _out, _except = select.select(readable, writeable, errorable, 0)
        except (select.error, socket.error, Exception) as e:
            # TODO: with multiple FDs, must call select with just one until we find the error :(
            if len(readable) == 1:
                readable[0].reconnect()
                return msg.error('Error in select(): %s' % str(e))
            raise Exception("can't handle more than one fd")

        for fileno in _except:
            fd = fd_map[fileno]
            self._reconnect(fd, _in, _out)

        for fileno in _out:
            fd = fd_map[fileno]
            try:
                fd.write()
            except Exception as e:
                msg.error('Couldn\'t write to socket: %s' % str(e))
                return self._reconnect(fd, _in)

        for fileno in _in:
            fd = fd_map[fileno]
            try:
                fd.read()
            except Exception as e:
                msg.error('Couldn\'t read from socket: %s' % str(e))
                fd.reconnect()

reactor = _Reactor()
