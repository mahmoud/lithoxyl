# -*- coding: utf-8 -*-

import sys
import inspect
import itertools


class EncodingLookupError(LookupError):
    pass


class ErrorBehaviorLookupError(LookupError):
    pass


def check_encoding_settings(encoding, errors, reraise=True):
    try:
        # then test error-handler
        u''.encode(encoding)
    except LookupError as le:
        if reraise:
            raise EncodingLookupError(le.message)
        return False
    try:
        # then test error-handler
        # python2.6 does not support kwargs for encode
        u'\xdd'.encode('ascii', errors)
    except LookupError as le:
        if reraise:
            raise ErrorBehaviorLookupError(le.message)
        return False
    except Exception:
        # that ascii encode should never work
        return True


def unwrap(target, attr_name):
    wrapped_func = getattr(target, attr_name)
    try:
        unwrapped_func = wrapped_func.__lithoxyl_wrapped__[3]
    except Exception:
        raise ValueError('%s does not appear to be a wrapped function'
                         % wrapped_func)
    setattr(target, attr_name, unwrapped_func)
    return


def unwrap_all(target=None):
    if target is None or isinstance(target, int):
        target = target or 1
        try:
            target_module_name = sys._getframe(target).f_globals.__name__
            calling_module = sys.modules[target_module_name]
        except Exception:
            raise ValueError('unable to wrap all with target: %r' % target)
        target = calling_module

    for attr_name in dir(target):
        try:
            unwrap(target, attr_name)
        except ValueError:
            continue
    return


def wrap_all(logger, level='info', target=None, skip=None,
             label=None, level_map=None, extras=None):
    """
    """
    ret = []
    extras = extras or {}
    level_map = level_map or {}

    if target is None or isinstance(target, int):
        target = target or 1
        try:
            target_module_name = sys._getframe(target).f_globals.__name__
            calling_module = sys.modules[target_module_name]
        except Exception:
            raise ValueError('unable to wrap all with target: %r' % target)
        target = calling_module

    if skip is None:
        skip = '_'
    if isinstance(skip, basestring):
        skip_func = lambda attr_name: skip and attr_name.startswith(skip)
    elif callable(skip):
        skip_func = skip
    else:
        raise ValueError('skip expected string prefix or callable, not %r' %
                         (skip,))

    if label is None:
        try:
            label = target.__name__
        except AttributeError:
            label = '(%s@%s)' % (target.__class__.__name__, hex(id(target)))
    label = str(label)

    for attr_name in dir(target):
        if skip_func(attr_name):
            continue
        val = getattr(target, attr_name)
        if not callable(val) or isinstance(val, type):
            continue
        kwargs = dict(extras)

        kwargs['level'] = level_map.get(attr_name, level)
        kwargs['action_name'] = label + '.' + attr_name

        log_wrapper = logger.wrap(**kwargs)

        wrapped_func = log_wrapper(val)
        setattr(target, attr_name, wrapped_func)
        ret.append(attr_name)

    return ret


"""decorator.py is bad because it excessively changes your decorator
API to be reliant on decorator.py's strange aesthetic. A pre-existing
decorator can't easily be migrated, and a decorator.py decorator is
not compatible with functools.wraps.

Function signature propagation is orthogonal to closure usage. The
author of decorator.py seems to find a problem with having a function
inside of a function and/or relying on closures and/or functools.wraps
interface.
"""
