# -*- coding: utf-8 -*-
import sys
import time
sys.path.append('..')

from tabulate import tabulate
from lithoxyl import Logger
from lithoxyl.sensible import BASIC_FIELDS, ISO8601_FIELDS, SensibleMessageFormatter as SMF


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
    headers = ['Name', 'Description', 'Example']
    if quoted:
        headers.append('Quoted')
    for f in fields:
        example = SMF('{' + f.fname + '}').format(test_rec.end_event)
        row = ['``' + f.fname + '``', 'X' + (' ' * 60) + 'X', '``' + summarize(example, maxlen) + '``']
        if quoted:
            row.append('Y' if f.quote else ' ')
        rows.append(row)
    text = tabulate(rows, headers=headers, tablefmt='grid')
    if indent:
        text = '    ' + ('\n    '.join(text.splitlines()))
    return text


print get_field_table_text(BASIC_FIELDS, quoted=False)
print
print get_field_table_text(ISO8601_FIELDS, quoted=False)
