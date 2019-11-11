from requests import Session

from _credential import _hd, _masiro_cookie
from toolbox import discuz, storage
from toolbox.tools import Now
from compiler import bbcode

now = Now()

session = Session()
session.cookies.update(_masiro_cookie)
session.headers.update(_hd)

Masiro = discuz.Discuz('https://masiro.moe', session)


def work(project, _vars):
    post_hash = storage.Storage(project, 'masiro')
    menu_item_list = []
    for section_title, files in _vars.menu.items():
        menu_item_list.append(f'\n[size=3][b]{section_title}[/b][/size]\n')
        print(f'[{now}] Update posts for section {section_title}: ')
        for file in files:
            print(file, end='-', flush=True)
            title, content = bbcode.compile(open(f'./{project}/{file}', "rb").read(), sub_characters=_vars.sub_characters)
            title = _vars.masiro_title_format(file, section_title, title)
            if file in post_hash:
                record = post_hash[file]
                forum, thread, post = record.pos_info()
                if record.need_update(title, content):
                    print('Edit', end='', flush=True)
                    Masiro.edit_main_thread(
                            forum, _vars.masiro_thread_type(section_title, file), thread, post, title, content)
                    print('ed ', end='', flush=True)
                else:
                    print('Pass ', end='', flush=True)
            else:
                print('Post', end='', flush=True)
                forum, thread, post = \
                    Masiro.post_thread(_vars.masiro_forum_id, _vars.masiro_thread_type(section_title, file), title, content)
                post_hash.add_record(storage.Record.new_content(file, forum, thread, post, title, content))
                print('ed ', end='', flush=True)
            menu_item_list.append(f'[url=https://masiro.moe/forum.php?mod=viewthread&tid={thread}]{title}[/url]')
        print(f'\n[{now}] Update posts for section {section_title}: Finished.')
    menu_bbcode = '\n'.join(menu_item_list)[1:]
    print(f'[{now}] Update menu: ', end='', flush=True)
    if post_hash['menu'].need_update(_vars.title + ' - 目录', menu_bbcode):
        forum, thread, post = post_hash['menu'].pos_info()
        Masiro.edit_main_thread(forum, _vars.masiro_menu_thread_type, thread, post, _vars.title + ' - 目录', menu_bbcode)
        print('Finished.')
    else:
        print('Passed.')
