"""
"Has this ever happened to you?"

Here's an example of some ostensibly well-instrumented code.
"""

import logging

_create_user = lambda: 'a dummy function that supposedly creates the user'


def create_user(name):
    logging.info('creating user with name %r', name)
    try:
        success = _create_user()
        if success:
            logging.info('successfully created user %r', name)
        else:
            logging.error('failed to create user %r', name)
    except Exception:
        logging.critical('exception encountered while creating user %r',
                         name, exc_info=True)
    return success


"""
Notice how the logging statements tend to dominate the code, almost
drowning out the meaning of the code.

Here's lithoxyl's take
"""

from lithoxyl import stderr_log


def create_user(name):
    with stderr_log.critical('user creation', reraise=False) as r:
        success = _create_user()
        if not success:
            r.failure()
