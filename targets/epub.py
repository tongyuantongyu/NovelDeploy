import os
import shutil
import datetime

from ebooklib import epub

from toolbox.tools import Now
from compiler import epub_html

now = Now()

css = """body{padding:0;margin:0;line-height:1.2;text-align:justify}
p{text-indent:2em;display:block;line-height:1.3;margin-top:0.6em;margin-bottom:0.6em}
div{margin:0;padding:0;line-height:1.2;text-align:justify}
h1{font-size:1.4em;line-height:1.2;margin-top:1em;margin-bottom:1.2em;font-weight:bold;text-align:center !important}

.notetag{font-size:0.8em;vertical-align:super;font-weight:bold;color:#960014;text-decoration:none}
"""


def build_page(book: epub.EpubBook, file, filename):
    tex = open(file, "rb").read()
    title, content = epub_html.compile(tex)
    page = epub.EpubHtml(title=title, file_name=filename + ".xhtml", content=content, lang='zh')
    page.add_link(href='./style/style.css', rel='stylesheet', type='text/css')
    link = epub.Link(filename + ".xhtml", title, "chap_" + filename)
    book.add_item(page)
    book.spine.append(page)
    return link


def work(project, _vars):
    book = epub.EpubBook()
    book.set_identifier(_vars.nid)
    book.set_title(_vars.title)
    book.set_language('zh')
    book.add_author(_vars.author)
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubItem(uid="style_nav", file_name="style/style.css", media_type="text/css", content=css))
    book.spine = ['nav']
    book.add_metadata('DC', 'description', _vars.description)
    book.toc = tuple((epub.Section(title),
                      tuple(build_page(book, f'./{project}/{file}', file.replace(".tex", "")) for file in files))
                     for title, files in _vars.menu.items())
    epub.write_epub(f"./artifacts/{project}/epub/{project}_latest.epub", book, {'epub3_pages': False})
    shutil.copy(f"./artifacts/{project}/epub/{project}_latest.epub",
                f"./artifacts/{project}/epub/history/{project}_{datetime.datetime.now().strftime('%y%m%d')}.epub")
    _abspath = os.path.abspath(f"./artifacts/{project}/epub/{project}_latest.epub")
    print(f'[{now}] Epub file saved at {_abspath}.')
