# -*- coding: utf-8 -*-

from __future__ import absolute_import

from httoop.codecs.codec import Codec
from httoop.exceptions import DecodeError, EncodeError

import zlib


class GZip(Codec):
	mimetype = 'application/gzip'

	@classmethod
	def encode(cls, data, charset=None, mimetype=None):
		try:
			return zlib.compress(Codec.encode(data, charset), 16 + zlib.MAX_WBITS)
		except zlib.error:
			raise EncodeError('Invalid gzip data')

	@classmethod
	def decode(cls, data, charset=None, mimetype=None):
		try:
			data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
		except zlib.error:
			raise DecodeError('Invalid gzip data')
		return Codec.decode(data, charset)
