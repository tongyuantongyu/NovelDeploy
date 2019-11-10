import os
import io
import shutil
import datetime
import tarfile

from toolbox.tools import Now
from compiler import plain_text

now = Now()


def work(project, _vars):
    try:
        os.remove(f"./artifacts/{project}/text/{project}_latest.tar.gz")
    except FileNotFoundError:
        pass
    tar = tarfile.open(f"./artifacts/{project}/text/{project}_latest.tar.gz", "x:gz")
    for sec_title, files in _vars.menu.items():
        for file in files:
            tex = open(f'./{project}/{file}', 'rb').read()
            title, content = plain_text.compile(tex)
            combined = f"{title}\n\n\n{content}".encode()
            buf = io.BytesIO(combined)
            info = tarfile.TarInfo(f'{sec_title}/{file[:-4]}.txt')
            info.size = len(combined)
            tar.addfile(info, buf)
    tar.close()
    shutil.copy(f"./artifacts/{project}/text/{project}_latest.tar.gz",
                f"./artifacts/{project}/text/history/{project}_{datetime.datetime.now().strftime('%y%m%d')}.tar.gz")
    _abspath = os.path.abspath(f"./artifacts/{project}/epub/{project}_latest.tar.gz")
    print(f'[{now}] Text tarball file saved at {_abspath}.')
