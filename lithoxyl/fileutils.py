import os
import time

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

_MAX_I = 100


def get_rotating_filename(prefix='',
                          extension=None,
                          time_unit='hour',
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
    basename = '_'.join([prefix, t_str])
    filename = basename
    if extension is not None:
        filename = '.'.join([basename, extension])
    for i in range(_MAX_I):
        if not os.path.exists(filename):
            break
        filename = '.'.join([basename, str(i), extension])
    return filename

"""If a file with prefix_(.*).ext exists, and no pattern is provided,
detect and follow the pattern. If no patterns match, use default
pattern.
"""
