# -*- coding: utf-8 -*-
"""HTTP request and response messages

.. seealso:: :rfc:`2616#section-4`
"""

__all__ = ('Request',)

from httoop.messages.method import Method
from httoop.messages.message import Message
from httoop.uri import HTTP as URI
from httoop.exceptions import InvalidLine, InvalidURI


class Request(Message):
	u"""A HTTP request message

		.. seealso:: :rfc:`2616#section-5`
	"""
	__slots__ = ('__protocol', '__headers', '__body', '__uri', '__method')

	@property
	def method(self):
		return self.__method

	@method.setter
	def method(self, method):
		self.__method.set(method)

	@property
	def uri(self):
		return self.__uri

	@uri.setter
	def uri(self, uri):
		self.__uri.set(uri)

	def __init__(self, method=None, uri=None, headers=None, body=None, protocol=None):  # pylint: disable=R0913
		"""Creates a new Request object to hold information about a request.

			:param method: the requested method
			:type  method: str

			:param uri: the requested URI
			:type  uri: str or :class:`URI`

		"""

		super(Request, self).__init__(protocol, headers, body)
		self.__method = Method(method or 'GET')
		self.__uri = URI(uri or '/')

	def parse(self, line):
		"""parses the request line and sets method, uri and protocol version
			:param line: the request line
			:type  line: bytes
		"""
		bits = line.strip().split(None, 2)
		try:
			method, uri, version = bits
		except ValueError:
			raise InvalidLine(line.decode('ISO8859-1'))

		# protocol version
		super(Request, self).parse(version)

		# method
		self.method.parse(method)

		# URI
		if uri.startswith(b'//'):
			raise InvalidURI(u'Invalid URI: must be an absolute path or contain a scheme')
		if uri.startswith(b'/'):
			self.uri.parse_relative(uri)
		elif uri == b'*':
			self.uri.path = uri
		else:
			self.uri.parse(uri)
		if not isinstance(self.uri, (self.uri.SCHEMES['http'], self.uri.SCHEMES['https'])):
			raise InvalidURI()
		self.uri.validate()

	def compose(self):
		u"""composes the request line"""
		return b"%s %s %s\r\n" % (bytes(self.__method), bytes(self.__uri), bytes(self.protocol))

	def __repr__(self):
		return "<HTTP Request(%s %s %s)>" % (bytes(self.__method), bytes(self.__uri.path), bytes(self.protocol))
