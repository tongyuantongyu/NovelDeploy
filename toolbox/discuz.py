import time
import re
import random
from typing import Tuple

import requests
import js2py

from bs4 import BeautifulSoup as bs

# post urls
new_forum = "{site}/forum.php?mod=forumdisplay&fid={fid}"
new_accept = "{site}/forum.php?mod=ajax&action=checkpostrule&ac=newthread&inajax=yes"
new_action = "{site}/forum.php?mod=post&action=newthread&fid={fid}&extra=&topicsubmit=yes"
load_reply = "{site}/forum.php?mod=post&action=reply&fid={fid}&tid={tid}&cedit=yes"
load_thread = "{site}/forum.php?mod=viewthread&tid={tid}"
reply_accept = "{site}/forum.php?mod=ajax&action=checkpostrule&ac=reply&inajax=yes"
new_reply = "{site}/forum.php?mod=post&action=reply&fid={fid}&tid={tid}&extra=&replysubmit=yes"
new_fastreply = "{site}/forum.php?mod=post&action=reply&fid={fid}&tid={tid}&extra=&replysubmit=yes&infloat=yes&handlekey=fastpost&inajax=1"

find_reply = "{site}/forum.php?mod=redirect&goto=findpost&ptid={tid}&pid={pid}"
edit_forum = "{site}/forum.php?mod=post&action=edit&fid={fid}&tid={tid}&pid={pid}"
edit_accept = "{site}/forum.php?mod=ajax&action=checkpostrule&ac=post&inajax=yes"
edit_action = "{site}/forum.php?mod=post&action=edit&extra=&editsubmit=yes"

formhash_prefix = '<input type="hidden" name="formhash" value="'

new_thread_formdata_tmpl = {
    "replycredit_extcredits" : "0",
    "replycredit_times"      : "1",
    "replycredit_membertimes": "1",
    "replycredit_random"     : "100",
    "wysiwyg"                : "1",
    "readperm"               : "",
    "price"                  : "",
    "tags"                   : "",
    "rushreplyfrom"          : "",
    "rushreplyto"            : "",
    "rewardfloor"            : "",
    "replylimit"             : "",
    "stopfloor"              : "",
    "creditlimit"            : "",
    "cronpublishdate"        : "",
    "allownoticeauthor"      : "1",
    "usesig"                 : "1",
    "save"                   : ""
}

new_reply_formdata_tmpl = {
    "noticeauthor"   : "",
    "noticetrimstr"  : "",
    "noticeauthormsg": "",
    "subject"        : "",
    "wysiwyg"        : "1",
    "usesig"         : "1",
    "save"           : ""
}

new_fastreply_formdata_tmpl = {
    "subject": "",
    "usesig" : "1"
}

edit_main_thread_formdata_tmpl = {
    "delattachop"            : "0",
    "page"                   : "1",
    "wysiwyg"                : "1",
    "subject"                : "",
    "checkbox"               : "0",
    "usesig"                 : "1",
    "delete"                 : "0",
    "save"                   : "",
    "typeid"                 : "792",
    "replycredit_extcredits" : "0",
    "replycredit_times"      : "1",
    "replycredit_membertimes": "1",
    "replycredit_random"     : "100",
    "readperm"               : "",
    "price"                  : "0",
    "tags"                   : "",
    "allownoticeauthor"      : "1"
}

edit_reply_thread_formdata_tmpl = {
    "delattachop": "0",
    "wysiwyg"    : "1",
    "subject"    : "",
    "usesig"     : "1",
    "delete"     : "0",
}

obfuscate_name = ['location',
                  'window',
                  'replace',
                  'assign',
                  'href']

awful_getName_func = r'''function getName(){var caller=getName.caller;if(caller.name){return caller.name} var str=caller.toString().replace(/[\s]*/g,"");var name=str.match(/^function([^\(]+?)\(/);if(name && name[1]){return name[1];} else {return '';}}'''

fake_location = [r"_\w+\['href'\].+;$", r"_\w+\.href=.+;$", r"_\w+\[_\w+\].+;$"]


def now():
    return str(int(time.time()))


def random_mark():
    return f"mark_{hex(random.randint(0, 1 << 64 - 1))[2:]:0>16}"


def fxxk_dsign(content):
    try:
        content = content.decode()
    except AttributeError:
        pass
    js = content[31:-9]
    for name in obfuscate_name:
        js = re.sub(rf"\w+ = '?{name}'?;", '', js)
    redirect = re.findall(r"_\w+?\[_\w+?\]=", js)
    if len(redirect) == 2:
        js = js[:js.find(redirect[1])]
    else:
        for fake in fake_location:
            if re.search(fake, js):
                js = re.sub(fake, '', js)
                break
    js = re.sub(r"location\[_\w+\]=?", '', js)
    js = re.sub(r"location\.href=?", '', js)
    js = re.sub(r"_\w+\[_\w+\]=?", '', js)
    js = js.replace(awful_getName_func, '')
    js = re.sub(r"function (?P<f_name>\w+?)\(\){return getName\(\);\}",
                r"function \g<f_name>(){return '\g<f_name>';}", js)
    return js2py.eval_js(js)


class Discuz:
    def __init__(self, site: str, session: requests.Session):
        self.site = site
        self.session = session

    def get_thread_post(self, link, mark='', first=False) -> Tuple[str, str]:
        thread = re.search(r'(?<=&tid=)(\d)+(?=&)', link)[0]
        match = re.search(r'(?<=&pid=)(\d)+(?=&)', link)
        if match:
            return thread, match[0]
        result_page = bs(self.load_page(link), 'lxml')
        if first:
            return thread, result_page.find('td', class_='t_f')['id'].split('_')[-1]
        else:
            for reply in result_page.find_all('td', class_='t_f'):
                if mark in reply.get_text():
                    return thread, reply['id'].split('_')[-1]
            raise RuntimeError("Can't find post")

    def load_page(self, link):
        if not link.startswith('http'):
            link = self.site + '/' + link
        resp = self.session.get(link).content.decode()
        if 'function getName(){' in resp:
            resp = self.session.get(self.site + fxxk_dsign(resp)).content.decode()
        return resp

    def post_thread(self, forum, ttype, subject, message, dzcode=True):
        resp = self.load_page(new_forum.format(site=self.site, fid=forum))
        formhash_pos = resp.find(formhash_prefix)
        self.session.get(new_accept.format(site=self.site))
        formdata = new_thread_formdata_tmpl
        formdata["posttime"] = now()
        formdata["fid"] = forum
        formdata["typeid"] = ttype
        formdata["subject"] = subject
        formdata["message"] = random_mark()
        formdata["formhash"] = resp[formhash_pos + 44: formhash_pos + 52]
        if dzcode:
            formdata["wysiwyg"] = "0"
        post_resp = self.session.post(new_action.format(site=self.site, fid=forum), data=formdata,
                                      allow_redirects=False)
        link = post_resp.headers["location"]
        thread, post = self.get_thread_post(link, first=True)
        return self.edit_main_thread(forum, ttype, thread, post, subject, message, dzcode)

    def reply_thread(self, forum, thread, message, dzcode=True):
        resp = self.load_page(load_reply.format(site=self.site, fid=forum, tid=thread))
        formhash_pos = resp.find(formhash_prefix)
        self.session.get(reply_accept.format(site=self.site))
        formdata = new_reply_formdata_tmpl
        formdata["posttime"] = now()
        mark = random_mark()
        formdata["message"] = mark
        formdata["formhash"] = resp[formhash_pos + 44: formhash_pos + 52]
        if dzcode:
            formdata["wysiwyg"] = "0"
        post_resp = self.session.post(new_reply.format(site=self.site, fid=forum, tid=thread), data=formdata,
                                      allow_redirects=False)
        link = post_resp.headers["location"]
        _, post = self.get_thread_post(link, mark=mark)
        return self.edit_reply_thread(forum, thread, post, message, dzcode)

    def fastreply_thread(self, forum, thread, message, dzcode=False):
        resp = self.load_page(load_thread.format(site=self.site, tid=thread))
        formhash_pos = resp.find(formhash_prefix)
        self.session.get(reply_accept.format(site=self.site))
        formdata = new_fastreply_formdata_tmpl
        formdata["posttime"] = now()
        formdata["message"] = message
        formdata["formhash"] = resp[formhash_pos + 44: formhash_pos + 52]
        self.session.post(new_reply.format(site=self.site, fid=forum, tid=thread), data=formdata, allow_redirects=False)

    def edit_main_thread(self, forum, ttype, thread, post, subject, message, dzcode=True):
        resp = self.load_page(edit_forum.format(site=self.site, tid=thread, fid=forum, pid=post))
        formhash_pos = resp.find(formhash_prefix)
        self.session.get(edit_accept.format(site=self.site))
        formdata = edit_main_thread_formdata_tmpl
        formdata["posttime"] = now()
        formdata["fid"] = forum
        formdata["typeid"] = ttype
        formdata["tid"] = thread
        formdata["pid"] = post
        formdata["subject"] = subject
        formdata["message"] = message
        formdata["formhash"] = resp[formhash_pos + 44: formhash_pos + 52]
        if dzcode:
            formdata["wysiwyg"] = "0"
        self.session.post(edit_action.format(site=self.site), data=formdata, allow_redirects=False)
        return forum, thread, post

    def edit_reply_thread(self, forum, thread, post, message, dzcode=True):
        # resp = self.session.get(find_reply.format(site=self.site, tid=thread, pid=post), allow_redirects=False)
        # page = re.search(r'(?<=&page=)(\d)+(?=[&#])', resp.headers["location"])[0]
        resp = self.load_page(edit_forum.format(site=self.site, tid=thread, fid=forum, pid=post))
        formhash_pos = resp.find(formhash_prefix)
        self.session.get(edit_accept.format(site=self.site))
        formdata = edit_reply_thread_formdata_tmpl
        formdata["posttime"] = now()
        formdata["fid"] = forum
        formdata["tid"] = thread
        formdata["pid"] = post
        formdata["message"] = message
        # formdata["page"] = page
        formdata["formhash"] = resp[formhash_pos + 44: formhash_pos + 52]
        if dzcode:
            formdata["wysiwyg"] = "0"
        self.session.post(edit_action.format(site=self.site), data=formdata, allow_redirects=False)
        return forum, thread, post
