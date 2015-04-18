# -*- coding: utf-8 -*-
import sys
import time
sys.path.append('..')

from tabulate import tabulate
from lithoxyl import Logger
from lithoxyl.fields import BASIC_FIELDS, ISO8601_FIELDS
from lithoxyl.formatters import Formatter


def summarize(text, length):
    if length < 0:
        return text
    text = text.strip()
    len_diff = len(text) - length
    if len_diff <= 0:
        return text
    return ''.join([text[:length/2].strip(),
                    ' ... ',
                    text[-length/2:].strip()])


## Setting up test record
def get_test_record():
    logger = Logger('test_logger')
    with logger.critical('test_task', reraise=False) as test_rec:
        time.sleep(0.7)
        test_rec['item'] = 'my_item'
        test_rec.warn("things aren't looking great")
        test_rec.failure('task status: {status_str}')
        raise ValueError('unexpected value for {item}')
    return test_rec

test_rec = get_test_record()


def get_field_table_text(fields, quoted, maxlen=36, indent=True):
    rows = []
    headers = ['Name', 'Example', 'Description']
    if quoted:
        headers.append('Quoted')
    for f in fields:
        example = Formatter('{' + f.fname + '}').format_record(test_rec)
        row = ['``' + f.fname + '``', '``' + summarize(example, maxlen) + '``', 'X' + (' ' * 30) + 'X']
        if quoted:
            row.append('Y' if f.quote else ' ')
        rows.append(row)
    text = tabulate(rows, headers=headers, tablefmt='grid')
    if indent:
        text = '    ' + ('\n    '.join(text.splitlines()))
    return text


print get_field_table_text(BASIC_FIELDS, quoted=True)
print
print get_field_table_text(ISO8601_FIELDS, quoted=False)
