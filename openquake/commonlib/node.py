# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2014-2016 GEM Foundation
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake. If not, see <http://www.gnu.org/licenses/>.

"""
This module defines a Node class, together with a few conversion
functions which are able to convert NRML files into hierarchical
objects (DOM). That makes it easier to read and write XML from Python
and viceversa. Such features are used in the command-line conversion
tools. The Node class is kept intentionally similar to an
Element class, however it overcomes the limitation of ElementTree: in
particular a node can manage a lazy iterable of subnodes, whereas
ElementTree wants to keep everything in memory. Moreover the Node
class provides a convenient dot notation to access subnodes.

The Node class is instantiated with four arguments:

1. the node tag (a mandatory string)
2. the node attributes (a dictionary)
3. the node value (a string or None)
4. the subnodes (an iterable over nodes)

If a node has subnodes, its value should be None.

For instance, here is an example of instantiating a root node
with two subnodes a and b:

>>> from openquake.commonlib.node import Node
>>> a = Node('a', {}, 'A1')
>>> b = Node('b', {'attrb': 'B'}, 'B1')
>>> root = Node('root', nodes=[a, b])
>>> root
<root {} None ...>

Node objects can be converted into nicely indented strings:

>>> print(root.to_str())
root
  a 'A1'
  b{attrb='B'} 'B1'
<BLANKLINE>

The subnodes can be retrieved with the dot notation:

>>> root.a
<a {} A1 >

The value of a node can be extracted with the `~` operator:

>>> ~root.a
'A1'

If there are multiple subnodes with the same name

>>> root.append(Node('a', {}, 'A2'))  # add another 'a' node

the dot notation will retrieve the first node.

It is possible to retrieve the other nodes from the ordinal
index:

>>> root[0], root[1], root[2]
(<a {} A1 >, <b {'attrb': 'B'} B1 >, <a {} A2 >)

The list of all subnodes with a given name can be retrieved
as follows:

>>> list(root.getnodes('a'))
[<a {} A1 >, <a {} A2 >]

It is also possible to delete a node given its index:

>>> del root[2]

A node is an iterable object yielding its subnodes:

>>> list(root)
[<a {} A1 >, <b {'attrb': 'B'} B1 >]

The attributes of a node can be retrieved with the square bracket notation:

>>> root.b['attrb']
'B'

It is possible to add and remove attributes freely:

>>> root.b['attr'] = 'new attr'
>>> del root.b['attr']

Node objects can be easily converted into ElementTree objects:

>>> node_to_elem(root)  #doctest: +ELLIPSIS
<Element 'root' at ...>

Then is trivial to generate the XML representation of a node:

>>> from xml.etree import ElementTree
>>> print(ElementTree.tostring(node_to_elem(root)))
<root><a>A1</a><b attrb="B">B1</b></root>

Generating XML files larger than the available memory requires some
care. The trick is to use a node generator, such that it is not
necessary to keep the entire tree in memory. Here is an example:

>>> def gen_many_nodes(N):
...     for i in xrange(N):
...         yield Node('a', {}, 'Text for node %d' % i)

>>> lazytree = Node('lazytree', {}, nodes=gen_many_nodes(10))

The lazytree object defined here consumes no memory, because the
nodes are not created a instantiation time. They are created as
soon as you start iterating on the lazytree. In particular
list(lazytree) will generated all of them. If your goal is to
store the tree on the filesystem in XML format you should use
a writing routine converting a subnode at the time, without
requiring the full list of them. The routines provided by
ElementTree are no good, however commonlib.writers
provide an StreamingXMLWriter just for that purpose.

Lazy trees should *not* be used unless it is absolutely necessary in
order to save memory; the problem is that if you use a lazy tree the
slice notation will not work (the underlying generator will not accept
it); moreover it will not be possible to iterate twice on the
subnodes, since the generator will be exhausted. Notice that even
accessing a subnode with the dot notation will avance the
generator. Finally, nodes containing lazy nodes will not be pickleable.
"""
from openquake.baselib.python3compat import configparser, with_metaclass

import io
import sys
import copy
import pprint as pp
from contextlib import contextmanager
from openquake.baselib.python3compat import raise_, exec_
from openquake.commonlib.writers import StreamingXMLWriter
from xml.etree import ElementTree


class SourceLineParser(ElementTree.XMLParser):
    """
    A custom parser managing line numbers
    """
    def _start_list(self, tag, attrib_in):
        elem = super(SourceLineParser, self)._start_list(tag, attrib_in)
        elem.lineno = self.parser.CurrentLineNumber
        # there is also CurrentColumnNumber available, if wanted
        return elem


def fromstring(text):
    """Parse an XML string and return a tree"""
    return ElementTree.fromstring(text, SourceLineParser())


def parse(source, remove_comments=True, **kw):
    """Thin wrapper around ElementTree.parse"""
    return ElementTree.parse(source, SourceLineParser(), **kw)


def iterparse(source, events=('end',), remove_comments=True, **kw):
    """Thin wrapper around ElementTree.iterparse"""
    return ElementTree.iterparse(source, events, SourceLineParser(), **kw)


# ###################### utilities for the Node class ####################### #


def _displayattrs(attrib, expandattrs):
    """
    Helper function to display the attributes of a Node object in lexicographic
    order.

    :param attrib: dictionary with the attributes
    :param expandattrs: if True also displays the value of the attributes
    """
    if not attrib:
        return ''
    if expandattrs:
        alist = ['%s=%r' % item for item in sorted(attrib.items())]
    else:
        alist = list(attrib)
    return '{%s}' % ', '.join(alist)


def _display(node, indent, expandattrs, expandvals, output):
    """Core function to display a Node object"""
    attrs = _displayattrs(node.attrib, expandattrs)
    val = ' %s' % repr(node.text) \
        if expandvals and node.text is not None else ''
    output.write(
        (indent + striptag(node.tag) + attrs + val + '\n').decode('utf8'))
    for sub_node in node:
        _display(sub_node, indent + '  ', expandattrs, expandvals, output)


def node_display(root, expandattrs=False, expandvals=False, output=sys.stdout):
    """
    Write an indented representation of the Node object on the output;
    this is intended for testing/debugging purposes.

    :param root: a Node object
    :param bool expandattrs: if True, the values of the attributes are
                             also printed, not only the names
    :param bool expandvals: if True, the values of the tags are also printed,
                            not only the names.
    :param output: stream where to write the string representation of the node
    """
    _display(root, '', expandattrs, expandvals, output)


def striptag(tag):
    """
    Get the short representation of a fully qualified tag

    :param str tag: a (fully qualified or not) XML tag
    """
    if tag.startswith('{'):
        return tag.rsplit('}')[1]
    return tag


class Node(object):
    """
    A class to make it easy to edit hierarchical structures with attributes,
    such as XML files. Node objects must be pickleable and must consume as
    little memory as possible. Moreover they must be easily converted from
    and to ElementTree objects. The advantage over ElementTree objects
    is that subnodes can be lazily generated and that they can be accessed
    with the dot notation.
    """
    __slots__ = ('tag', 'attrib', 'text', 'nodes', 'lineno')

    def __init__(self, fulltag, attrib=None, text=None,
                 nodes=None, lineno=None):
        """
        :param str tag: the Node name
        :param dict attrib: the Node attributes
        :param unicode text: the Node text (default None)
        :param nodes: an iterable of subnodes (default empty list)
        """
        self.tag = fulltag
        self.attrib = {} if attrib is None else attrib
        self.text = text
        self.nodes = [] if nodes is None else nodes
        self.lineno = lineno
        if self.nodes and self.text is not None:
            raise ValueError(
                'A branch node cannot have a value, got %r' % self.text)

    def __getattr__(self, name):
        if name.startswith('_'):
            # do the magic only for public names
            raise AttributeError(name)
        for node in self.nodes:
            if striptag(node.tag) == name:
                return node
        raise NameError('No subnode named %r found in %r' %
                        (name, striptag(self.tag)))

    def getnodes(self, name):
        "Return the direct subnodes with name 'name'"
        for node in self.nodes:
            if striptag(node.tag) == name:
                yield node

    def append(self, node):
        "Append a new subnode"
        if not isinstance(node, self.__class__):
            raise TypeError('Expected Node instance, got %r' % node)
        self.nodes.append(node)

    def to_str(self, expandattrs=True, expandvals=True):
        """
        Convert the node into a string, intended for testing/debugging purposes

        :param expandattrs:
          print the values of the attributes if True, else print only the names
        :param expandvals:
          print the values if True, else print only the tag names
        """
        out = io.StringIO()
        node_display(self, expandattrs, expandvals, out)
        return out.getvalue()

    def __iter__(self):
        """Iterate over subnodes"""
        return iter(self.nodes)

    def __repr__(self):
        """A condensed representation for debugging purposes"""
        return '<%s %s %s %s>' % (striptag(self.tag), self.attrib, self.text,
                                  '' if not self.nodes else '...')

    def __getitem__(self, i):
        """
        Retrieve a subnode, if i is an integer, or an attribute, if i
        is a string.
        """
        if isinstance(i, str):
            return self.attrib[i]
        else:  # assume an integer or a slice
            return self.nodes[i]

    def __setitem__(self, i, value):
        """
        Update a subnode, if i is an integer, or an attribute, if i
        is a string.
        """
        if isinstance(i, str):
            self.attrib[i] = value
        else:  # assume an integer or a slice
            self.nodes[i] = value

    def __delitem__(self, i):
        """
        Remove a subnode, if i is an integer, or an attribute, if i
        is a string.
        """
        if isinstance(i, str):
            del self.attrib[i]
        else:  # assume an integer or a slice
            del self.nodes[i]

    def __invert__(self):
        """
        Return the value of a leaf; raise a TypeError if the node is not a leaf
        """
        if self:
            raise TypeError('%s is a composite node, not a leaf' % self)
        return self.text

    def __len__(self):
        """Return the number of subnodes"""
        return len(self.nodes)

    def __nonzero__(self):
        """
        Return True if there are subnodes; it does not iter on the
        subnodes, so for lazy nodes it returns True even if the
        generator is empty.
        """
        return bool(self.nodes)

    if sys.version > '3':
        __bool__ = __nonzero__

    def __deepcopy__(self, memo):
        new = object.__new__(self.__class__)
        new.tag = self.tag
        new.attrib = self.attrib.copy()
        new.text = copy.copy(self.text)
        new.nodes = [copy.deepcopy(n, memo) for n in self.nodes]
        new.lineno = self.lineno
        return new

    def __getstate__(self):
        return dict((slot, getattr(self, slot))
                    for slot in self.__class__.__slots__)

    def __setstate__(self, state):
        for slot in self.__class__.__slots__:
            setattr(self, slot, state[slot])

    def __eq__(self, other):
        return all(getattr(self, slot) == getattr(other, slot)
                   for slot in self.__class__.__slots__)

    def __ne__(self, other):
        return not self.__eq__(other)


class MetaLiteralNode(type):
    """
    Metaclass adding __slots__ and extending the docstring with a note
    about the known validators. Moreover it checks for the attribute
    `.validators`.
    """
    def __new__(meta, name, bases, dic):
        doc = "Known validators:\n%s" % '\n'.join(
            '    %s: `%s`' % (n, v.__name__)
            for n, v in dic['validators'].items())
        dic['__doc__'] = dic.get('__doc__', '') + doc
        dic['__slots__'] = dic.get('__slots__', [])
        return super(MetaLiteralNode, meta).__new__(meta, name, bases, dic)


class LiteralNode(with_metaclass(MetaLiteralNode, Node)):
    """
    Subclasses should define a non-empty dictionary of validators.
    """
    validators = {}  # to be overridden in subclasses

    def __init__(self, fulltag, attrib=None, text=None,
                 nodes=None, lineno=None):
        validators = self.__class__.validators
        tag = striptag(fulltag)
        if tag in validators:
            # try to cast the node, if the tag is known
            assert not nodes, 'You cannot cast a composite node: %s' % nodes
            try:
                text = validators[tag](text, **attrib)
                assert text is not None
            except Exception as exc:
                raise ValueError('Could not convert %s->%s: %s, line %s' %
                                 (tag, validators[tag].__name__, exc, lineno))
        elif attrib:
            # cast the attributes
            for n, v in attrib.items():
                if n in validators:
                    try:
                        attrib[n] = validators[n](v)
                    except Exception as exc:
                        raise ValueError(
                            'Could not convert %s->%s: %s, line %s' %
                            (n, validators[n].__name__, exc, lineno))
        super(LiteralNode, self).__init__(fulltag, attrib, text, nodes, lineno)


def to_literal(self):
    """
    Convert the node into a literal Python object
    """
    if not self.nodes:
        return (self.tag, self.attrib, self.text, [])
    else:
        return (self.tag, self.attrib, self.text,
                list(map(to_literal, self.nodes)))


def pprint(self, stream=None, indent=1, width=80, depth=None):
    """
    Pretty print the underlying literal Python object
    """
    pp.pprint(to_literal(self), stream, indent, width, depth)


def node_from_dict(dic, nodefactory=Node):
    """
    Convert a (nested) dictionary with attributes tag, attrib, text, nodes
    into a Node object.
    """
    tag = dic['tag']
    text = dic.get('text')
    attrib = dic.get('attrib', {})
    nodes = dic.get('nodes', [])
    if not nodes:
        return nodefactory(tag, attrib, text)
    return nodefactory(tag, attrib, nodes=list(map(node_from_dict, nodes)))


def node_to_dict(node):
    """
    Convert a Node object into a (nested) dictionary
    with attributes tag, attrib, text, nodes.

    :param node: a Node-compatible object
    """
    dic = dict(tag=node.tag, attrib=node.attrib, text=node.text)
    if node.nodes:
        dic['nodes'] = [node_to_dict(n) for n in node]
    return dic


def node_from_elem(elem, nodefactory=Node, lazy=()):
    """
    Convert (recursively) an ElementTree object into a Node object.
    """
    children = list(elem)
    lineno = getattr(elem, 'lineno', None)
    if not children:
        return nodefactory(elem.tag, dict(elem.attrib), elem.text,
                           lineno=lineno)
    if striptag(elem.tag) in lazy:
        nodes = (node_from_elem(ch, nodefactory, lazy) for ch in children)
    else:
        nodes = [node_from_elem(ch, nodefactory, lazy) for ch in children]
    return nodefactory(elem.tag, dict(elem.attrib), nodes=nodes, lineno=lineno)


# taken from https://gist.github.com/651801, which comes for the effbot
def node_to_elem(root):
    """
    Convert (recursively) a Node object into an ElementTree object.
    """
    def generate_elem(append, node, level):
        var = "e" + str(level)
        arg = repr(node.tag)
        if node.attrib:
            arg += ", **%r" % node.attrib
        if level == 1:
            append("e1 = Element(%s)" % arg)
        else:
            append("%s = SubElement(e%d, %s)" % (var, level - 1, arg))
        if not node.nodes:
            append("%s.text = %r" % (var, node.text))
        for x in node:
            generate_elem(append, x, level + 1)
    # generate code to create a tree
    output = []
    generate_elem(output.append, root, 1)  # print "\n".join(output)
    namespace = {"Element": ElementTree.Element,
                 "SubElement": ElementTree.SubElement}
    exec_("\n".join(output), globals(), namespace)
    return namespace["e1"]


def read_nodes(fname, filter_elem, nodefactory=Node, remove_comments=True):
    """
    Convert an XML file into a lazy iterator over Node objects
    satifying the given specification, i.e. a function element -> boolean.

    :param fname: file name of file object
    :param filter_elem: element specification

    In case of errors, add the file name to the error message.
    """
    try:
        for _, el in iterparse(fname, remove_comments=remove_comments):
            if filter_elem(el):
                yield node_from_elem(el, nodefactory)
                el.clear()  # save memory
    except:
        etype, exc, tb = sys.exc_info()
        msg = str(exc)
        if not str(fname) in msg:
            msg = '%s in %s' % (msg, fname)
        raise_(etype, msg, tb)


def node_from_xml(xmlfile, nodefactory=Node):
    """
    Convert a .xml file into a Node object.

    :param xmlfile: a file name or file object open for reading
    """
    root = parse(xmlfile).getroot()
    return node_from_elem(root, nodefactory)


def node_to_xml(node, output=sys.stdout, nsmap=None):
    """
    Convert a Node object into a pretty .xml file without keeping
    everything in memory. If you just want the string representation
    use commonlib.writers.tostring(node).

    :param node: a Node-compatible object (ElementTree nodes are fine)
    :param nsmap: if given, shorten the tags with aliases

    """
    if nsmap:
        for ns, prefix in nsmap.items():
            if prefix:
                node['xmlns:' + prefix[:-1]] = ns
            else:
                node['xmlns'] = ns
    with StreamingXMLWriter(output, nsmap=nsmap) as w:
        w.serialize(node)


def node_from_ini(ini_file, nodefactory=Node, root_name='ini'):
    """
    Convert a .ini file into a Node object.

    :param ini_file: a filename or a file like object in read mode
    """
    fileobj = open(ini_file) if isinstance(ini_file, str) else ini_file
    cfp = configparser.RawConfigParser()
    cfp.readfp(fileobj)
    root = nodefactory(root_name)
    sections = cfp.sections()
    for section in sections:
        params = dict(cfp.items(section))
        root.append(Node(section, params))
    return root


def node_to_ini(node, output=sys.stdout):
    """
    Convert a Node object with the right structure into a .ini file.

    :params node: a Node object
    :params output: a file-like object opened in write mode
    """
    for subnode in node:
        output.write(u'\n[%s]\n' % subnode.tag)
        for name, value in sorted(subnode.attrib.items()):
            output.write(u'%s=%s\n' % (name, value))
    output.flush()


def node_copy(node, nodefactory=Node):
    """Make a deep copy of the node"""
    return nodefactory(node.tag, node.attrib.copy(), node.text,
                       [node_copy(n, nodefactory) for n in node])


@contextmanager
def context(fname, node):
    """
    Context manager managing exceptions and adding line number of the
    current node and name of the current file to the error message.

    :param fname: the current file being processed
    :param node: the current node being processed
    """
    try:
        yield node
    except:
        etype, exc, tb = sys.exc_info()
        msg = 'node %s: %s, line %s of %s' % (
            striptag(node.tag), exc, node.lineno, fname)
        raise_(etype, msg, tb)
