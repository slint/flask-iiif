# -*- coding: utf-8 -*-
#
# This file is part of Flask-IIIF
# Copyright (C) 2015, 2016 CERN.
#
# Flask-IIIF is free software; you can redistribute it and/or modify
# it under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Flask-IIIF decorators."""

from functools import wraps

from flask import current_app, make_response, request

from flask_restful import abort

from werkzeug import LocalProxy

from .errors import (
    IIIFValidatorError, MultimediaError, MultimediaImageCropError,
    MultimediaImageFormatError, MultimediaImageNotFound,
    MultimediaImageQualityError, MultimediaImageResizeError,
    MultimediaImageRotateError
)

__all__ = ('api_decorator', 'error_handler', )

current_iiif = LocalProxy(lambda: current_app.extensions['iiif'])


def error_handler(f):
    """Error handler."""
    @wraps(f)
    def inner(*args, **kwargs):
        """Wrap the errors."""
        try:
            return f(*args, **kwargs)
        except (MultimediaImageCropError, MultimediaImageResizeError,
                MultimediaImageFormatError, MultimediaImageRotateError,
                MultimediaImageQualityError) as error:
            abort(500, message=error.message, code=500)
        except IIIFValidatorError as error:
            abort(400, message=error.message, code=400)
        except (MultimediaError, MultimediaImageNotFound) as error:
            abort(error.code, message=error.message, code=error.code)
    return inner


def api_decorator(f):
    """API decorator."""
    @wraps(f)
    def inner(*args, **kwargs):
        if current_iiif.api_decorator_callback:
            current_iiif.api_decorator_callback(*args, **kwargs)
        return f(*args, **kwargs)
    return inner


def http_cache_decorator(f):
    """HTTP cache decorator.

    This decorator utilizes two functions in order to decorate a response
    with the necessary HTTP headers to conform to browser caching mechanisms.

    It uses `last_modified_callback` in oder to provide a date for the
    Last-Modified header and the `etag_callback` to provide an checksum value
    for the ETag header.
    """
    @wraps(f)
    def inner(*args, **kwargs):
        etag = None
        if current_iiif.etag_callback:
            etag = current_iiif.etag_callback(*args, **kwargs)

        last_mod = None
        if current_iiif.last_modified_callback:
            last_mod = current_iiif.last_modified_callback(*args, **kwargs)

        if etag or last_mod:
            from werkzeug.http import is_resource_modified
            modified = is_resource_modified(request.environ, etag=etag,
                                            last_modified=last_mod)
            if not modified:
                return '', 304

            res = make_response(f(*args, **kwargs))
            if etag:
                res.set_etag(etag)
            if last_mod:
                res.last_modified = last_mod
            return res
        return f(*args, **kwargs)
    return inner
