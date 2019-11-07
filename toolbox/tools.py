import datetime


class Now:
    def __str__(self):
        return datetime.datetime.now().strftime("%H:%M:%S")


class Log:

    working = False
    now = Now()

    def __init__(self, out='out.log', err='err.log'):
        if self.working:
            raise RuntimeError("Another Logger already working.")
        self.working = True
        self._log_out = open(out, 'a')
        self._log_err = open(err, 'a')

    def __enter__(self):
        import sys
        self._out_write = sys.stdout.write
        self._err_write = sys.stderr.write
        sys.stdout.write = self.get_writer('out')
        sys.stderr.write = self.get_writer('err')

    def get_writer(self, target):
        def _writer(text):
            if target == 'out':
                self._log_out.write(text)
                self._out_write(text)
            elif target == 'err':
                self._log_err.write(text)
                self._err_write(text)
        return _writer

    def __exit__(self, exc_type, exc_val, exc_tb):
        import sys
        sys.stdout.write = self._out_write
        sys.stderr.write = self._err_write
        if exc_type:
            import traceback
            self._log_err.write(f'[{self.now}] {exc_type.__name__}: {exc_val}\n{"".join(traceback.format_tb(exc_tb))}\n')
        self._log_out.close()
        self._log_err.close()
        self.working = False
