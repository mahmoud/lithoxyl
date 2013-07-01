# -*- coding: utf-8 -*-

import re
from string import Formatter
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


_INTCHARS = 'bcdoxXn'
_FLOATCHARS = 'eEfFgGn%'
_TYPE_MAP = dict([(x, int) for x in _INTCHARS] +
                 [(x, float) for x in _FLOATCHARS])


def get_format_args(fstr):
    # TODO: memoize
    formatter = Formatter()
    fargs, fkwargs, _dedup = [], [], set()

    def _add_arg(argname, type_char='s'):
        if argname not in _dedup:
            _dedup.add(argname)
            argtype = _TYPE_MAP.get(type_char, str)  # TODO: unicode
            try:
                fargs.append((int(argname), argtype))
            except ValueError:
                fkwargs.append((argname, argtype))

    for lit, fname, fspec, conv in formatter.parse(fstr):
        if fname is not None:
            type_char = fspec[-1:]
            try:
                # TODO: doesn't handle compound lookups
                base_fname = re.split('[.[]', fname)[0]
                assert base_fname
            except (IndexError, AssertionError):
                raise ValueError('encountered anonymous positional argument')
            _add_arg(fname, type_char)
            for sublit, subfname, _, _ in formatter.parse(fspec):
                # TODO: positional and anon args not allowed here.
                if subfname is not None:
                    _add_arg(subfname)
    return fargs, fkwargs


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


_TEST_TMPLS = ["example 1: {hello}",
               "example 2: {hello:*10}",
               "example 3: {hello:*{width}}",
               "example 4: {hello:{fchar}{width}}, {width}",
               "example 5: {0}, {1:d}, {2:f}, {1}",
               "example 6: {}, {}, {}, {1}"]


def test_get_fstr_args():
    results = []
    for t in _TEST_TMPLS:
        inferred_t = infer_positional_format_args(t)
        res = get_format_args(inferred_t)
        print res
        results.append(res)
    return results


if __name__ == '__main__':
    test_pos_infer()
    test_get_fstr_args()
