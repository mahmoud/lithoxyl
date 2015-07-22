# -*- coding: utf-8 -*-
"""If there is one recurring theme in ``boltons``, it is that Python
has excellent datastructures that constitute a good foundation for
most quick manipulations, as well as building applications. However,
Python usage has grown much faster than builtin data structure
power. Python has a growing need for more advanced general-purpose
data structures which behave intuitively.

The :class:`Table` class is one example. When handed one- or
two-dimensional data, it can provide useful, if basic, text and HTML
renditions of small to medium sized data. It also heuristically
handles recursive data of various formats (lists, dicts, namedtuples,
objects).

For more advanced :class:`Table`-style manipulation check out the
`pandas`_ DataFrame. Text table rendering is based on the `tabulate`_
library.

.. _pandas: http://pandas.pydata.org/
.. _tabulate: https://bitbucket.org/astanin/python-tabulate/
"""

from __future__ import print_function
from __future__ import unicode_literals

import re
import cgi
import types
from itertools import islice
from collections import namedtuple, Sequence, Mapping, MutableSequence
try:
    string_types, integer_types = (str, unicode), (int, long)
    from itertools import izip_longest
    from functools import partial
    _none_type = type(None)
    _int_type = int
    _long_type = long
    _float_type = float
    _text_type = unicode
    _binary_type = str
except:
    # Python 3 compat
    string_types, integer_types = (str, bytes), (int,)
    from itertools import zip_longest as izip_longest
    from functools import reduce, partial
    _none_type = type(None)
    _int_type = int
    _long_type = int
    _float_type = float
    _text_type = str
    _binary_type = bytes

try:
    from typeutils import make_sentinel
    _MISSING = make_sentinel(var_name='_MISSING')
except ImportError:
    _MISSING = object()

# text-rendering types
MIN_PADDING = 2
Line = namedtuple("Line", ["begin", "hline", "sep", "end"])
DataRow = namedtuple("DataRow", ["begin", "sep", "end"])
TableFormat = namedtuple("TableFormat", ["lineabove", "linebelowheader",
                                         "linebetweenrows", "linebelow",
                                         "headerrow", "datarow",
                                         "padding", "with_header_hide"])


"""
Some idle feature thoughts:

* shift around column order without rearranging data
* gotta make it so you can add additional items, not just initialize with
* maybe a shortcut would be to allow adding of Tables to other Tables
* what's the perf of preallocating lists and overwriting items versus
  starting from empty?
* is it possible to effectively tell the difference between when a
  Table is from_data()'d with a single row (list) or with a list of lists?
* CSS: white-space pre-line or pre-wrap maybe?
* Would be nice to support different backends (currently uses lists
  exclusively). Sometimes large datasets come in list-of-dicts and
  list-of-tuples format and it's desirable to cut down processing overhead.

TODO: make iterable on rows?
"""

__all__ = ['Table']


def to_text(obj, maxlen=None):
    try:
        text = unicode(obj)
    except:
        try:
            text = unicode(repr(obj))
        except:
            text = unicode(object.__repr__(obj))
    if maxlen and len(text) > maxlen:
        text = text[:maxlen - 3] + '...'
        # TODO: inverse of ljust/rjust/center
    return text


def escape_html(obj, maxlen=None):
    text = to_text(obj, maxlen=maxlen)
    return cgi.escape(text, quote=True)


_DNR = set((type(None), bool, complex, float,
            type(NotImplemented), slice,
            types.FunctionType, types.MethodType, types.BuiltinFunctionType,
            types.GeneratorType) + string_types + integer_types)


class UnsupportedData(TypeError):
    pass


class InputType(object):
    def __init__(self, *a, **kw):
        pass

    def get_entry_seq(self, data_seq, headers):
        return [self.get_entry(entry, headers) for entry in data_seq]


class DictInputType(InputType):
    def check_type(self, obj):
        return isinstance(obj, Mapping)

    def guess_headers(self, obj):
        return obj.keys()

    def get_entry(self, obj, headers):
        return [obj.get(h) for h in headers]

    def get_entry_seq(self, obj, headers):
        return [[ci.get(h) for h in headers] for ci in obj]


class ObjectInputType(InputType):
    def check_type(self, obj):
        return type(obj) not in _DNR and hasattr(obj, '__class__')

    def guess_headers(self, obj):
        headers = []
        for attr in dir(obj):
            # an object's __dict__ could technically have non-string keys
            try:
                val = getattr(obj, attr)
            except:
                # seen on greenlet: `run` shows in dir() but raises
                # AttributeError. Also properties misbehave.
                continue
            if callable(val):
                continue
            headers.append(attr)
        return headers

    def get_entry(self, obj, headers):
        values = []
        for h in headers:
            try:
                values.append(getattr(obj, h))
            except:
                values.append(None)
        return values


# might be better to hardcode list support since it's so close to the
# core or might be better to make this the copy-style from_* importer
# and have the non-copy style be hardcoded in __init__
class ListInputType(InputType):
    def check_type(self, obj):
        return isinstance(obj, MutableSequence)

    def guess_headers(self, obj):
        return None

    def get_entry(self, obj, headers):
        return obj

    def get_entry_seq(self, obj_seq, headers):
        return obj_seq


class TupleInputType(InputType):
    def check_type(self, obj):
        return isinstance(obj, tuple)

    def guess_headers(self, obj):
        return None

    def get_entry(self, obj, headers):
        return list(obj)

    def get_entry_seq(self, obj_seq, headers):
        return [list(t) for t in obj_seq]


class NamedTupleInputType(InputType):
    def check_type(self, obj):
        return hasattr(obj, '_fields') and isinstance(obj, tuple)

    def guess_headers(self, obj):
        return list(obj._fields)

    def get_entry(self, obj, headers):
        return [getattr(obj, h, None) for h in headers]

    def get_entry_seq(self, obj_seq, headers):
        return [[getattr(obj, h, None) for h in headers] for obj in obj_seq]


class Table(object):
    """
    This Table class is meant to be simple, low-overhead, and extensible. Its
    most common use would be for translation between in-memory data
    structures and serialization formats, such as HTML and console-ready text.

    As such, it stores data in list-of-lists format, and *does not* copy
    lists passed in. It also reserves the right to modify those lists in a
    "filling" process, whereby short lists are extended to the width of
    the table (usually determined by number of headers). This greatly
    reduces overhead and processing/validation that would have to occur
    otherwise.

    General description of headers behavior:

    Headers describe the columns, but are not part of the data, however,
    if the *headers* argument is omitted, Table tries to infer header
    names from the data. It is possible to have a table with no headers,
    just pass in ``headers=None``.

    Supported inputs:

    * :class:`list` of :class:`list` objects
    * :class:`dict` (list/single)
    * :class:`object` (list/single)
    * :class:`collections.namedtuple` (list/single)
    * TODO: DB API cursor?
    * TODO: json

    Supported outputs:

    * HTML
    * Pretty text (also usable as GF Markdown)
    * TODO: CSV
    * TODO: json
    * TODO: json lines

    To minimize resident size, the Table data is stored as a list of lists.
    """

    # order definitely matters here
    _input_types = [DictInputType(), ListInputType(),
                    NamedTupleInputType(), TupleInputType(),
                    ObjectInputType()]

    _html_tr, _html_tr_close = '<tr>', '</tr>'
    _html_th, _html_th_close = '<th>', '</th>'
    _html_td, _html_td_close = '<td>', '</td>'
    # _html_thead, _html_thead_close = '<thead>', '</thead>'
    # _html_tfoot, _html_tfoot_close = '<tfoot>', '</tfoot>'
    _html_table_tag, _html_table_tag_close = '<table>', '</table>'

    def __init__(self, data=None, headers=_MISSING):
        if headers is _MISSING:
            headers = []
            if data:
                headers, data = list(data[0]), islice(data, 1, None)
        self.headers = headers or []
        self._data = []
        self._width = 0
        self.extend(data)

    def extend(self, data):
        """
        Append the given data to the end of the Table.
        """
        if not data:
            return
        self._data.extend(data)
        self._set_width()
        self._fill()

    def _set_width(self, reset=False):
        if reset:
            self._width = 0
        if self._width:
            return
        if self.headers:
            self._width = len(self.headers)
            return
        self._width = max([len(d) for d in self._data])

    def _fill(self):
        width, filler = self._width, [None]
        if not width:
            return
        for d in self._data:
            rem = width - len(d)
            if rem > 0:
                d.extend(filler * rem)
        return

    @classmethod
    def from_dict(cls, data, headers=_MISSING, max_depth=1):
        """Create a Table from a :class:`dict`. Operates the same as
        :meth:`from_data`, but forces interpretation of the data as a
        Mapping.
        """
        return cls.from_data(data=data, headers=headers,
                             max_depth=max_depth, _data_type=DictInputType())

    @classmethod
    def from_list(cls, data, headers=_MISSING, max_depth=1):
        """Create a Table from a :class:`list`. Operates the same as
        :meth:`from_data`, but forces the interpretation of the data
        as a Sequence.
        """
        return cls.from_data(data=data, headers=headers,
                             max_depth=max_depth, _data_type=ListInputType())

    @classmethod
    def from_object(cls, data, headers=_MISSING, max_depth=1):
        """Create a Table from an :class:`object`. Operates the same as
        :meth:`from_data`, but forces the interpretation of the data
        as an object. May be useful for some :class:`dict` and
        :class:`list` subtypes.
        """
        return cls.from_data(data=data, headers=headers,
                             max_depth=max_depth, _data_type=ObjectInputType())

    @classmethod
    def from_data(cls, data, headers=_MISSING, max_depth=1, _data_type=None):
        """Create a Table from any supported data, heuristically
        selecting how to represent the data in Table format.

        Args:
            data (object): Any object or iterable with data to be
                imported to the Table.

            headers (iterable): An iterable of headers to be matched
                to the data. If not explicitly passed, headers will be
                guessed for certain datatypes.

            max_depth (int): The level to which nested Tables should
                be created (default: 1).

            _data_type (InputType subclass): For advanced use cases,
                do not guess the type of the input data, use this data
                type instead.
        """
        # TODO: seen/cycle detection/reuse ?
        # maxdepth follows the same behavior as find command
        # i.e., it doesn't work if max_depth=0 is passed in
        if max_depth < 1:
            return cls(headers=headers)  # return data instead?
        is_seq = isinstance(data, Sequence)
        if is_seq:
            if not data:
                return cls(headers=headers)
            to_check = data[0]
            if not _data_type:
                for it in cls._input_types:
                    if it.check_type(to_check):
                        _data_type = it
                        break
                else:
                    # not particularly happy about this rewind-y approach
                    is_seq = False
                    to_check = data
        else:
            if type(data) in _DNR:
                # hmm, got scalar data.
                # raise an exception or make an exception, nahmsayn?
                return Table([[data]], headers=headers)
            to_check = data
        if not _data_type:
            for it in cls._input_types:
                if it.check_type(to_check):
                    _data_type = it
                    break
            else:
                raise UnsupportedData('unsupported data type %r'
                                      % type(data))
        if headers is _MISSING:
            headers = _data_type.guess_headers(to_check)
        if is_seq:
            entries = _data_type.get_entry_seq(data, headers)
        else:
            entries = [_data_type.get_entry(data, headers)]
        if max_depth > 1:
            new_max_depth = max_depth - 1
            for i, entry in enumerate(entries):
                for j, cell in enumerate(entry):
                    if type(cell) in _DNR:
                        # optimization to avoid function overhead
                        continue
                    try:
                        entries[i][j] = cls.from_data(cell,
                                                      max_depth=new_max_depth)
                    except UnsupportedData:
                        continue
        return cls(entries, headers=headers)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __repr__(self):
        cn = self.__class__.__name__
        if self.headers:
            return '%s(headers=%r, data=%r)' % (cn, self.headers, self._data)
        else:
            return '%s(%r)' % (cn, self._data)

    def to_html(self, orientation=None, wrapped=True,
                with_headers=True, with_newlines=True, max_depth=1):
        """Render this Table to HTML. Configure the structure of Table
        HTML by subclassing and overriding ``_html_*`` class
        attributes.

        Args:
            orientation (str): one of 'auto', 'horizontal', or
                'vertical' (or the first letter of any of
                those). Default 'auto'.
            wrapped (bool): whether or not to include the wrapping
                '<table></table>' tags. Default ``True``, set to
                ``False`` if appending multiple Table outputs or an
                otherwise customized HTML wrapping tag is needed.
            with_newlines (bool): Set to ``True`` if output should
                include added newlines to make the HTML more
                readable. Default ``False``.
            max_depth (int): Indicate how deeply to nest HTML tables
                before simply reverting to :func:`repr`-ing the nested
                data.

        Returns:
            A text string of the HTML of the rendered table.
        """
        lines = []
        headers = []
        if with_headers and self.headers:
            headers.extend(self.headers)
            headers.extend([None] * (self._width - len(self.headers)))
        if wrapped:
            lines.append(self._html_table_tag)
        orientation = orientation or 'auto'
        ol = orientation[0].lower()
        if ol == 'a':
            ol = 'h' if len(self) > 1 else 'v'
        if ol == 'h':
            self._add_horizontal_html_lines(lines, headers=headers,
                                            max_depth=max_depth)
        elif ol == 'v':
            self._add_vertical_html_lines(lines, headers=headers,
                                          max_depth=max_depth)
        else:
            raise ValueError("expected one of 'auto', 'vertical', or"
                             " 'horizontal', not %r" % orientation)
        if wrapped:
            lines.append(self._html_table_tag_close)
        sep = '\n' if with_newlines else ''
        return sep.join(lines)

    def _add_horizontal_html_lines(self, lines, headers, max_depth):
        esc = escape_html
        new_depth = max_depth - 1 if max_depth > 1 else max_depth
        if max_depth > 1:
            new_depth = max_depth - 1
        if headers:
            _thth = self._html_th_close + self._html_th
            lines.append(self._html_tr + self._html_th +
                         _thth.join([esc(h) for h in headers]) +
                         self._html_th_close + self._html_tr_close)
        trtd, _tdtd, _td_tr = (self._html_tr + self._html_td,
                               self._html_td_close + self._html_td,
                               self._html_td_close + self._html_tr_close)
        for row in self._data:
            if max_depth > 1:
                _fill_parts = []
                for cell in row:
                    if isinstance(cell, Table):
                        _fill_parts.append(cell.to_html(max_depth=new_depth))
                    else:
                        _fill_parts.append(esc(cell))
            else:
                _fill_parts = [esc(c) for c in row]
            lines.append(''.join([trtd, _tdtd.join(_fill_parts), _td_tr]))

    def _add_vertical_html_lines(self, lines, headers, max_depth):
        esc = escape_html
        new_depth = max_depth - 1 if max_depth > 1 else max_depth
        tr, th, _th = self._html_tr, self._html_th, self._html_th_close
        td, _tdtd = self._html_td, self._html_td_close + self._html_td
        _td_tr = self._html_td_close + self._html_tr_close
        for i in range(self._width):
            line_parts = [tr]
            if headers:
                line_parts.extend([th, esc(headers[i]), _th])
            if max_depth > 1:
                new_depth = max_depth - 1
                _fill_parts = []
                for row in self._data:
                    cell = row[i]
                    if isinstance(cell, Table):
                        _fill_parts.append(cell.to_html(max_depth=new_depth))
                    else:
                        _fill_parts.append(esc(row[i]))
            else:
                _fill_parts = [esc(row[i]) for row in self._data]
            line_parts.extend([td, _tdtd.join(_fill_parts), _td_tr])
            lines.append(''.join(line_parts))

    def to_text(self, with_headers=True, maxlen=None, style='rst'):
        """Get the Table's textual representation. Only works well
        for Tables with non-recursive data.

        Args:
            with_headers (bool): Whether to include a header row at the top.
            maxlen (int): Max length of data in each cell.
        """
        headers = self.headers if with_headers else ()
        return tabulate(self._data, headers, tablefmt=style)


### Text-rendering based on tabulate follows

# A table structure is suppposed to be:
#
#     --- lineabove ---------
#         headerrow
#     --- linebelowheader ---
#         datarow
#     --- linebewteenrows ---
#     ... (more datarows) ...
#     --- linebewteenrows ---
#         last datarow
#     --- linebelow ---------
#
# TableFormat's line* elements can be
#
#   - either None, if the element is not used,
#   - or a Line tuple,
#   - or a function: [col_widths], [col_alignments] -> string.
#
# TableFormat's *row elements can be
#
#   - either None, if the element is not used,
#   - or a DataRow tuple,
#   - or a function: [cell_values], [col_widths], [col_alignments] -> string.
#
# padding (an integer) is the amount of white space around data values.
#
# with_header_hide:
#
#   - either None, to display all table elements unconditionally,
#   - or a list of elements not to be displayed if the table has column headers.
#


def _pipe_segment_with_colons(align, colwidth):
    """Return a segment of a horizontal line with optional colons which
    indicate column's alignment (as in `pipe` output format)."""
    w = colwidth
    if align in ["right", "decimal"]:
        return ('-' * (w - 1)) + ":"
    elif align == "center":
        return ":" + ('-' * (w - 2)) + ":"
    elif align == "left":
        return ":" + ('-' * (w - 1))
    else:
        return '-' * w


def _pipe_line_with_colons(colwidths, colaligns):
    """Return a horizontal line with optional colons to indicate column's
    alignment (as in `pipe` output format)."""
    segments = [_pipe_segment_with_colons(a, w) for a, w in zip(colaligns, colwidths)]
    return "|" + "|".join(segments) + "|"


def _mediawiki_row_with_attrs(separator, cell_values, colwidths, colaligns):
    alignment = { "left":    '',
                  "right":   'align="right"| ',
                  "center":  'align="center"| ',
                  "decimal": 'align="right"| ' }
    # hard-coded padding _around_ align attribute and value together
    # rather than padding parameter which affects only the value
    values_with_attrs = [' ' + alignment.get(a, '') + c + ' '
                         for c, a in zip(cell_values, colaligns)]
    colsep = separator*2
    return (separator + colsep.join(values_with_attrs)).rstrip()


def _html_row_with_attrs(celltag, cell_values, colwidths, colaligns):
    alignment = { "left":    '',
                  "right":   ' style="text-align: right;"',
                  "center":  ' style="text-align: center;"',
                  "decimal": ' style="text-align: right;"' }
    values_with_attrs = ["<{0}{1}>{2}</{0}>".format(celltag, alignment.get(a, ''), c)
                         for c, a in zip(cell_values, colaligns)]
    return "<tr>" + "".join(values_with_attrs).rstrip() + "</tr>"

def _moin_row_with_attrs(celltag, cell_values, colwidths, colaligns, header=''):
    alignment = { "left":    '',
                  "right":   '<style="text-align: right;">',
                  "center":  '<style="text-align: center;">',
                  "decimal": '<style="text-align: right;">' }
    values_with_attrs = ["{0}{1} {2} ".format(celltag,
                                              alignment.get(a, ''),
                                              header+c+header)
                         for c, a in zip(cell_values, colaligns)]
    return "".join(values_with_attrs)+"||"

def _latex_line_begin_tabular(colwidths, colaligns, booktabs=False):
    alignment = { "left": "l", "right": "r", "center": "c", "decimal": "r" }
    tabular_columns_fmt = "".join([alignment.get(a, "l") for a in colaligns])
    return "\n".join(["\\begin{tabular}{" + tabular_columns_fmt + "}",
                      "\\toprule" if booktabs else "\hline"])

LATEX_ESCAPE_RULES = {r"&": r"\&", r"%": r"\%", r"$": r"\$", r"#": r"\#",
                      r"_": r"\_", r"^": r"\^{}", r"{": r"\{", r"}": r"\}",
                      r"~": r"\textasciitilde{}", "\\": r"\textbackslash{}",
                      r"<": r"\ensuremath{<}", r">": r"\ensuremath{>}"}


def _latex_row(cell_values, colwidths, colaligns):
    def escape_char(c):
        return LATEX_ESCAPE_RULES.get(c, c)
    escaped_values = ["".join(map(escape_char, cell)) for cell in cell_values]
    rowfmt = DataRow("", "&", "\\\\")
    return _build_simple_row(escaped_values, rowfmt)


_table_formats = {"simple":
                  TableFormat(lineabove=Line("", "-", "  ", ""),
                              linebelowheader=Line("", "-", "  ", ""),
                              linebetweenrows=None,
                              linebelow=Line("", "-", "  ", ""),
                              headerrow=DataRow("", "  ", ""),
                              datarow=DataRow("", "  ", ""),
                              padding=0,
                              with_header_hide=["lineabove", "linebelow"]),
                  "plain":
                  TableFormat(lineabove=None, linebelowheader=None,
                              linebetweenrows=None, linebelow=None,
                              headerrow=DataRow("", "  ", ""),
                              datarow=DataRow("", "  ", ""),
                              padding=0, with_header_hide=None),
                  "grid":
                  TableFormat(lineabove=Line("+", "-", "+", "+"),
                              linebelowheader=Line("+", "=", "+", "+"),
                              linebetweenrows=Line("+", "-", "+", "+"),
                              linebelow=Line("+", "-", "+", "+"),
                              headerrow=DataRow("|", "|", "|"),
                              datarow=DataRow("|", "|", "|"),
                              padding=1, with_header_hide=None),
                  "fancy_grid":
                  TableFormat(lineabove=Line("╒", "═", "╤", "╕"),
                              linebelowheader=Line("╞", "═", "╪", "╡"),
                              linebetweenrows=Line("├", "─", "┼", "┤"),
                              linebelow=Line("╘", "═", "╧", "╛"),
                              headerrow=DataRow("│", "│", "│"),
                              datarow=DataRow("│", "│", "│"),
                              padding=1, with_header_hide=None),
                  "pipe":
                  TableFormat(lineabove=_pipe_line_with_colons,
                              linebelowheader=_pipe_line_with_colons,
                              linebetweenrows=None,
                              linebelow=None,
                              headerrow=DataRow("|", "|", "|"),
                              datarow=DataRow("|", "|", "|"),
                              padding=1,
                              with_header_hide=["lineabove"]),
                  "orgtbl":
                  TableFormat(lineabove=None,
                              linebelowheader=Line("|", "-", "+", "|"),
                              linebetweenrows=None,
                              linebelow=None,
                              headerrow=DataRow("|", "|", "|"),
                              datarow=DataRow("|", "|", "|"),
                              padding=1, with_header_hide=None),
                  "jira":
                  TableFormat(lineabove=None,
                              linebelowheader=None,
                              linebetweenrows=None,
                              linebelow=None,
                              headerrow=DataRow("||", "||", "||"),
                              datarow=DataRow("|", "|", "|"),
                              padding=1, with_header_hide=None),
                  "psql":
                  TableFormat(lineabove=Line("+", "-", "+", "+"),
                              linebelowheader=Line("|", "-", "+", "|"),
                              linebetweenrows=None,
                              linebelow=Line("+", "-", "+", "+"),
                              headerrow=DataRow("|", "|", "|"),
                              datarow=DataRow("|", "|", "|"),
                              padding=1, with_header_hide=None),
                  "rst":
                  TableFormat(lineabove=Line("", "=", "  ", ""),
                              linebelowheader=Line("", "=", "  ", ""),
                              linebetweenrows=None,
                              linebelow=Line("", "=", "  ", ""),
                              headerrow=DataRow("", "  ", ""),
                              datarow=DataRow("", "  ", ""),
                              padding=0, with_header_hide=None),
                  "mediawiki":
                  TableFormat(lineabove=Line("{| class=\"wikitable\" style=\"text-align: left;\"",
                                             "", "", "\n|+ <!-- caption -->\n|-"),
                              linebelowheader=Line("|-", "", "", ""),
                              linebetweenrows=Line("|-", "", "", ""),
                              linebelow=Line("|}", "", "", ""),
                              headerrow=partial(_mediawiki_row_with_attrs, "!"),
                              datarow=partial(_mediawiki_row_with_attrs, "|"),
                              padding=0, with_header_hide=None),
                  "moinmoin":
                  TableFormat(lineabove=None,
                              linebelowheader=None,
                              linebetweenrows=None,
                              linebelow=None,
                              headerrow=partial(_moin_row_with_attrs,"||",header="'''"),
                              datarow=partial(_moin_row_with_attrs,"||"),
                              padding=1, with_header_hide=None),
                  "html":
                  TableFormat(lineabove=Line("<table>", "", "", ""),
                              linebelowheader=None,
                              linebetweenrows=None,
                              linebelow=Line("</table>", "", "", ""),
                              headerrow=partial(_html_row_with_attrs, "th"),
                              datarow=partial(_html_row_with_attrs, "td"),
                              padding=0, with_header_hide=None),
                  "latex":
                  TableFormat(lineabove=_latex_line_begin_tabular,
                              linebelowheader=Line("\\hline", "", "", ""),
                              linebetweenrows=None,
                              linebelow=Line("\\hline\n\\end{tabular}", "", "", ""),
                              headerrow=_latex_row,
                              datarow=_latex_row,
                              padding=1, with_header_hide=None),
                  "latex_booktabs":
                  TableFormat(lineabove=partial(_latex_line_begin_tabular, booktabs=True),
                              linebelowheader=Line("\\midrule", "", "", ""),
                              linebetweenrows=None,
                              linebelow=Line("\\bottomrule\n\\end{tabular}", "", "", ""),
                              headerrow=_latex_row,
                              datarow=_latex_row,
                              padding=1, with_header_hide=None),
                  "tsv":
                  TableFormat(lineabove=None, linebelowheader=None,
                              linebetweenrows=None, linebelow=None,
                              headerrow=DataRow("", "\t", ""),
                              datarow=DataRow("", "\t", ""),
                              padding=0, with_header_hide=None)}


tabulate_formats = list(sorted(_table_formats.keys()))


_invisible_codes = re.compile(r"\x1b\[\d*m|\x1b\[\d*\;\d*\;\d*m")  # ANSI color codes
_invisible_codes_bytes = re.compile(b"\x1b\[\d*m|\x1b\[\d*\;\d*\;\d*m")  # ANSI color codes


def simple_separated_format(separator):
    """Construct a simple TableFormat with columns separated by a separator.

    >>> tsv = simple_separated_format("\\t") ; \
        tabulate([["foo", 1], ["spam", 23]], tablefmt=tsv) == 'foo \\t 1\\nspam\\t23'
    True

    """
    return TableFormat(None, None, None, None,
                       headerrow=DataRow('', separator, ''),
                       datarow=DataRow('', separator, ''),
                       padding=0, with_header_hide=None)


def _isconvertible(conv, string):
    try:
        n = conv(string)
        return True
    except (ValueError, TypeError):
        return False


def _isnumber(string):
    """
    >>> _isnumber("123.45")
    True
    >>> _isnumber("123")
    True
    >>> _isnumber("spam")
    False
    """
    return _isconvertible(float, string)


def _isint(string, inttype=int):
    """
    >>> _isint("123")
    True
    >>> _isint("123.45")
    False
    """
    return type(string) is inttype or\
           (isinstance(string, _binary_type) or isinstance(string, _text_type))\
            and\
            _isconvertible(inttype, string)


def _type(string, has_invisible=True):
    """The least generic type (type(None), int, float, str, unicode).

    >>> _type(None) is type(None)
    True
    >>> _type("foo") is type("")
    True
    >>> _type("1") is type(1)
    True
    >>> _type('\x1b[31m42\x1b[0m') is type(42)
    True
    >>> _type('\x1b[31m42\x1b[0m') is type(42)
    True

    """

    if has_invisible and \
       (isinstance(string, _text_type) or isinstance(string, _binary_type)):
        string = _strip_invisible(string)

    if string is None:
        return _none_type
    elif hasattr(string, "isoformat"):  # datetime.datetime, date, and time
        return _text_type
    elif _isint(string):
        return int
    elif _isint(string, _long_type):
        return _long_type
    elif _isnumber(string):
        return float
    elif isinstance(string, _binary_type):
        return _binary_type
    else:
        return _text_type


def _afterpoint(string):
    """Symbols after a decimal point, -1 if the string lacks the decimal point.

    >>> _afterpoint("123.45")
    2
    >>> _afterpoint("1001")
    -1
    >>> _afterpoint("eggs")
    -1
    >>> _afterpoint("123e45")
    2

    """
    if _isnumber(string):
        if _isint(string):
            return -1
        else:
            pos = string.rfind(".")
            pos = string.lower().rfind("e") if pos < 0 else pos
            if pos >= 0:
                return len(string) - pos - 1
            else:
                return -1  # no point
    else:
        return -1  # not a number


def _padleft(width, s, has_invisible=True):
    """Flush right.

    >>> _padleft(6, '\u044f\u0439\u0446\u0430') == '  \u044f\u0439\u0446\u0430'
    True

    """
    iwidth = width + len(s) - len(_strip_invisible(s)) if has_invisible else width
    fmt = "{0:>%ds}" % iwidth
    return fmt.format(s)


def _padright(width, s, has_invisible=True):
    """Flush left.

    >>> _padright(6, '\u044f\u0439\u0446\u0430') == '\u044f\u0439\u0446\u0430  '
    True

    """
    iwidth = width + len(s) - len(_strip_invisible(s)) if has_invisible else width
    fmt = "{0:<%ds}" % iwidth
    return fmt.format(s)


def _padboth(width, s, has_invisible=True):
    """Center string.

    >>> _padboth(6, '\u044f\u0439\u0446\u0430') == ' \u044f\u0439\u0446\u0430 '
    True

    """
    iwidth = width + len(s) - len(_strip_invisible(s)) if has_invisible else width
    fmt = "{0:^%ds}" % iwidth
    return fmt.format(s)


def _strip_invisible(s):
    "Remove invisible ANSI color codes."
    if isinstance(s, _text_type):
        return re.sub(_invisible_codes, "", s)
    else:  # a bytestring
        return re.sub(_invisible_codes_bytes, "", s)


def _visible_width(s):
    """Visible width of a printed string. ANSI color codes are removed.

    >>> _visible_width('\x1b[31mhello\x1b[0m'), _visible_width("world")
    (5, 5)

    """
    if isinstance(s, _text_type) or isinstance(s, _binary_type):
        return len(_strip_invisible(s))
    else:
        return len(_text_type(s))


def _align_column(strings, alignment, minwidth=0, has_invisible=True):
    """[string] -> [padded_string]

    >>> list(map(str,_align_column(["12.345", "-1234.5", "1.23", "1234.5", "1e+234", "1.0e234"], "decimal")))
    ['   12.345  ', '-1234.5    ', '    1.23   ', ' 1234.5    ', '    1e+234 ', '    1.0e234']

    >>> list(map(str,_align_column(['123.4', '56.7890'], None)))
    ['123.4', '56.7890']

    """
    if alignment == "right":
        strings = [s.strip() for s in strings]
        padfn = _padleft
    elif alignment == "center":
        strings = [s.strip() for s in strings]
        padfn = _padboth
    elif alignment == "decimal":
        if has_invisible:
            decimals = [_afterpoint(_strip_invisible(s)) for s in strings]
        else:
            decimals = [_afterpoint(s) for s in strings]
        maxdecimals = max(decimals)
        strings = [s + (maxdecimals - decs) * " "
                   for s, decs in zip(strings, decimals)]
        padfn = _padleft
    elif not alignment:
        return strings
    else:
        strings = [s.strip() for s in strings]
        padfn = _padright

    if has_invisible:
        width_fn = _visible_width
    else:
        width_fn = len

    maxwidth = max(max(map(width_fn, strings)), minwidth)
    padded_strings = [padfn(maxwidth, s, has_invisible) for s in strings]
    return padded_strings


def _more_generic(type1, type2):
    types = { _none_type: 0, int: 1, float: 2, _binary_type: 3, _text_type: 4 }
    invtypes = { 4: _text_type, 3: _binary_type, 2: float, 1: int, 0: _none_type }
    moregeneric = max(types.get(type1, 4), types.get(type2, 4))
    return invtypes[moregeneric]


def _column_type(strings, has_invisible=True):
    """The least generic type all column values are convertible to.

    >>> _column_type(["1", "2"]) is _int_type
    True
    >>> _column_type(["1", "2.3"]) is _float_type
    True
    >>> _column_type(["1", "2.3", "four"]) is _text_type
    True
    >>> _column_type(["four", '\u043f\u044f\u0442\u044c']) is _text_type
    True
    >>> _column_type([None, "brux"]) is _text_type
    True
    >>> _column_type([1, 2, None]) is _int_type
    True
    >>> import datetime as dt
    >>> _column_type([dt.datetime(1991,2,19), dt.time(17,35)]) is _text_type
    True

    """
    types = [_type(s, has_invisible) for s in strings ]
    return reduce(_more_generic, types, int)


def _format(val, valtype, floatfmt, missingval="", has_invisible=True):
    """Format a value accoding to its type.

    Unicode is supported:

    >>> hrow = ['\u0431\u0443\u043a\u0432\u0430', '\u0446\u0438\u0444\u0440\u0430'] ; \
        tbl = [['\u0430\u0437', 2], ['\u0431\u0443\u043a\u0438', 4]] ; \
        good_result = '\\u0431\\u0443\\u043a\\u0432\\u0430      \\u0446\\u0438\\u0444\\u0440\\u0430\\n-------  -------\\n\\u0430\\u0437             2\\n\\u0431\\u0443\\u043a\\u0438           4' ; \
        tabulate(tbl, headers=hrow) == good_result
    True

    """
    if val is None:
        return missingval

    if valtype in [int, _long_type, _text_type]:
        return "{0}".format(val)
    elif valtype is _binary_type:
        try:
            return _text_type(val, "ascii")
        except TypeError:
            return _text_type(val)
    elif valtype is float:
        is_a_colored_number = has_invisible and isinstance(val, (_text_type, _binary_type))
        if is_a_colored_number:
            raw_val = _strip_invisible(val)
            formatted_val = format(float(raw_val), floatfmt)
            return val.replace(raw_val, formatted_val)
        else:
            return format(float(val), floatfmt)
    else:
        return "{0}".format(val)


def _align_header(header, alignment, width):
    if alignment == "left":
        return _padright(width, header)
    elif alignment == "center":
        return _padboth(width, header)
    elif not alignment:
        return "{0}".format(header)
    else:
        return _padleft(width, header)


def _normalize_tabular_data(tabular_data, headers):
    """Transform a supported data type to a list of lists, and a list of headers.

    Supported tabular data types:

    * list-of-lists or another iterable of iterables

    * list of named tuples (usually used with headers="keys")

    * list of dicts (usually used with headers="keys")

    * list of OrderedDicts (usually used with headers="keys")

    * 2D NumPy arrays

    * NumPy record arrays (usually used with headers="keys")

    * dict of iterables (usually used with headers="keys")

    * pandas.DataFrame (usually used with headers="keys")

    The first row can be used as headers if headers="firstrow",
    column indices can be used as headers if headers="keys".

    """

    if hasattr(tabular_data, "keys") and hasattr(tabular_data, "values"):
        # dict-like and pandas.DataFrame?
        if hasattr(tabular_data.values, "__call__"):
            # likely a conventional dict
            keys = tabular_data.keys()
            rows = list(izip_longest(*tabular_data.values()))  # columns have to be transposed
        elif hasattr(tabular_data, "index"):
            # values is a property, has .index => it's likely a pandas.DataFrame (pandas 0.11.0)
            keys = tabular_data.keys()
            vals = tabular_data.values  # values matrix doesn't need to be transposed
            names = tabular_data.index
            rows = [[v]+list(row) for v,row in zip(names, vals)]
        else:
            raise ValueError("tabular data doesn't appear to be a dict or a DataFrame")

        if headers == "keys":
            headers = list(map(_text_type,keys))  # headers should be strings

    else:  # it's a usual an iterable of iterables, or a NumPy array
        rows = list(tabular_data)

        if (headers == "keys" and
            hasattr(tabular_data, "dtype") and
            getattr(tabular_data.dtype, "names")):
            # numpy record array
            headers = tabular_data.dtype.names
        elif (headers == "keys"
              and len(rows) > 0
              and isinstance(rows[0], tuple)
              and hasattr(rows[0], "_fields")):
            # namedtuple
            headers = list(map(_text_type, rows[0]._fields))
        elif (len(rows) > 0
              and isinstance(rows[0], dict)):
            # dict or OrderedDict
            uniq_keys = set() # implements hashed lookup
            keys = [] # storage for set
            if headers == "firstrow":
                firstdict = rows[0] if len(rows) > 0 else {}
                keys.extend(firstdict.keys())
                uniq_keys.update(keys)
                rows = rows[1:]
            for row in rows:
                for k in row.keys():
                    #Save unique items in input order
                    if k not in uniq_keys:
                        keys.append(k)
                        uniq_keys.add(k)
            if headers == 'keys':
                headers = keys
            elif isinstance(headers, dict):
                # a dict of headers for a list of dicts
                headers = [headers.get(k, k) for k in keys]
                headers = list(map(_text_type, headers))
            elif headers == "firstrow":
                if len(rows) > 0:
                    headers = [firstdict.get(k, k) for k in keys]
                    headers = list(map(_text_type, headers))
                else:
                    headers = []
            elif headers:
                raise ValueError('headers for a list of dicts is not a dict or a keyword')
            rows = [[row.get(k) for k in keys] for row in rows]
        elif headers == "keys" and len(rows) > 0:
            # keys are column indices
            headers = list(map(_text_type, range(len(rows[0]))))

    # take headers from the first row if necessary
    if headers == "firstrow" and len(rows) > 0:
        headers = list(map(_text_type, rows[0])) # headers should be strings
        rows = rows[1:]

    headers = list(map(_text_type,headers))
    rows = list(map(list,rows))

    # pad with empty headers for initial columns if necessary
    if headers and len(rows) > 0:
       nhs = len(headers)
       ncols = len(rows[0])
       if nhs < ncols:
           headers = [""]*(ncols - nhs) + headers

    return rows, headers


def tabulate(tabular_data, headers=(), tablefmt="simple",
             floatfmt="g", numalign="decimal", stralign="left",
             missingval=""):
    """Format a fixed width table for pretty printing.

    >>> print(tabulate([[1, 2.34], [-56, "8.999"], ["2", "10001"]]))
    ---  ---------
      1      2.34
    -56      8.999
      2  10001
    ---  ---------

    The first required argument (`tabular_data`) can be a
    list-of-lists (or another iterable of iterables), a list of named
    tuples, a dictionary of iterables, an iterable of dictionaries,
    a two-dimensional NumPy array, NumPy record array, or a Pandas'
    dataframe.


    Table headers
    -------------

    To print nice column headers, supply the second argument (`headers`):

      - `headers` can be an explicit list of column headers
      - if `headers="firstrow"`, then the first row of data is used
      - if `headers="keys"`, then dictionary keys or column indices are used

    Otherwise a headerless table is produced.

    If the number of headers is less than the number of columns, they
    are supposed to be names of the last columns. This is consistent
    with the plain-text format of R and Pandas' dataframes.

    >>> print(tabulate([["sex","age"],["Alice","F",24],["Bob","M",19]],
    ...       headers="firstrow"))
           sex      age
    -----  -----  -----
    Alice  F         24
    Bob    M         19


    Column alignment
    ----------------

    `tabulate` tries to detect column types automatically, and aligns
    the values properly. By default it aligns decimal points of the
    numbers (or flushes integer numbers to the right), and flushes
    everything else to the left. Possible column alignments
    (`numalign`, `stralign`) are: "right", "center", "left", "decimal"
    (only for `numalign`), and None (to disable alignment).


    Table formats
    -------------

    `floatfmt` is a format specification used for columns which
    contain numeric data with a decimal point.

    `None` values are replaced with a `missingval` string:

    >>> print(tabulate([["spam", 1, None],
    ...                 ["eggs", 42, 3.14],
    ...                 ["other", None, 2.7]], missingval="?"))
    -----  --  ----
    spam    1  ?
    eggs   42  3.14
    other   ?  2.7
    -----  --  ----

    Various plain-text table formats (`tablefmt`) are supported:
    'plain', 'simple', 'grid', 'pipe', 'orgtbl', 'rst', 'mediawiki',
     'latex', and 'latex_booktabs'. Variable `tabulate_formats` contains the list of
    currently supported formats.

    "plain" format doesn't use any pseudographics to draw tables,
    it separates columns with a double space:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                 ["strings", "numbers"], "plain"))
    strings      numbers
    spam         41.9999
    eggs        451

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="plain"))
    spam   41.9999
    eggs  451

    "simple" format is like Pandoc simple_tables:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                 ["strings", "numbers"], "simple"))
    strings      numbers
    ---------  ---------
    spam         41.9999
    eggs        451

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="simple"))
    ----  --------
    spam   41.9999
    eggs  451
    ----  --------

    "grid" is similar to tables produced by Emacs table.el package or
    Pandoc grid_tables:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                ["strings", "numbers"], "grid"))
    +-----------+-----------+
    | strings   |   numbers |
    +===========+===========+
    | spam      |   41.9999 |
    +-----------+-----------+
    | eggs      |  451      |
    +-----------+-----------+

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="grid"))
    +------+----------+
    | spam |  41.9999 |
    +------+----------+
    | eggs | 451      |
    +------+----------+

    "fancy_grid" draws a grid using box-drawing characters:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                ["strings", "numbers"], "fancy_grid"))
    ╒═══════════╤═══════════╕
    │ strings   │   numbers │
    ╞═══════════╪═══════════╡
    │ spam      │   41.9999 │
    ├───────────┼───────────┤
    │ eggs      │  451      │
    ╘═══════════╧═══════════╛

    "pipe" is like tables in PHP Markdown Extra extension or Pandoc
    pipe_tables:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                ["strings", "numbers"], "pipe"))
    | strings   |   numbers |
    |:----------|----------:|
    | spam      |   41.9999 |
    | eggs      |  451      |

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="pipe"))
    |:-----|---------:|
    | spam |  41.9999 |
    | eggs | 451      |

    "orgtbl" is like tables in Emacs org-mode and orgtbl-mode. They
    are slightly different from "pipe" format by not using colons to
    define column alignment, and using a "+" sign to indicate line
    intersections:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                ["strings", "numbers"], "orgtbl"))
    | strings   |   numbers |
    |-----------+-----------|
    | spam      |   41.9999 |
    | eggs      |  451      |


    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="orgtbl"))
    | spam |  41.9999 |
    | eggs | 451      |

    "rst" is like a simple table format from reStructuredText; please
    note that reStructuredText accepts also "grid" tables:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]],
    ...                ["strings", "numbers"], "rst"))
    =========  =========
    strings      numbers
    =========  =========
    spam         41.9999
    eggs        451
    =========  =========

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="rst"))
    ====  ========
    spam   41.9999
    eggs  451
    ====  ========

    "mediawiki" produces a table markup used in Wikipedia and on other
    MediaWiki-based sites:

    >>> print(tabulate([["strings", "numbers"], ["spam", 41.9999], ["eggs", "451.0"]],
    ...                headers="firstrow", tablefmt="mediawiki"))
    {| class="wikitable" style="text-align: left;"
    |+ <!-- caption -->
    |-
    ! strings   !! align="right"|   numbers
    |-
    | spam      || align="right"|   41.9999
    |-
    | eggs      || align="right"|  451
    |}

    "html" produces HTML markup:

    >>> print(tabulate([["strings", "numbers"], ["spam", 41.9999], ["eggs", "451.0"]],
    ...                headers="firstrow", tablefmt="html"))
    <table>
    <tr><th>strings  </th><th style="text-align: right;">  numbers</th></tr>
    <tr><td>spam     </td><td style="text-align: right;">  41.9999</td></tr>
    <tr><td>eggs     </td><td style="text-align: right;"> 451     </td></tr>
    </table>

    "latex" produces a tabular environment of LaTeX document markup:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="latex"))
    \\begin{tabular}{lr}
    \\hline
     spam &  41.9999 \\\\
     eggs & 451      \\\\
    \\hline
    \\end{tabular}

    "latex_booktabs" produces a tabular environment of LaTeX document markup
    using the booktabs.sty package:

    >>> print(tabulate([["spam", 41.9999], ["eggs", "451.0"]], tablefmt="latex_booktabs"))
    \\begin{tabular}{lr}
    \\toprule
     spam &  41.9999 \\\\
     eggs & 451      \\\\
    \\bottomrule
    \end{tabular}
    """
    if tabular_data is None:
        tabular_data = []
    list_of_lists, headers = _normalize_tabular_data(tabular_data, headers)

    # optimization: look for ANSI control codes once,
    # enable smart width functions only if a control code is found
    plain_text = '\n'.join(['\t'.join(map(_text_type, headers))] + \
                            ['\t'.join(map(_text_type, row)) for row in list_of_lists])
    has_invisible = re.search(_invisible_codes, plain_text)
    if has_invisible:
        width_fn = _visible_width
    else:
        width_fn = len

    # format rows and columns, convert numeric values to strings
    cols = list(zip(*list_of_lists))
    coltypes = list(map(_column_type, cols))
    cols = [[_format(v, ct, floatfmt, missingval, has_invisible) for v in c]
             for c,ct in zip(cols, coltypes)]

    # align columns
    aligns = [numalign if ct in [int,float] else stralign for ct in coltypes]
    minwidths = [width_fn(h) + MIN_PADDING for h in headers] if headers else [0]*len(cols)
    cols = [_align_column(c, a, minw, has_invisible)
            for c, a, minw in zip(cols, aligns, minwidths)]

    if headers:
        # align headers and add headers
        t_cols = cols or [['']] * len(headers)
        t_aligns = aligns or [stralign] * len(headers)
        minwidths = [max(minw, width_fn(c[0])) for minw, c in zip(minwidths, t_cols)]
        headers = [_align_header(h, a, minw)
                   for h, a, minw in zip(headers, t_aligns, minwidths)]
        rows = list(zip(*cols))
    else:
        minwidths = [width_fn(c[0]) for c in cols]
        rows = list(zip(*cols))

    if not isinstance(tablefmt, TableFormat):
        tablefmt = _table_formats.get(tablefmt, _table_formats["simple"])

    return _format_table(tablefmt, headers, rows, minwidths, aligns)


def _build_simple_row(padded_cells, rowfmt):
    "Format row according to DataRow format without padding."
    begin, sep, end = rowfmt
    return (begin + sep.join(padded_cells) + end).rstrip()


def _build_row(padded_cells, colwidths, colaligns, rowfmt):
    "Return a string which represents a row of data cells."
    if not rowfmt:
        return None
    if hasattr(rowfmt, "__call__"):
        return rowfmt(padded_cells, colwidths, colaligns)
    else:
        return _build_simple_row(padded_cells, rowfmt)


def _build_line(colwidths, colaligns, linefmt):
    "Return a string which represents a horizontal line."
    if not linefmt:
        return None
    if hasattr(linefmt, "__call__"):
        return linefmt(colwidths, colaligns)
    else:
        begin, fill, sep,  end = linefmt
        cells = [fill*w for w in colwidths]
        return _build_simple_row(cells, (begin, sep, end))


def _pad_row(cells, padding):
    if cells:
        pad = " "*padding
        padded_cells = [pad + cell + pad for cell in cells]
        return padded_cells
    else:
        return cells


def _format_table(fmt, headers, rows, colwidths, colaligns):
    """Produce a plain-text representation of the table."""
    lines = []
    hidden = fmt.with_header_hide if (headers and fmt.with_header_hide) else []
    pad = fmt.padding
    headerrow = fmt.headerrow

    padded_widths = [(w + 2*pad) for w in colwidths]
    padded_headers = _pad_row(headers, pad)
    padded_rows = [_pad_row(row, pad) for row in rows]

    if fmt.lineabove and "lineabove" not in hidden:
        lines.append(_build_line(padded_widths, colaligns, fmt.lineabove))

    if padded_headers:
        lines.append(_build_row(padded_headers, padded_widths, colaligns, headerrow))
        if fmt.linebelowheader and "linebelowheader" not in hidden:
            lines.append(_build_line(padded_widths, colaligns, fmt.linebelowheader))

    if padded_rows and fmt.linebetweenrows and "linebetweenrows" not in hidden:
        # initial rows with a line below
        for row in padded_rows[:-1]:
            lines.append(_build_row(row, padded_widths, colaligns, fmt.datarow))
            lines.append(_build_line(padded_widths, colaligns, fmt.linebetweenrows))
        # the last row without a line below
        lines.append(_build_row(padded_rows[-1], padded_widths, colaligns, fmt.datarow))
    else:
        for row in padded_rows:
            lines.append(_build_row(row, padded_widths, colaligns, fmt.datarow))

    if fmt.linebelow and "linebelow" not in hidden:
        lines.append(_build_line(padded_widths, colaligns, fmt.linebelow))

    return "\n".join(lines)



if __name__ == '__main__':
    def main():
        data_dicts = [{'id': 1, 'name': 'John Doe'},
                      {'id': 2, 'name': 'Dale Simmons'}]
        data_lists = [['id', 'name'],
                      [1, 'John Doe'],
                      [2, 'Dale Simmons']]
        t1 = Table(data_lists)
        t2 = Table.from_dict(data_dicts[0])
        t3 = Table.from_dict(data_dicts)
        t3.extend([[3, 'Kurt Rose'], [4]])
        print(t1)
        print(t2)
        print(t2.to_html())
        print(t3)
        print(t3.to_html())
        print(t3.to_text())

        import re
        t4 = Table.from_object(re.compile(''))
        print(t4.to_text())
        import pdb;pdb.set_trace()

    main()
