# -*- coding: utf-8 -*-

from hashlib import md5

from httoop.exceptions import InvalidHeader
from httoop.header.element import HeaderElement


class DigestAuthScheme(object):

	algorithms = {
		'MD5': lambda val: md5(val).hexdigest(),
		'MD5-sess': lambda val: md5(val).hexdigest(),
	}
	qops = ('auth', 'auth-int')  # quality of protection

	@classmethod
	def get_algorithm(cls, algorithm):
		try:
			return cls.algorithms[algorithm]
		except KeyError:
			raise InvalidHeader(u'Unknown digest authentication algorithm: %r' % (algorithm,))

	@classmethod
	def compose(cls, authinfo):
		params = cls._compose(authinfo)
		return b', '.join([HeaderElement.formatparam(k, v) for k, v in params])

	@classmethod
	def _compose(cls, authinfo):
		return authinfo


class DigestAuthResponseScheme(DigestAuthScheme):

	@classmethod
	def _compose(cls, authinfo):
		realm = authinfo['realm']
		algorithm = authinfo.get('algorithm', 'MD5')
		domain = authinfo.get('domain')
		if isinstance(domain, (list, tuple)):
			domain = ' '.join(domain)
		nonce = authinfo['nonce'].replace('"', '')

		opaque = authinfo.get('opaque')
		stale = authinfo.get('stale')
		if isinstance(stale, bool):
			stale = 'true' if stale else 'false'

		qop_options = authinfo.get('qop', tuple(cls.qops))
		if isinstance(qop_options, (list, tuple)):
			qop_options = ','.join(qop_options)
		auth_param = authinfo.get('auth-param', [None, None])
		params = [
			('realm', realm),
			('domain', domain),
			('nonce', nonce),
			('opaque', opaque),
			('stale', stale),
			('algorithm', algorithm),
			('qop', qop_options),
			auth_param
		]
		return [(k, v) for k, v in params if v is not None]


class DigestAuthRequestScheme(DigestAuthScheme):

	@classmethod
	def _compose(cls, authinfo):
		username = authinfo['username']
		realm = authinfo['realm']
		nonce = authinfo.get('nonce', '').replace('"', '')
		if not nonce:
			nonce = cls.generate_nonce(authinfo)
		digest_uri = authinfo['uri']
		response = authinfo.get('response')
		if response is None:
			response = cls.calculate_request_digest(authinfo)

		algorithm = authinfo.get('algorithm')
		opaque = authinfo.get('opaque')
		message_qop = authinfo.get('qop')
		auth_param = authinfo.get('auth-param', [None, None])

		cnonce = None
		nonce_count = None
		if message_qop:
			cnonce = authinfo['cnonce']
			nonce_count = authinfo['nc']
		params = [
			('username', username),
			('realm', realm),
			('nonce', nonce),
			('uri', digest_uri),
			('response', response),
			('algorithm', algorithm),
			('cnonce', cnonce),
			('opaque', opaque),
			('qop', message_qop),
			('nc', nonce_count),
			auth_param
		]
		return [(k, v) for k, v in params if v is not None]

	@classmethod
	def generate_nonce(cls, authinfo):
		from time import time
		from uuid import uuid4
		nonce = '%d:%s:%s' % (time(), authinfo.get('etag', authinfo.get('realm')), uuid4(), )
		algorithm = authinfo.get('algorithm', 'MD5')
		H = cls.get_algorithm(algorithm)
		return H(nonce)

	@classmethod
	def check(cls, authinfo, request_params):
		if authinfo['realm'] != request_params['realm']:
			return False
		response = cls.calculate_request_digest(authinfo)
		return response == request_params['response']

	@classmethod
	def calculate_request_digest(cls, authinfo, A1=None):
		algorithm = authinfo.get('algorithm', 'MD5')
		H = cls.get_algorithm(algorithm)

		if algorithm == 'MD5-sess' and authinfo.get('A1'):
			secret = H(authinfo['A1'])
		else:
			secret = H(cls.A1(authinfo))

		qop = authinfo.get('qop')
		hash_a2 = H(cls.A2(authinfo))
		if qop in ('auth', 'auth-int'):
			data = b'%s:%s:%s:%s:%s' % (authinfo['nonce'], authinfo['nc'], authinfo['cnonce'], authinfo['qop'], hash_a2)
		elif qop is None:
			data = b'%s:%s' % (authinfo['nonce'], hash_a2)
		else:
			raise NotImplementedError('Unknown quality of protection: %r' % (qop,))

		return H(b'%s:%s' % (secret, data))

	@classmethod
	def A2(cls, params):
		qop = params.get('qop', '')
		if not qop or qop == 'auth':
			return b'%s:%s' % (params['method'], params['uri'])
		elif qop == 'auth-int':
			H = cls.get_algorithm(params['algorithm'])
			return b'%s:%s:%s' % (params['method'], params['uri'], H(params['entity_body']))
		else:
			raise NotImplementedError('Unknown quality of protection: %r' % (qop,))

	@classmethod
	def A1(cls, params):
		algorithm = params.get('algorithm', '')

		if not algorithm or algorithm == 'MD5':
			return b'%s:%s:%s' % (params['username'], params['realm'], params['password'])
		elif algorithm == 'MD5-sess':
			H = cls.get_algorithm(algorithm)
			s = b'%s:%s:%s' % (params['username'], params['realm'], params['password'])
			return b'%s:%s:%s' % (H(s), params['nonce'], params['cnonce'])
		else:
			raise NotImplementedError('Unknown algorithm: %s' % (algorithm,))
