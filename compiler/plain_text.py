import re
from typing import Match, Callable, Tuple

fnorder = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '⑪', '⑫', '⑬', '⑭', '⑮', '⑯',
           '⑰', '⑱', '⑲', '⑳', '㉑', '㉒', '㉓', '㉔', '㉕', '㉖', '㉗', '㉘', '㉙', '㉚', '㉛', '㉜',
           '㉝', '㉞', '㉟', '㊱', '㊲', '㊳', '㊴', '㊵', '㊶', '㊷', '㊸', '㊹', '㊺', '㊻', '㊼', '㊽',
           '㊾', '㊿']
oforder = ['❶', '❷', '❸', '❹', '❺', '❻', '❼', '❽', '❾', '❿', '⓫', '⓬', '⓭', '⓮', '⓯', '⓰',
           '⓱', '⓲', '⓳', '⓴']


class FootnoteStorage:
    def __init__(self):
        self.footnotes = []

    def add(self, footnote):
        self.footnotes.append(footnote)
        return len(self.footnotes) - 1

    def __str__(self):
        _str = "译者注释：\n"
        for index, item in enumerate(self.footnotes):
            item = item.replace('\\\\', '\n')
            _str += f"{fnorder[index]}{item}\n"
        return _str[:-1]

    def __bool__(self):
        return bool(self.footnotes)


class OFootnoteStorage:
    def __init__(self):
        self.footnotes = []

    def add(self, footnote):
        self.footnotes.append(footnote)
        return len(self.footnotes) - 1

    def __str__(self):
        _str = "作者注释：\n"
        for index, item in enumerate(self.footnotes):
            item = item.replace('\\\\', '\n')
            _str += f"{oforder[index]}{item}\n"
        return _str[:-1]

    def __bool__(self):
        return bool(self.footnotes)


class EmptyTexError(RuntimeError):
    def __init__(self, *args):
        super().__init__(self, *args)


def gen_ruby_plain_text(match: Match) -> str:
    """Convert matched ruby tex code into plain text for bbs usage
    \ruby{A}{B} -> A（B）

    Also support | split ruby
    \ruby{椎名|真昼}{しいな|まひる} -> 椎名（しいな）真昼（まひる）
    """
    return ''.join('{}（{}）'.format(*pair) for pair in
                   zip(match['word'].split('|'), match['ruby'].split('|')))


def format_line(source_line: str, fts: FootnoteStorage, ofs: OFootnoteStorage) -> str:
    if '\\psline' in source_line:
        return '-' * 30
    if '\\vspace{2\\baselineskip}' in source_line:
        return '\n'
    if '\\begin{itemize}' in source_line:
        return ''
    if '\\end{itemize}' in source_line:
        return ''
    if '\\item' in source_line:
        return '· ' + source_line.replace('\\item', '').replace(' ', '')
    additional_line = ''
    processed_line = source_line
    # {\jpfont にほんご} -> にほんご
    processed_line = processed_line.replace("\\sqsplit", "◇◇◇◇◇◇◇◇")
    processed_line = processed_line.replace("\\cardline", "  --------")
    processed_line = re.sub(r'\\textbf{(?P<word>.+?)}', '\\g<word>', processed_line)
    processed_line = re.sub(r'\\gray{(?P<word>.+?)}', '\\g<word>', processed_line)
    processed_line = re.sub(r' {\\jpfont (?P<word>.+?)}', '\\g<word>', processed_line)
    processed_line = re.sub(r'(?<=}){\\jpfont (?P<word>.+?)}(?!\|)', '{\\g<word>}', processed_line)
    processed_line = re.sub(r'(?<=[{|]){\\jpfont (?P<word>.+?)}', '\\g<word>', processed_line)
    processed_line = processed_line.replace('\\trans{', '\\ruby{')
    # format ruby using ruby_func
    processed_line = re.sub(r'\\ruby{(?P<word>.+?)}{(?P<ruby>.+?)}', gen_ruby_plain_text, processed_line)
    for match in re.finditer(r'\\footnote{(?P<note>.+?)}', processed_line):
        processed_line = processed_line.replace(match[0], fnorder[fts.add(match['note'])])
    for match in re.finditer(r'\\ofnote{(?P<note>.+?)}', processed_line):
        processed_line = processed_line.replace(match[0], oforder[ofs.add(match['note'])])
    if processed_line.endswith("\\\\"):
        processed_line = processed_line[:-2] + "\n"
    return processed_line


def format_title(source_title: str, fts: FootnoteStorage, ofs: OFootnoteStorage) -> str:
    data = re.search('(?<=\\\\subsection)(\\[(?P<plain_title>.+)\\])?({(?P<title>.+)\\})', source_title)
    t = re.sub(r' {\\jpfont (?P<word>.+?)}', '\\g<word>', data.group('title'))
    t = re.sub(r'(?<=}){\\jpfont (?P<word>.+?)}(?!\|)', '{\\g<word>}', t)
    t = re.sub(r'(?<=[{|]){\\jpfont (?P<word>.+?)}', '\\g<word>', t)
    t = re.sub(r'\\ruby{(?P<word>.+?)}{(?P<ruby>.+?)}', '\\g<word>', t)
    for match in re.finditer(r'\\footnote{(?P<note>.+?)}', t):
        t = t.replace(match[0], fnorder[fts.add(match['note'])])
    for match in re.finditer(r'\\ofnote{(?P<note>.+?)}', t):
        t = t.replace(match[0], oforder[ofs.add(match['note'])])
    return t


def compile(tex, sub_characters=None):
    fts = FootnoteStorage()
    ofs = OFootnoteStorage()
    try:
        tex = tex.decode()
    except AttributeError:
        pass
    sl = [i for i in tex.split('\n') if i if not i.startswith('%')]
    ol = []
    if not sl or not sl[0].startswith('\\'):
        raise EmptyTexError()
    title = format_title(sl[0], fts, ofs)
    for line in (s for s in sl[1:] if s):
        if '\\' not in line:
            ol.append(line)
        else:
            ol.append(format_line(line, fts, ofs))
    if not ol:
        raise EmptyTexError()
    content = '\n'.join(ol)
    if ofs:
        content += f"\n------------------------------\n{str(ofs)}"
    if fts:
        content += f"\n------------------------------\n{str(fts)}"
    if sub_characters:
        for source, replace in sub_characters:
            content = content.replace(source, replace)
    return title, content
