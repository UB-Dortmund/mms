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


from __future__ import (absolute_import, division, print_function, unicode_literals)

import logging
import re
from logging.handlers import RotatingFileHandler
from bs4 import BeautifulSoup

import requests
import simplejson as json
from flask import Flask, request, jsonify, url_for
from flask import make_response
from flask_cors import CORS
from flask_swagger import swagger
from flask_wtf.csrf import CSRFProtect

from forms.forms import *
import persistence
from utils.solr_handler import Solr

try:
    import local_stats_secrets as secrets
except ImportError:
    import stats_secrets as secrets


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

csrf = CSRFProtect(app)

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
handler.setFormatter(log_formatter)
app.logger.addHandler(handler)

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
log.addHandler(handler)


# ---------- EXPORT ----------

@app.route('/export/openapc/<year>', methods=['GET'])
@csrf.exempt
def export_openapc(year=''):
    '''
        Getting a bibliography

        swagger_from_file: api_doc/export_openapc.yml
    '''

    if theme(request.access_route) == 'dortmund':
        affiliation = 'tudo'
        affiliation_str = 'TU Dortmund'
    elif theme(request.access_route) == 'bochum':
        affiliation = 'rubi'
        affiliation_str = 'Ruhr-Universität Bochum'
    else:
        affiliation = ''
        affiliation_str = ''

    if affiliation:
        csv = '"institution";"period";"euro";"doi";"is_hybrid";"publisher";"journal_full_title";"issn";"url";"local_id"\n'

        oa_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2', handler='query',
                       query='oa_funds:true', facet='false', rows=100000,
                       fquery=['%s:true' % affiliation, 'fdate:%s' % year])
        oa_solr.request()
        results = oa_solr.results

        if len(results) > 0:
            for record in results:
                thedata = json.loads(record.get('wtf_json'))

                doi = record.get('doi')[0]
                is_hybrid = False
                if record.get('is_hybrid'):
                    is_hybrid = record.get('is_hybrid')
                publisher = ''
                journal_title = ''
                issn = ''
                url = ''
                if not doi:

                    journal_title = ''
                    if record.get('is_part_of_id'):
                        if record.get('is_part_of_id')[0]:
                            host = persistence.get_work(record.get('is_part_of_id')[0])
                            if host:
                                record = json.loads(host.get('wtf_json'))
                                # print(json.dumps(record, indent=4))
                                journal_title = record.get('title')
                                if record.get('fsubseries'):
                                    journal_title = record.get('fsubseries')
                                publisher = ''
                                if record.get('publisher'):
                                    publisher = record.get('publisher')
                                issn = ''
                                if record.get('ISSN'):
                                    for entry in record.get('ISSN'):
                                        if entry:
                                            issn = entry
                                            break

                    url = ''
                    if thedata.get('uri'):
                        for uri in thedata.get('uri'):
                            url = uri
                            break

                csv += '"%s";%s;%s;"%s";"%s";"%s";"%s";"%s";"%s";"%s"\n' % (
                    affiliation_str,
                    year,
                    0.00,
                    doi,
                    is_hybrid,
                    publisher,
                    journal_title,
                    issn,
                    url,
                    record.get('id')
                )

            resp = make_response(csv, 200)
            resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
            return resp
        else:
            return make_response('No results', 404)
    else:
        return make_response('No affiliation parameter set. Please contact the administrator!', 400)


@app.route('/export/oa_report/<year>', methods=['GET'])
@csrf.exempt
def export_oa_report(year=''):
    '''
        Getting a bibliography

        swagger_from_file: api_doc/export_oa_report.yml
    '''
    pubtype = request.args.get('pubtype', 'ArticleJournal')

    if theme(request.access_route) == 'dortmund':
        affiliation = 'tudo'
        affiliation_str = 'TU Dortmund'
    elif theme(request.access_route) == 'bochum':
        affiliation = 'rubi'
        affiliation_str = 'Ruhr-Universität Bochum'
    else:
        affiliation = ''
        affiliation_str = ''

    if affiliation:
        csv = '"AU";"TI";"SO";"DT";"RP";"EM";"OI";"PU";"ISSN";"E-ISSN";"DOI";"OA";"RP TUDO";"Fak"\n'

        # TODO search for all publications of the given year
        oa_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2', handler='query',
                       query='*:*', facet='false', rows=100000,
                       fquery=['%s:true' % affiliation, 'fdate:%s' % year, 'pubtype:%s' % pubtype])
        oa_solr.request()
        results = oa_solr.results

        if results:
            for record in results:
                thedata = json.loads(record.get('wtf_json'))

                author = ''
                corresponding_author = ''
                corresponding_affiliation = ''
                faks = ''
                for person in thedata.get('person'):
                    if 'aut' in person.get('role'):
                        author += person.get('name') + ';'
                        if person.get('corresponding_author'):
                            corresponding_author = person.get('name')
                            if person.get('tudo'):
                                corresponding_affiliation = True
                                if person.get('gnd'):
                                    tudo = persistence.get_person(person.get('gnd'))
                                    # print(person.get('gnd'))
                                    if tudo:
                                        if tudo.get('affiliation_id'):
                                            faks = ''
                                            for entry in tudo.get('affiliation_id'):
                                                affil = persistence.get_orga(entry)
                                                fak = ''
                                                if affil:
                                                    has_parent = False
                                                    fak = affil.get('pref_label')
                                                    if affil.get('parent_id'):
                                                        has_parent = True
                                                        fak = '%s / %s' % (affil.get('parent_label'), affil.get('pref_label'))
                                                    while has_parent:
                                                        affil = persistence.get_orga(affil.get('parent_id'))
                                                        if affil.get('parent_id'):
                                                            has_parent = True
                                                            fak = '%s / %s' % (affil.get('parent_label'), affil.get('pref_label'))
                                                        else:
                                                            has_parent = False
                                                else:
                                                    fak = 'LinkError: Person %s' % person.get('gnd')
                                                faks += fak + ';'
                                            faks = faks[:-1]

                author = author[:-1]

                publisher = ''
                journal_title = ''
                issn = ''
                journal_title = ''
                if record.get('is_part_of_id'):
                    if record.get('is_part_of_id')[0]:
                        host = persistence.get_work(record.get('is_part_of_id')[0])
                        if host:
                            record = json.loads(host.get('wtf_json'))
                            # print(json.dumps(record, indent=4))
                            journal_title = record.get('title')
                            if record.get('fsubseries'):
                                journal_title = record.get('fsubseries')
                            publisher = ''
                            if record.get('publisher'):
                                publisher = record.get('publisher')
                            issn = ''
                            if record.get('ISSN'):
                                for entry in record.get('ISSN'):
                                    if entry:
                                        issn = entry
                                        break

                csv += '"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s";"%s"\n' % (
                    author,
                    thedata.get('title'),
                    journal_title,
                    'article',
                    corresponding_author,
                    '',
                    '',
                    publisher,
                    issn,
                    '',
                    thedata.get('DOI')[0],
                    thedata.get('oa_funded'),
                    corresponding_affiliation,
                    faks,
                )

        resp = make_response(csv, 200)
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        return resp
    else:
        return make_response('No affiliation parameter set. Please contact the administrator!', 400)


# ---------- STATISTICS ----------


# ---------- REST ----------

@app.route("/export/spec")
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
            'name': 'export',
            'description': 'Special data views as exports'
        },
        {
            'name': 'statistics',
            'description': 'Statistics'
        },
    ]
    return jsonify(swag)


@app.route('/export/_ping')
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


@app.route('/export/_health')
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
            'http://%s:%s/%s/organisation/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
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

    return dependencies


# ---------- MAIN ----------

def str2bool(v):
    if str(v).lower() in ("yes", "true",  "True", "t", "1"):
        return True
    else:
        return False


def theme(ip):
    # logging.info('IPs: %s' % len(ip))
    # logging.info('IPs: %s' % ip)
    site = 'dortmund'
    try:
        idx = len(ip)-2
    except Exception:
        idx = ip[0]

    if ip[idx].startswith('134.147'):
        site = 'bochum'
    elif ip[idx].startswith('129.217'):
        site = 'dortmund'

    return site


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


if __name__ == '__main__':
    app.run(port=secrets.APP_PORT)
