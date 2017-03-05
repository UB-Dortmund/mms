# The MIT License
#
#  Copyright 2015-2017 University Library Bochum <bibliogaphie-ub@rub.de> and UB Dortmund <api.ub@tu-dortmund.de>.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

# Specification: http://www.openarchives.org/OAI/openarchivesprotocol.html

from __future__ import (absolute_import, division, print_function, unicode_literals)

import datetime
import dicttoxml
import pytz
import utcdatetime
from xml.dom.minidom import parseString, getDOMImplementation
import logging
import re
from logging.handlers import RotatingFileHandler

import requests
import simplejson as json
from flask import Flask, render_template, request, jsonify
from flask import make_response
from flask_cors import CORS
from flask_redis import Redis
from flask_swagger import swagger
from flask_wtf.csrf import CSRFProtect

from forms.forms import *
import persistence
from utils.solr_handler import Solr

try:
    import local_oai_pmh_secrets as secrets
except ImportError:
    import oai_pmh_secrets as secrets


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app = Flask(__name__)
CORS(app)

if secrets.DIFFERENT_PROXY_PATH:
    app.wsgi_app = ReverseProxied(app.wsgi_app)

app.debug = secrets.DEBUG
app.secret_key = secrets.DEBUG_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS '] = False

app.config['REDIS_OAI_PMH_RT_URL'] = secrets.REDIS_OAI_PMH_RT_URL
Redis(app, 'REDIS_OAI_PMH_RT')

csrf = CSRFProtect(app)

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
handler.setFormatter(log_formatter)
app.logger.addHandler(handler)

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
log.addHandler(handler)

# ---------- OAI-PMH Data Provider ----------


@app.route('/oai', methods=['GET'])
@csrf.exempt
def oai_get():
    """
        OAI-PMH Data Provider

        swagger_from_file: api_doc/oai_pmh_get.yml
    """
    verb = request.args.get('verb', '')

    if verb == 'Identify':
        if len(request.args) > 1:
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='text/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "text/xml"

            return response
        else:
            oai_identify_xml = render_template('oai_pmh/oai_identify.xml',
                                               data={'verb': verb,
                                                     'info': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)),
                                                     'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                     },
                                               now=timestamp(),
                                               mimetype='text/xml')

            response = make_response(oai_identify_xml)
            response.headers["Content-Type"] = "text/xml"

            return response
    elif verb == 'ListMetadataFormats':
        identifier = request.args.get('identifier', '')

        if identifier:
            try:
                uuid.UUID(identifier.replace(secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'), ''))
                result = persistence.get_work(identifier.replace(secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'), ''))
                if result:
                    oai_listmetadataformats_xml = render_template('oai_pmh/oai_listmetadataformats.xml',
                                                                  data={
                                                                      'verb': verb,
                                                                      'identifier': identifier,
                                                                      'formats': secrets.FORMATS,
                                                                      'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                                      'id_prefix': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'),
                                                                  },
                                                                  now=timestamp(),
                                                                  mimetype='text/xml')

                    response = make_response(oai_listmetadataformats_xml)
                    response.headers["Content-Type"] = "text/xml"

                    return response
                else:
                    oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                    data={'verb': verb,
                                                          'error_code': 'idDoesNotExist',
                                                          'error_text': 'The value of the identifier argument is unknown or illegal in this repository.',
                                                          'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                          },
                                                    now=timestamp(),
                                                    mimetype='text/xml')

                    response = make_response(oai_error_xml)
                    response.headers["Content-Type"] = "text/xml"

                    return response
            except:
                oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                data={'verb': verb,
                                                      'error_code': 'idDoesNotExist',
                                                      'error_text': 'The value of the identifier argument is unknown or illegal in this repository.',
                                                      'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                      },
                                                now=timestamp(),
                                                mimetype='text/xml')

                response = make_response(oai_error_xml)
                response.headers["Content-Type"] = "text/xml"

                return response

        else:
            oai_listmetadataformats_xml = render_template('oai_pmh/oai_listmetadataformats.xml',
                                                          data={
                                                              'verb': verb,
                                                              'formats': secrets.FORMATS,
                                                              'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                          },
                                                          now=timestamp(),
                                                          mimetype='text/xml')

            response = make_response(oai_listmetadataformats_xml)
            response.headers["Content-Type"] = "text/xml"

            return response
    elif verb == 'ListSets':
        if len(request.args) > 1:
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='application/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "application/xml"

            return response

        else:
            # TODO weitere Kollektionen? z.B. Orgas und Groups?
            oai_listsets_xml = render_template('oai_pmh/oai_listsets.xml',
                                               data={'verb': verb,
                                                     'info': secrets.SETS_INFO,
                                                     'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                     },
                                               now=timestamp(),
                                               mimetype='text/xml')

            response = make_response(oai_listsets_xml)
            response.headers["Content-Type"] = "application/xml"

            return response
    elif verb == 'ListIdentifiers':
        allowed_params = ('verb', 'from', 'until', 'metadataPrefix', 'set', 'resumptionToken')

        # Optional parameters
        oai_from = request.args.get('from', '')
        oai_until = request.args.get('until', '')
        oai_set = request.args.get('set', '')
        # Exclusive parameter
        resumption_token = request.args.get('resumptionToken', '')

        # Required parameter
        oai_metadata_prefix = request.args.get('metadataPrefix', '')

        # exists a not allowed parameter?
        try:
            if len(request.args) > 1:
                for param in request.args.keys():
                    if param not in allowed_params:
                        raise KeyError
        except KeyError:
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='text/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "text/xml"

            return response

        # is metadata_prefix valid?
        if oai_metadata_prefix not in secrets.VALID_METADATA_PREFIXES:
            if resumption_token != '':
                pass
            else:
                oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                data={'verb': verb,
                                                      'error_code': 'cannotDisseminateFormat',
                                                      'error_text': 'The metadata format identified by the value given for the metadataPrefix argument is not supported by the item or by the repository.',
                                                      'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                      },
                                                now=timestamp(),
                                                mimetype='text/xml')

                response = make_response(oai_error_xml)
                response.headers["Content-Type"] = "text/xml"

                return response

        # is resumption_token exclusive?
        if resumption_token and (oai_from or oai_until or oai_set):
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(
                                                      theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='text/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "text/xml"

            return response

        # build query
        cursor = 0
        if resumption_token:
            r = app.extensions['redis']['REDIS_OAI_PMH_RT']
            rt = r.hget('resumptionToken', resumption_token)
            cursor = rt.get('cursor')
            oai_from = rt.get('from')
            oai_until = rt.get('until')
            oai_set = rt.get('set')

            if oai_from and not oai_until:
                query = 'recordChangeDate:[%s+TO+*]' % (oai_from + 'T00:00:00Z')
            elif not oai_from and oai_until:
                query = 'recordChangeDate:[*+TO+%s]' % (oai_until + 'T00:00:00Z')
            elif oai_from and oai_until:
                query = 'recordChangeDate:[%s+TO+%s]' % (oai_from + 'T00:00:00Z', oai_until + 'T00:00:00Z')
            else:
                query = '*:*'

            filterquery = []
            if oai_set:
                theset = oai_set
                if oai_set.startswith('doc-type'):
                    filterquery.append('oai_type:"%s"' % theset.replace('doc-type:', ''))
                if oai_set.startswith('ddc'):
                    filterquery.append('ddc:"%s"' % theset.replace('ddc:', ''))
                if oai_set == 'ec_fundedresources':
                    filterquery.append('fp7:*')

            # resumptionToken expired?
            if datetime.datetime.now() > datetime.datetime.strptime(rt.get('expirationDate'), "%Y-%m-%dT%H:%M:%S.%fZ"):
                oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                data={'verb': verb,
                                                      'error_code': 'badResumptionToken',
                                                      'error_text': 'The value of the resumptionToken argument is invalid or expired.',
                                                      'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                      },
                                                now=timestamp(),
                                                mimetype='text/xml')

                response = make_response(oai_error_xml)
                response.headers["Content-Type"] = "text/xml"

                return response
        else:
            if oai_from and not oai_until:
                query = 'recordChangeDate:[%s+TO+*]' % (oai_from + 'T00:00:00Z')
            elif not oai_from and oai_until:
                query = 'recordChangeDate:[*+TO+%s]' % (oai_until + 'T00:00:00Z')
            elif oai_from and oai_until:
                query = 'recordChangeDate:[%s+TO+%s]' % (oai_from + 'T00:00:00Z', oai_until + 'T00:00:00Z')
            else:
                query = '*:*'

            filterquery = []
            if oai_set:
                theset = oai_set
                if oai_set.startswith('doc-type'):
                    filterquery.append('oai_type:"%s"' % theset.replace('doc-type:', ''))
                if oai_set.startswith('ddc'):
                    filterquery.append('ddc:"%s"' % theset.replace('ddc:', ''))
                if oai_set == 'ec_fundedresources':
                    filterquery.append('fp7:*')

        # Solr request
        search_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           start=cursor, rows=secrets.BATCH_SIZE,
                           query=query,
                           fquery=filterquery,
                           fields=['id', 'recordChangeDate', 'oai_type', 'ddc'],
                           sort='recordChangeDate asc')
        search_solr.request()
        result = search_solr.results

        hit_count = search_solr.count()

        rt_last = False
        if int(cursor) + secrets.BATCH_SIZE >= hit_count:
            rt_last = True

        rt_id = ''
        rt = {}
        if hit_count > secrets.BATCH_SIZE and cursor < hit_count:
            rt_id = uuid.uuid4()
            rt.setdefault('expirationDate', (datetime.datetime.now() + datetime.timedelta(2)).isoformat() + 'Z')
            rt.setdefault('cursor', (int(cursor) + secrets.BATCH_SIZE))
            if oai_from:
                rt.setdefault('from', oai_from)
            if oai_until:
                rt.setdefault('until', oai_until)
            if oai_set:
                rt.setdefault('set', oai_set)

            r = app.extensions['redis']['REDIS_OAI_PMH_RT']
            r.hset('resumptionToken', rt_id, rt)

        oai_listidentifiers_xml = render_template('oai_pmh/oai_listidentifiers.xml',
                                                  data={'verb': verb,
                                                        'docs': result,
                                                        'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                        'id_prefix': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'),
                                                        'resumption_token': rt_id,
                                                        'expiration_date': rt.get('expirationDate'),
                                                        'cursor': rt.get('cursor'),
                                                        'complete_list_size': hit_count,
                                                        'last_batch': rt_last,
                                                        'metadata_prefix': oai_metadata_prefix,
                                                        'from': oai_from,
                                                        'until': oai_until,
                                                        'set': oai_set,
                                                        },
                                                  now=timestamp(),
                                                  mimetype='text/xml')

        response = make_response(oai_listidentifiers_xml)
        response.headers["Content-Type"] = "text/xml"

        return response

    else:
        oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                        data={'verb': verb,
                                              'error_code': 'badVerb',
                                              'error_text': 'Value of the verb argument is not a legal OAI-PMH verb, the verb argument is missing, or the verb argument is repeated.',
                                              'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                              },
                                        now=timestamp(),
                                        mimetype='text/xml')

        response = make_response(oai_error_xml)
        response.headers["Content-Type"] = "text/xml"

        return response


@app.route('/oai', methods=['POST'])
@csrf.exempt
def oai_post():
    """
        OAI-PMH Data Provider

        swagger_from_file: api_doc/oai_pmh_post.yml
    """
    if request.headers.get('Content-Type') and request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
        verb = request.form['verb']
    else:
        response = make_response(400, 'Not well formed Header! Content-Type must be application/x-www-form-urlencoded')
        response.headers["Content-Type"] = "text/xml"

        return response

    if verb == 'Identify':
        if request.headers.get('Content-Type') and request.headers.get(
                'Content-Type') == 'application/x-www-form-urlencoded' and len(request.form) > 1:

            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get(
                                                      'baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='text/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "text/xml"

            return response
        else:
            oai_identify_xml = render_template('oai_pmh/oai_identify.xml',
                                               data={'verb': verb,
                                                     'info': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)),
                                                     'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                     },
                                               now=timestamp(),
                                               mimetype='text/xml')

            response = make_response(oai_identify_xml)
            response.headers["Content-Type"] = "text/xml"

            return response
    if verb == 'ListMetadataFormats':
        if len(request.form) > 1:
            identifier = request.form['identifier']

            if identifier:
                try:
                    uuid.UUID(identifier.replace(secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'), ''))
                    result = persistence.get_work(identifier.replace(secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'), ''))
                    if result:
                        oai_listmetadataformats_xml = render_template('oai_pmh/oai_listmetadataformats.xml',
                                                                      data={
                                                                          'verb': verb,
                                                                          'identifier': identifier,
                                                                          'formats': secrets.FORMATS,
                                                                          'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                                          'id_prefix': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'),
                                                                      },
                                                                      now=timestamp(),
                                                                      mimetype='text/xml')

                        response = make_response(oai_listmetadataformats_xml)
                        response.headers["Content-Type"] = "text/xml"

                        return response
                    else:
                        oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                        data={'verb': verb,
                                                              'error_code': 'idDoesNotExist',
                                                              'error_text': 'The value of the identifier argument is unknown or illegal in this repository.',
                                                              'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                              },
                                                        now=timestamp(),
                                                        mimetype='text/xml')

                        response = make_response(oai_error_xml)
                        response.headers["Content-Type"] = "text/xml"

                        return response
                except:
                    oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                    data={'verb': verb,
                                                          'error_code': 'idDoesNotExist',
                                                          'error_text': 'The value of the identifier argument is unknown or illegal in this repository.',
                                                          'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                          },
                                                    now=timestamp(),
                                                    mimetype='text/xml')

                    response = make_response(oai_error_xml)
                    response.headers["Content-Type"] = "text/xml"

                    return response
        else:
            oai_listmetadataformats_xml = render_template('oai_pmh/oai_listmetadataformats.xml',
                                                          data={
                                                              'verb': verb,
                                                              'formats': secrets.FORMATS,
                                                              'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                          },
                                                          now=timestamp(),
                                                          mimetype='text/xml')

            response = make_response(oai_listmetadataformats_xml)
            response.headers["Content-Type"] = "text/xml"

            return response
    elif verb == 'ListSets':
        if len(request.form) > 1:
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='application/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "application/xml"

            return response

        else:
            # TODO weitere Kollektionen? z.B. Orgas und Groups?
            oai_listsets_xml = render_template('oai_pmh/oai_listsets.xml',
                                               data={'verb': verb,
                                                     'info': secrets.SETS_INFO,
                                                     'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                     },
                                               now=timestamp(),
                                               mimetype='text/xml')

            response = make_response(oai_listsets_xml)
            response.headers["Content-Type"] = "application/xml"

            return response
    elif verb == 'ListIdentifiers':
        allowed_params = ('verb', 'from', 'until', 'metadataPrefix', 'set', 'resumptionToken')

        # Required parameter
        oai_metadata_prefix = ''
        # Optional parameters
        oai_from = ''
        oai_until = ''
        oai_set = ''
        # Exclusive parameter
        resumption_token = ''

        try:
            if len(request.form) > 1:
                for param in request.form:
                    if param not in allowed_params:
                        raise KeyError
                    else:
                        if param == 'metadataPrefix':
                            oai_metadata_prefix = request.form[param]
                        if param == 'from':
                            oai_from = request.form[param]
                        if param == 'until':
                            oai_until = request.form[param]
                        if param == 'set':
                            oai_set = request.form[param]
                        if param == 'resumptionToken':
                            resumption_token = request.form[param]

        except KeyError:
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='text/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "text/xml"

            return response

        # is metadata_prefix valid?
        if oai_metadata_prefix not in secrets.VALID_METADATA_PREFIXES:
            if resumption_token != '':
                pass
            else:
                oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                data={'verb': verb,
                                                      'error_code': 'cannotDisseminateFormat',
                                                      'error_text': 'The metadata format identified by the value given for the metadataPrefix argument is not supported by the item or by the repository.',
                                                      'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                      },
                                                now=timestamp(),
                                                mimetype='text/xml')

                response = make_response(oai_error_xml)
                response.headers["Content-Type"] = "text/xml"

                return response

        # is resumption_token exclusive?
        if resumption_token and (oai_from or oai_until or oai_set):
            oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                            data={'verb': verb,
                                                  'error_code': 'badArgument',
                                                  'error_text': 'The request includes illegal arguments, is missing required arguments, includes a repeated argument, or values for arguments have an illegal syntax.',
                                                  'base_url': secrets.OAI_PMH_APP_DATA.get(
                                                      theme(request.access_route)).get('baseURL'),
                                                  },
                                            now=timestamp(),
                                            mimetype='text/xml')

            response = make_response(oai_error_xml)
            response.headers["Content-Type"] = "text/xml"

            return response

        # build query
        cursor = 0
        if resumption_token:
            r = app.extensions['redis']['REDIS_OAI_PMH_RT']
            rt = r.hget('resumptionToken', resumption_token)
            cursor = rt.get('cursor')
            oai_from = rt.get('from')
            oai_until = rt.get('until')
            oai_set = rt.get('set')

            if oai_from and not oai_until:
                query = 'recordChangeDate:[%s+TO+*]' % (oai_from + 'T00:00:00Z')
            elif not oai_from and oai_until:
                query = 'recordChangeDate:[*+TO+%s]' % (oai_until + 'T00:00:00Z')
            elif oai_from and oai_until:
                query = 'recordChangeDate:[%s+TO+%s]' % (oai_from + 'T00:00:00Z', oai_until + 'T00:00:00Z')
            else:
                query = '*:*'

            filterquery = []
            if oai_set:
                theset = oai_set
                if oai_set.startswith('doc-type'):
                    filterquery.append('oai_type:"%s"' % theset.replace('doc-type:', ''))
                if oai_set.startswith('ddc'):
                    filterquery.append('ddc:"%s"' % theset.replace('ddc:', ''))
                if oai_set == 'ec_fundedresources':
                    filterquery.append('fp7:*')

            # resumptionToken expired?
            if datetime.datetime.now() > datetime.datetime.strptime(rt.get('expirationDate'), "%Y-%m-%dT%H:%M:%S.%fZ"):
                oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                                data={'verb': verb,
                                                      'error_code': 'badResumptionToken',
                                                      'error_text': 'The value of the resumptionToken argument is invalid or expired.',
                                                      'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                      },
                                                now=timestamp(),
                                                mimetype='text/xml')

                response = make_response(oai_error_xml)
                response.headers["Content-Type"] = "text/xml"

                return response
        else:
            if oai_from and not oai_until:
                query = 'recordChangeDate:[%s+TO+*]' % (oai_from + 'T00:00:00Z')
            elif not oai_from and oai_until:
                query = 'recordChangeDate:[*+TO+%s]' % (oai_until + 'T00:00:00Z')
            elif oai_from and oai_until:
                query = 'recordChangeDate:[%s+TO+%s]' % (oai_from + 'T00:00:00Z', oai_until + 'T00:00:00Z')
            else:
                query = '*:*'

            filterquery = []
            if oai_set:
                theset = oai_set
                if oai_set.startswith('doc-type'):
                    filterquery.append('oai_type:"%s"' % theset.replace('doc-type:', ''))
                if oai_set.startswith('ddc'):
                    filterquery.append('ddc:"%s"' % theset.replace('ddc:', ''))
                if oai_set == 'ec_fundedresources':
                    filterquery.append('fp7:*')

        # Solr request
        search_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           start=cursor, rows=secrets.BATCH_SIZE,
                           query=query,
                           fquery=filterquery,
                           fields=['id', 'recordChangeDate', 'oai_type', 'ddc'],
                           sort='recordChangeDate asc')
        search_solr.request()
        result = search_solr.results

        hit_count = search_solr.count()

        rt_last = False
        if int(cursor) + secrets.BATCH_SIZE >= hit_count:
            rt_last = True

        rt_id = ''
        rt = {}
        if hit_count > secrets.BATCH_SIZE and cursor < hit_count:
            rt_id = uuid.uuid4()
            rt.setdefault('expirationDate', (datetime.datetime.now() + datetime.timedelta(2)).isoformat() + 'Z')
            rt.setdefault('cursor', (int(cursor) + secrets.BATCH_SIZE))
            if oai_from:
                rt.setdefault('from', oai_from)
            if oai_until:
                rt.setdefault('until', oai_until)
            if oai_set:
                rt.setdefault('set', oai_set)

            r = app.extensions['redis']['REDIS_OAI_PMH_RT']
            r.hset('resumptionToken', rt_id, rt)

        oai_listidentifiers_xml = render_template('oai_pmh/oai_listidentifiers.xml',
                                                  data={'verb': verb,
                                                        'docs': result,
                                                        'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                                        'id_prefix': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('id_prefix'),
                                                        'resumption_token': rt_id,
                                                        'expiration_date': rt.get('expirationDate'),
                                                        'cursor': rt.get('cursor'),
                                                        'complete_list_size': hit_count,
                                                        'last_batch': rt_last,
                                                        'metadata_prefix': oai_metadata_prefix,
                                                        'from': oai_from,
                                                        'until': oai_until,
                                                        'set': oai_set,
                                                        },
                                                  now=timestamp(),
                                                  mimetype='text/xml')

        response = make_response(oai_listidentifiers_xml)
        response.headers["Content-Type"] = "text/xml"

        return response

    else:
        oai_error_xml = render_template('oai_pmh/oai_error.xml',
                                        data={'verb': verb,
                                              'error_code': 'badVerb',
                                              'error_text': 'Value of the verb argument is not a legal OAI-PMH verb, the verb argument is missing, or the verb argument is repeated.',
                                              'base_url': secrets.OAI_PMH_APP_DATA.get(theme(request.access_route)).get('baseURL'),
                                              },
                                        now=timestamp(),
                                        mimetype='text/xml')

        response = make_response(oai_error_xml)
        response.headers["Content-Type"] = "text/xml"

        return response


@app.route("/spec")
def spec():
    swag = swagger(app, from_file_keyword='swagger_from_file')
    swag['info']['version'] = secrets.SWAGGER_API_VERSION
    swag['info']['title'] = secrets.SWAGGER_TITLE
    swag['info']['description'] = secrets.SWAGGER_DESCRIPTION
    swag['schemes'] = secrets.SWAGGER_SCHEMES
    swag['host'] = secrets.SWAGGER_HOST
    swag['basePath'] = secrets.SWAGGER_BASEPATH
    swag['tags'] = [
        {
            'name': 'monitoring',
            'description': 'Methods for monitoring the service'
        },
        {
            'name': 'oai-pmh',
            'description': 'OAI-PMH Data Provider'
        }
    ]
    return jsonify(swag)


@app.route('/_ping')
@csrf.exempt
def _ping():
    """
        Ping the service

        swagger_from_file: bibliography_doc/_ping.yml
    """
    try:
        if 'failed' in json.dumps(dependencies_health(), indent=4):
            return make_response('One or more dependencies unavailable!', 500)
        else:
            return make_response('pong', 200)
    except Exception:
        return make_response('One or more dependencies unavailable!', 500)


@app.route('/_health')
@csrf.exempt
def _health():
    """
        Showing the health of the service an its dependencies

        swagger_from_file: bibliography_doc/_health.yml
    """
    health_json = {
        "name": "hb2_flask",
        "timestamp": timestamp(),
        "dependencies": dependencies_health()
    }

    json_string = json.dumps(health_json, indent=4)
    status = 200

    if 'failed' in json_string:
        status = 500

    response = make_response(json_string, status)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-type'] = 'application/json'

    return response


def dependencies_health():
    dependencies = []

    # health of Solr cores
    try:
        status = requests.get(
            'http://%s:%s/%s/hb2/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "hb2"',
        'status': status,
        'description': 'Storage for bibliographic data',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/hb2_users/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "hb2_users"',
        'status': status,
        'description': 'Storage for registered users',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/group/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "group',
        'status': status,
        'description': 'Storage for working groups or projects data',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/organisation/admin/ping?wt=json' % (
                secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "organisation',
        'status': status,
        'description': 'Storage for organisations data',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/person/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "person',
        'status': status,
        'description': 'Storage for persons data',
        'external': False
    })

    # health of Redis
    try:
        storage = app.extensions['redis']['REDIS_OAI_PMH_RT']
        status = storage.dbsize()
    except:
        status = 0

    if status:
        dependencies.append({
            'service': 'Redis "OAI_PMH_RT"',
            'status': 'ok',
            'description': 'resumption tokens',
            'external': False
        })
    else:
        dependencies.append({
            'service': 'Redis "OAI_PMH_RT"',
            'status': 'failed',
            'description': 'resumption tokens',
            'external': False
        })

    return dependencies


@app.route('/redis/stats/<db>')
def redis_stats(db='2'):
    if db == '2':
        storage = app.extensions['redis']['REDIS_OAI_PMH_RT']

        stats = {}
        stats.setdefault('dbsize', storage.dbsize())

        content = []
        for key in storage.keys('*'):
            item = {}
            try:
                item.setdefault(key.decode("utf-8"), '%s ...' % storage.get(key).decode("utf-8")[:100])
            except Exception:
                item.setdefault(key.decode("utf-8"), storage.hgetall(key))
            content.append(item)

        stats.setdefault('items', content)

        return jsonify({'stats': stats})
    else:
        return 'No database with ID %s exists!' % db

# ---------- MAIN ----------

def str2bool(v):
    if str(v).lower() in ("yes", "true", "True", "t", "1"):
        return True
    else:
        return False


def theme(ip):
    # logging.info('IPs: %s' % len(ip))
    # logging.info('IPs: %s' % ip)
    site = 'tudo'
    try:
        idx = len(ip) - 2
    except Exception:
        idx = ip[0]

    if ip[idx].startswith('134.147'):
        site = 'rub'
    elif ip[idx].startswith('129.217'):
        site = 'tudo'

    return site


def timestamp():
    europe = pytz.timezone('Europe/London')
    return str(utcdatetime.utcdatetime.from_datetime(europe.localize(datetime.datetime.now())))


if __name__ == '__main__':
    app.run(port=secrets.APP_PORT)
