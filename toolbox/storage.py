import hashlib
from collections import OrderedDict


class Record:
    def __init__(self, file, fid, tid, pid,
                 title_hash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                 content_hash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'):
        self.file = file
        self.fid = int(fid)
        self.tid = int(tid)
        self.pid = int(pid)
        self.title_hash = title_hash
        self.content_hash = content_hash

    @classmethod
    def new_empty(cls, file, fid, tid, pid):
        return cls(file, fid, tid, pid)

    @classmethod
    def new_record(cls, record):
        try:
            record = record.decode()
        except AttributeError:
            pass
        if record[-1] == '\n':
            record = record[:-1]
        return cls(*record.split(' '))

    @classmethod
    def new_content(cls, file, fid, tid, pid, title='', content=''):
        return cls(file, fid, tid, pid, hashlib.sha256(title.encode()).hexdigest(),
                   hashlib.sha256(content.encode()).hexdigest())

    def __repr__(self):
        return '<Content Record index: {self.file} fid:{self.fid} tid:{self.tid} pid:{self.pid} hash:{thash},' \
               '{chash}>'.format(self=self, thash=self.title_hash[:8], chash=self.content_hash[:8])

    def __str__(self):
        return f'{self.file} {self.fid} {self.tid} {self.pid} {self.title_hash} {self.content_hash}'

    def __eq__(self, other):
        try:
            return str(other) == self.file
        except (ValueError, TypeError):
            try:
                return str(other) == str(self)
            except (ValueError, TypeError):
                return NotImplemented

    def need_update(self, title, content):
        title_hash = hashlib.sha256(title.encode()).hexdigest()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if title_hash == self.title_hash and content_hash == self.content_hash:
            return False
        self.update_record(title_hash, content_hash)
        return True

    def pos_info(self):
        return self.fid, self.tid, self.pid

    def update_record(self, title_hash, content_hash):
        self.title_hash = title_hash
        self.content_hash = content_hash


class Storage:
    def __init__(self, project='', title=''):
        self.title = title
        self.project = project
        if title and project:
            self.records = OrderedDict()
            try:
                self._storage = open(f'./storage/{project}/{title}.txt', 'r+')
                for record in self._storage.readlines():
                    self.records[record.split(' ')[0]] = Record.new_record(record)
            except FileNotFoundError:
                self._storage = open(f'./storage/{project}/{title}.txt', 'w')
        else:
            raise RuntimeError('Storage with no project or title name is not allowed.')

    def __getitem__(self, item):
        return self.records.get(item)

    def add_record(self, record):
        if isinstance(record, Record):
            self.records[record.file] = record
        else:
            r = Record.new_record(record)
            self.records[r.file] = r

    def __contains__(self, item):
        return item in self.records

    def __del__(self):
        self._storage.seek(0)
        self._storage.write('\n'.join(str(record) for _, record in self.records.items()))
        self._storage.truncate()
        self._storage.close()
