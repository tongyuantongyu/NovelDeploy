from requests import Session

from _credential import _hd, _lightnovel_cookie
from toolbox import discuz, storage
from toolbox.tools import Now
from compiler import bbcode

now = Now()

session = Session()
session.cookies.update(_lightnovel_cookie)
session.headers.update(_hd)

LK = discuz.Discuz('https://www.lightnovel.cn', session)


def work(project, _vars):
    post_hash = storage.Storage(project, 'lightnovel')
    menu_item_list = []
    for section_title, files in _vars.menu.items():
        menu_item_list.append(f'\n[size=3][b]{section_title}[/b][/size]\n')
        print(f'[{now}] Update posts for section {section_title}: ')
        for file in files:
            print(file, end='-', flush=True)
            title, content = bbcode.compile(open(f'./{project}/{file}', "rb").read(), sub_characters=_vars.sub_characters)
            title = _vars.lk_title_format(file, section_title, title)
            combined = f"[b][size=3]{title}[/size][/b]\n\n\n{content}"
            if file in post_hash:
                record = post_hash[file]
                forum, thread, post = record.pos_info()
                if record.need_update(title, content):
                    print('Edit', end='', flush=True)
                    LK.edit_reply_thread(forum, thread, post, combined)
                    print('ed ', end='', flush=True)
                else:
                    print('Pass ', end='', flush=True)
            else:
                print('Post', end='', flush=True)
                forum, thread, post = LK.reply_thread(_vars.lk_forum_id, _vars.lk_thread_id, combined)
                post_hash.add_record(storage.Record.new_content(file, forum, thread, post, title, content))
                print('ed ', end='', flush=True)
            menu_item_list.append(f'[url=https://www.lightnovel.cn/'
                                  f'forum.php?mod=redirect&goto=findpost&ptid={thread}&pid={post}]{title}[/url]')
        print(f'\n[{now}] Update posts for section {section_title}: Finished.')
    menu_bbcode = '\n'.join(menu_item_list)[1:]
    print(f'[{now}] Update menu: ', end='', flush=True)
    if post_hash['menu'].need_update('', menu_bbcode):
        forum, thread, post = post_hash['menu'].pos_info()
        LK.edit_reply_thread(forum, thread, post, menu_bbcode)
        print('Finished.')
    else:
        print('Passed.')
