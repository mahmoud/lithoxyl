import os
import time
import codecs


_MAX_I = 99
unit_pattern_list = [('s', 1,
                      "%Y-%m-%d_%H-%M-%S",
                      r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$"),
                     ('m', 60,
                      "%Y-%m-%d_%H-%M",
                      r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}$"),
                     ('h', 60 * 60,
                      "%Y-%m-%d_%H",
                      r"^\d{4}-\d{2}-\d{2}_\d{2}$"),
                     ('d', 60 * 60 * 24,
                      "%Y-%m-%d",
                      r"^\d{4}-\d{2}-\d{2}$")]
unit_pattern_map = dict([(x[0], x[1:]) for x in unit_pattern_list])


def open_timestamped(filename,
                     mode='r',
                     encoding=None,
                     errors='strict',
                     buffering=None,
                     time_unit='m',
                     time_count=1.0):
    try:
        time_char = time_unit.lower()[0]
    except:
        raise ValueError('invalid time unit %r, expected one of %r'
                         % (time_unit, sorted(unit_pattern_map.keys())))
    time_count = float(time_count)
    t_secs, t_fmt, t_pattern = unit_pattern_map[time_char]
    #interval = time_count * t_secs
    t_str = time.strftime(t_fmt)
    prefix, extension = os.path.splitext(filename)

    basename = '_'.join([prefix, t_str])
    newname = basename
    if extension:
        newname = basename + extension
    for i in range(_MAX_I):
        if not os.path.exists(newname):
            break
        newname = '.'.join([basename, str(i + 1), extension[1:]])
    if buffering is None:
        buffering = 1
    if encoding is None:
        ret = open(newname, mode, buffering)
    else:
        ret = codecs.open(newname, mode,
                          encoding=encoding,
                          errors=errors,
                          buffering=buffering)
    return ret

"""If a file with prefix_(.*).ext exists, and no pattern is provided,
detect and follow the pattern. If no patterns match, use default
pattern.
"""


if __name__ == '__main__':
    ret = open_timestamped('./tmp/derp.log', 'a')
    print repr(ret)
    ret = open_timestamped('./tmp/derp.log', 'a', encoding='utf-8')
    print repr(ret)
