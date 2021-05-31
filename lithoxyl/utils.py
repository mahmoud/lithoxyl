# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from __future__ import absolute_import
import os
import sys
import time
import types
import socket
import hashlib
import binascii
from os import getpid

PY3 = sys.version_info[0] == 3

try:
    basestring
    type_types = (type, types.ClassType)
except NameError:
    basestring = str
    type_types = (type,)

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
            raise EncodingLookupError(le.args[0])
        return False
    try:
        # then test error-handler
        # python2.6 does not support kwargs for encode
        u'\xdd'.encode('ascii', errors)
    except LookupError as le:
        if reraise:
            raise ErrorBehaviorLookupError(le.args[0])
        return False
    except Exception:
        # that ascii encode should never work
        return True


def unwrap(target, attr_name):
    wrapped_func = getattr(target, attr_name)
    try:
        unwrapped_func = wrapped_func.__lithoxyl_wrapped__[3]
    except Exception:
        raise ValueError('%r does not appear to be a wrapped function'
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

    unwrapped = set()

    def unwrap_sub_target(sub_target):
        for attr_name in dir(sub_target):
            try:
                val = getattr(sub_target, attr_name)
            except AttributeError:
                continue
            if not callable(val):
                continue
            elif isinstance(val, type_types):
                if id(val) in unwrapped:
                    continue
                unwrapped.add(id(val))
                unwrap_sub_target(val)
            else:
                try:
                    unwrap(sub_target, attr_name)
                except ValueError:
                    continue
        return

    unwrap_sub_target(target)
    return


def wrap_all(logger, level='info', target=None, skip=None,
             label=None, level_map=None, extras=None, depth=1,
             skip_exc=False):
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
    if skip_exc is True:
        skip_exc = Exception
    elif skip_exc is False:
        skip_exc = ()

    if label is None:
        try:
            label = target.__name__
        except AttributeError:
            label = '(%s@%s)' % (target.__class__.__name__, hex(id(target)))
    label = str(label)

    wrapped = set()

    def wrap_sub_target(sub_target, depth=depth, label=label):
        for attr_name in dir(sub_target):
            if skip_func(attr_name):
                continue
            val = getattr(sub_target, attr_name)
            if not callable(val):
                continue
            elif isinstance(val, type_types):
                # NOTE: it may be possible to get to the same function / method
                # via different attribute paths; we will pick one of them randomly
                # in that case for implementation simplicity
                if depth <= 0 or id(val) in wrapped:
                    continue
                wrapped.add(id(val))
                wrap_sub_target(val, depth - 1, label + '.' + attr_name)
            elif not hasattr(val, '__name__'):
                continue
            else:
                kwargs = dict(extras)

                kwargs['level'] = level_map.get(attr_name, level)
                kwargs['action_name'] = label + '.' + attr_name

                log_wrapper = logger.wrap(**kwargs)
                try:
                    wrapped_func = log_wrapper(val)
                    setattr(sub_target, attr_name, wrapped_func)
                except skip_exc:
                    continue

                ret.append(label + '.' + attr_name)
        return

    wrap_sub_target(target)

    return ret


# I'd love to use UUID.uuid4, but this is 10-20x faster
# 12 bytes (96 bits) means that there's 1 in 2^32 chance of a collision
# after 2^64 messages.
# TODO: fallback to UUID if hashlib isn't available?

def reseed_guid():
    """This is called automatically on fork by the functions below. You
    probably don't need to call this.
    """
    global _PID
    global _GUID_SALT
    global _GUID_START

    try:
        random_hex = os.urandom(4).hex()
    except AttributeError:
        # py2
        random_hex = binascii.hexlify(os.urandom(4))

    _PID = getpid()
    _GUID_SALT = '-'.join([str(getpid()),
                           socket.gethostname() or '<nohostname>',
                           str(time.time()),
                           random_hex])
    _GUID_START = int(hashlib.sha1(_GUID_SALT.encode('utf8')).hexdigest()[:24], 16)

    return


# set in reseed
_PID = None
_GUID_SALT = None
_GUID_START = None


reseed_guid()


def int2hexguid(id_int):
    """
    I'd love to use UUID.uuid4, but this is 20x faster

    sha1 is 20 bytes. 12 bytes (96 bits) means that there's 1 in 2^32
    chance of a collision after 2^64 messages.
    """
    return hashlib.sha1((_GUID_SALT + str(id_int)).encode('utf8')).hexdigest()[:24]


def int2hexguid_seq(id_int):
    """Much like int2hexguid, this function returns a fork-safe,
    globally-unique, 12-character hexadecimal string, based on an
    integer input. Intended for use with the always-incrementing
    action_ids and event_ids.

    This variant is specialized for use in autoincrementing use cases
    like action_id and event_id, as the guids it produces will
    maintain the same sortability characteristics as the original
    ID. (as the input integer increments, so will the output GUID)
    """
    if getpid() != _PID:
        reseed_guid()
    return '%x' % (_GUID_START + id_int)


"""decorator.py is bad because it excessively changes your decorator
API to be reliant on decorator.py's strange aesthetic. A pre-existing
decorator can't easily be migrated, and a decorator.py decorator is
not compatible with functools.wraps.

Function signature propagation is orthogonal to closure usage. The
author of decorator.py seems to find a problem with having a function
inside of a function and/or relying on closures and/or functools.wraps
interface.
"""

# from six, handling the change in py3's raise keyword
if PY3:
    try:
        exec_ = getattr(__builtins__, 'exec')
    except AttributeError:
        exec_ = __builtins__.get('exec')

    def reraise(tp, value, tb=None):
        try:
            if value is None:
                value = tp()
            if value.__traceback__ is not tb:
                raise value.with_traceback(tb)
            raise value
        finally:
            value = None
            tb = None

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec_("""def reraise(tp, value, tb=None):
    try:
        raise tp, value, tb
    finally:
        tb = None
""")
