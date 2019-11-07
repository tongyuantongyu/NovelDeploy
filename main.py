import hashlib
import hmac
import os
import sys
import traceback
import asyncio
import importlib

if sys.platform == 'win32':
    import subprocess

import tornado.web
import tornado.httpserver
import tornado.ioloop
from tornado.log import enable_pretty_logging
enable_pretty_logging()

import config
from _credential import _secret, _cert_dir
from toolbox import scheduler
from toolbox.tools import Now, Log

projects = config.tasks.keys()
now = Now()


class DirHandler(tornado.web.RequestHandler):

    async def get(self, *args):
        if not os.path.isdir(f'.{self.request.path}'):
            self.send_error(404, reason="Directory not exists.")
            return
        files = os.listdir(f'.{self.request.path}')
        title = self.request.path.split('/')[-2]
        files.sort(key=lambda x: (not os.path.isdir(f".{self.request.path}{x}"), x))
        file_list = []
        for file in files:
            if os.path.isdir(f".{self.request.path}{file}"):
                file_list.append(f'<a href="{self.request.path}{file}/">{file}</a></br>')
            else:
                file_list.append(f'<a href="{self.request.path}{file}">{file}</a></br>')
        self.write(f'<html><head><title>{title}</title></head>'
                   f'<body><h1>{title}</h1><div>{"".join(file_list)}</div></body></html>')


class SFileHandler(tornado.web.StaticFileHandler):

    async def get(self, path, include_body=True):
        _p = path.split('/')
        if len(_p) < 2 or _p[0] != 'artifacts' or _p[1] not in projects:
            self.send_error(403)
            return
        if os.path.isdir(f"./{path}"):
            self.redirect(f"/{path}/", permanent=True)
            return
        await super().get(path, include_body)


class UpdateHandler(tornado.web.RequestHandler):

    async def post(self, project):
        if project not in projects:
            self.send_error(403)
            return
        try:
            if not hmac.compare_digest(
                    'sha1=' + hmac.HMAC(_secret, self.request.body, hashlib.sha1).hexdigest(),
                    self.request.headers['X-Hub-Signature']):
                self.send_error(403)
                return
        except:
            self.send_error(403)
            return
        try:
            await asyncio.create_subprocess_shell(f"git submodule update --remote {project}")
        except Exception as e:
            print(traceback.format_exc())
            print(f"[{now}] Some error occurred during update: {e}")
            self.write("Some error occurred during update: " + str(e))
        else:
            self.write("Update Successful.")


class ForceUpdateHandler(tornado.web.RequestHandler):

    async def get(self, project):
        if project not in projects:
            self.send_error(403)
            return
        try:
            if sys.platform == 'win32':
                subprocess.call(f"git submodule update --remote {project}", shell=True)
            else:
                await asyncio.create_subprocess_shell(f"git submodule update --remote {project}")
            for task in scheduled_tasks[project]:
                await task.force_run()
        except Exception as e:
            print(traceback.format_exc())
            print(f"[{now}] Some error occurred during update: {e}")
            self.write("Some error occurred during update: " + str(e))
        else:
            self.write("Update Successful.")


application = tornado.web.Application([
    (r"/(robots.txt)", tornado.web.StaticFileHandler, {'path': ''}),
    (r"/(favicon.ico)", tornado.web.StaticFileHandler, {'path': ''}),
    (rf"/force_update_{_secret.decode()}/(?P<project>.*)", ForceUpdateHandler),
    (r"/update/(?P<project>.*)", UpdateHandler),
    (r"/(.*)/", DirHandler),
    (r"/(.*)(?!/)", SFileHandler, {'path': ''}),
])


def target(project, target_name):
    print(f'[{now}] Target {target_name}({project}): Start.')
    try:
        os.makedirs(os.path.abspath(f'./artifacts/{project}/{target_name}/'))
    except FileExistsError:
        pass
    importlib.import_module(f'targets.{target_name}', 'targets')\
        .work(project, importlib.import_module(f'{project}.config', project))
    print(f'[{now}] Target {target_name}({project}): Finished.')


def schedule(projects):
    tasks = dict()
    hour, minute, second = config.time_start
    count = 0
    for project, targets in projects.items():
        tasks[project] = []
        print(f'[{now}] Scheduling for project {project}: Start.')
        for target_name in targets:
            print(f'[{now}] Schedule Target {target_name}({project}).')
            tasks[project].append(scheduler.ScheduledTask(
                    (hour + count // 60, minute + count % 60, second), target, (project, target_name)))
            count += 1
        print(f'[{now}] Scheduling for project {project}: Finished.')
    return tasks


if __name__ == "__main__":
    with Log() as flusher:
        scheduled_tasks = schedule(config.tasks)

        _flush_log_task = scheduler.PeriodicalTask(360, flusher, ())

        server = tornado.httpserver.HTTPServer(application, ssl_options=_cert_dir)
        # server = tornado.httpserver.HTTPServer(application)
        server.listen(4443)
        tornado.ioloop.IOLoop.current().start()
