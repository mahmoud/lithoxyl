# -*- coding: utf-8 -*-

import re
from collections import namedtuple


_pos_farg_re = re.compile('({{)|'         # escaped open-brace
                          '(}})|'         # escaped close-brace
                          '({[:!.\[}])')  # anon positional format arg


def infer_positional_format_args(fstr):
    # TODO: memoize
    ret, max_anon = '', 0
    # look for {: or {! or {. or {[ or {}
    start, end, prev_end = 0, 0, 0
    for match in _pos_farg_re.finditer(fstr):
        start, end, group = match.start(), match.end(), match.group()
        if prev_end < start:
            ret += fstr[prev_end:start]
        prev_end = end
        if group == '{{' or group == '}}':
            ret += group
            continue
        ret += '{%s%s' % (max_anon, group[1:])
        max_anon += 1
    ret += fstr[prev_end:]
    return ret


PFAT = namedtuple("PositionalFormatArgTest", "fstr arg_vals res")


_PFATS = [PFAT('{} {} {}', ('hi', 'hello', 'bye'), "hi hello bye"),
          PFAT('{:d} {}', (1, 2), "1 2"),
          PFAT('{!s} {!r}', ('str', 'repr'), "str 'repr'"),
          PFAT('{[hi]}, {.__name__!r}', ({'hi': 'hi'}, re), "hi, 're'"),
          PFAT('{{joek}} ({} {})', ('so', 'funny'), "{joek} (so funny)")]


def test_pos_infer():
    for i, (tmpl, args, res) in enumerate(_PFATS):
        converted = infer_positional_format_args(tmpl)
        assert converted.format(*args) == res


if __name__ == '__main__':
    test_pos_infer()
