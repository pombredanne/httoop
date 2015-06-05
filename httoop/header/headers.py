# -*- coding: utf-8 -*-
import re

from httoop.util import CaseInsensitiveDict, iteritems
from httoop.meta import HTTPSemantic
from httoop.header.element import HEADER, HeaderElement
from httoop.exceptions import InvalidHeader


class Headers(CaseInsensitiveDict):

	__metaclass__ = HTTPSemantic

	# disallowed bytes for HTTP header field names
	HEADER_RE = re.compile(b"[\x00-\x1F\x7F()<>@,;:\\\\\"/\[\]?={} \t\x80-\xFF]")

	def elements(self, fieldname):
		u"""Return a sorted list of HeaderElements from
			the given comma-separated header string."""

		fieldvalue = self.get(fieldname)
		if not fieldvalue:
			return []

		Element = HEADER.get(fieldname, HeaderElement)

		result = []
		for element in Element.split(fieldvalue):
			result.append(Element.parse(element))

		return list(reversed(sorted(result)))
		# TODO: remove the reversed() (fix in AcceptElement)

	def element(self, fieldname, default=None):
		u"""Treat the field as single element"""
		if fieldname in self:
			Element = HEADER.get(fieldname, HeaderElement)
			return Element.parse(self[fieldname])
		return default

	def values(self, key=None):
		# if key is set return a ordered list of element values
		# TODO: may move this into another method because values is a dict name
		if key is None:
			return super(Headers, self).values()
		return [e.value for e in self.elements(key)]

	def append(self, _name, _value, **params):
		if params:
			Element = HEADER.get(_name, HeaderElement)
			parts = [_value or b'']
			for k, v in iteritems(params):
				k = k.replace('_', '-')  # TODO: find out why this is done
				if v is None:
					parts.append(k)
				else:
					parts.append(Element.formatparam(k, v))
			_value = "; ".join(parts)

		if _name not in self or not self[_name]:
			self[_name] = _value
		else:
			Element = HEADER.get(_name, HeaderElement)
			self[_name] = Element.join([self[_name], _value])

	def validate(self):
		u"""validates all header elements

			:raises: InvalidHeader
		"""
		for name in self:
			self.elements(name)

	def merge(self, other):
		raise NotImplementedError

	def set(self, headers):
		for key in self.keys():
			del self[key]
		self.update(headers)

	def parse(self, data):
		r"""parses HTTP headers

			:param data:
				the header string containing headers separated by "\r\n"
				without trailing "\r\n"
			:type  data: bytes
		"""

		lines = data.split(b'\r\n')

		# parse headers into key/value pairs paying attention
		# to continuation lines.
		while lines:
			# Parse initial header name : value pair.
			curr = lines.pop(0)
			if b':' not in curr:
				raise InvalidHeader(u"Invalid header line: %r" % curr.decode('ISO8859-1'))

			name, value = curr.split(":", 1)
			name = name.rstrip(" \t")

			if self.HEADER_RE.search(name):
				raise InvalidHeader(u"Invalid header name: %s" % name.decode('ISO8859-1'))

			name, value = name.strip(), [value.lstrip()]

			# Consume value continuation lines
			while lines and lines[0].startswith((" ", "\t")):
				value.append(lines.pop(0)[1:])
			value = b''.join(value).rstrip()

			# TODO: parse encoded fields (MIME syntax)

			# store new header value
			self.append(name, value)

	def compose(self):
		# TODO: if value contains UTF-8 chars encode them in MIME
		return b'%s\r\n' % b''.join(b'%s: %s\r\n' % (k, v.encode('ISO8859-1', 'replace')) for k, v in iteritems(self))

	def __repr__(self):
		return "<HTTP Headers(%s)>" % repr(list(self.items()))
