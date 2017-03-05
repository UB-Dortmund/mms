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
from logging.handlers import RotatingFileHandler

from jose import jwt
from jose.exceptions import JWTClaimsError

import requests
import simplejson as json

from flask import Flask, request, jsonify
from flask import make_response
from flask_cors import CORS
from flask_redis import Redis
from flask_swagger import swagger
from flask_wtf.csrf import CSRFProtect

from jsonmerge import Merger

import wtforms_json

import persistence

from forms.forms import *

from utils import display_vocabularies
from utils.solr_handler import Solr

try:
    import local_api_secrets as secrets
except ImportError:
    import api_secrets as secrets


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

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

csrf = CSRFProtect(app)

wtforms_json.init()

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
handler.setFormatter(log_formatter)
app.logger.addHandler(handler)

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
log.addHandler(handler)

app.config['REDIS_CONSOLIDATE_PERSONS_URL'] = secrets.REDIS_CONSOLIDATE_PERSONS_URL
Redis(app, 'REDIS_CONSOLIDATE_PERSONS')

app.config['REDIS_PUBLIST_CACHE_URL'] = secrets.REDIS_PUBLIST_CACHE_URL
Redis(app, 'REDIS_PUBLIST_CACHE')


# ---------- REST ----------


@app.route("/api/spec")
def spec():
    swag = swagger(app, from_file_keyword='swagger_from_file', )
    swag['info']['version'] = '2016-12-09'
    swag['info']['title'] = 'hb2_flask'
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
            'name': 'groups',
            'description': 'Working groups/Projects operations'
        },
        {
            'name': 'organisations',
            'description': 'Organisation operations'
        },
        {
            'name': 'persons',
            'description': 'Persons operations'
        },
        {
            'name': 'works',
            'description': 'Works operations'
        },
    ]
    return jsonify(swag)


@app.route('/api/_ping')
@csrf.exempt
def _ping():
    """
        Ping the service

        swagger_from_file: api_doc/_ping.yml
    """
    try:
        if 'failed' in json.dumps(dependencies_health(), indent=4):
            return make_response('One or more dependencies unavailable!', 500)
        else:
            return make_response('pong', 200)
    except Exception:
        return make_response('One or more dependencies unavailable!', 500)


@app.route('/api/_health')
@csrf.exempt
def _health():
    """
        Showing the health of the service an its dependencies

        swagger_from_file: api_doc/_health.yml
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

    # health of Redis
    try:
        storage = app.extensions['redis']['REDIS_CONSOLIDATE_PERSONS']
        status = storage.dbsize()
    except:
        status = 0

    if status:
        dependencies.append({
            'service': 'Redis "CONSOLIDATE_PERSONS"',
            'status': 'ok',
            'description': 'Storage for bibliographic records not linked to institutional actors',
            'external': False
        })
    else:
        dependencies.append({
            'service': 'Redis "CONSOLIDATE_PERSONS"',
            'status': 'failed',
            'description': 'Storage for bibliographic records not linked to institutional actors',
            'external': False
        })

    try:
        storage = app.extensions['redis']['REDIS_PUBLIST_CACHE']
        status = storage.dbsize()
    except:
        status = 0

    if status:
        dependencies.append({
            'service': 'Redis "PUBLIST_CACHE"',
            'status': 'ok',
            'description': 'Cache for user defined citation lists',
            'external': False
        })
    else:
        dependencies.append({
            'service': 'Redis "PUBLIST_CACHE"',
            'status': 'failed',
            'description': 'Cache for user defined citation lists',
            'external': False
        })

    # health of GBV SRU
    response = requests.get('http://sru.gbv.de/gvk')
    if response.status_code == 200:
        dependencies.append({'service': 'GVK SRU', 'status': 'ok', 'external': True})
    else:
        dependencies.append({'service': 'GVK SRU', 'status': 'failed', 'external': True})
    # health of CrossRef
    response = requests.get('http://api.crossref.org/works?query=frbr')
    if response.status_code == 200:
        dependencies.append({'service': 'CrossRef API', 'status': 'ok', 'external': True})
    else:
        dependencies.append({'service': 'CrossRef API', 'status': 'failed', 'external': True})
    # health of DataCite
    try:
        response = requests.get('https://api.datacite.org/works?query=frbr', timeout=3)
        if response.status_code == 200:
            dependencies.append({'service': 'DataCite API', 'status': 'ok', 'external': True})
        else:
            dependencies.append({'service': 'DataCite API', 'status': 'failed', 'external': True})
    except requests.exceptions.ReadTimeout:
        dependencies.append({'service': 'DataCite API', 'status': 'failed', 'external': True})
    # health of ORCID
    response = requests.get('https://pub.orcid.org/v2.0_rc3/status', headers={'Accept': 'text/plain'})
    if response.status_code == 200:
        dependencies.append({'service': 'ORCID API', 'status': 'ok', 'external': True})
    else:
        dependencies.append({'service': 'ORCID API', 'status': 'failed', 'external': True})
    # health of PAIA
    paia_health_json = requests.get(
        'https://api.ub.tu-dortmund.de/paia/_health',
        headers={'Accept': 'application/json'}).json()
    if 'failed' in json.dumps(paia_health_json):
        dependencies.append({
            'service': paia_health_json.get('name'),
            'status': 'failed',
            'description': 'Authorization Service of TU Dortmund University, University Library',
            'external': False
        })
    else:
        dependencies.append({
            'service': paia_health_json.get('name'),
            'status': 'ok',
            'description': 'Authorization Service of TU Dortmund University, University Library',
            'external': False
        })
    # TODO health of RUB Login Service
    # TODO health of the Ticket Services

    return dependencies


@app.route('/api/work/<work_id>', methods=['GET'])
@csrf.exempt
def work_get(work_id=''):
    """
        Get a work

        swagger_from_file: api_doc/work_get.yml
    """
    result = persistence.get_work(work_id)

    if result:
        thedata = json.loads(result.get('wtf_json'))
        resp = make_response(json.dumps(thedata, indent=4), 200)
        resp.headers['Content-Type'] = 'application/json'
        return resp

    else:
        resp = make_response('NOT FOUND: work resource \'%s\' not found!' % work_id, 404)
        resp.headers['Content-Type'] = 'text/plain'
        return resp


@app.route('/api/work', methods=['POST'])
@csrf.exempt
def work_post():
    """
        Create a new work

        swagger_from_file: api_doc/work_post.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if request.headers.get('Authorization'):

            if is_token_valid(request.headers.get('Authorization')):

                thedata = request.data.decode("utf-8")

                result = persistence.get_work(json.loads(thedata).get('id'))

                rel = str2bool(request.args.get('rel', 'true'))

                if result:

                    # TODO if force=true and existing id not equals posted id: add data
                    force = str2bool(request.args.get('force', 'false'))
                    rewrite = str2bool(request.args.get('rewrite', 'false'))

                    if (force and json.loads(thedata).get('id') != json.loads(result.get('wtf_json')).get('id')) or rewrite:
                        form = display_vocabularies.PUBTYPE2FORM.get(json.loads(thedata).get('pubtype')).from_json(json.loads(thedata))
                        form.created.data = timestamp()
                        form.changed.data = timestamp()
                        new_id, message = persistence.record2solr(form, action='create', relitems=rel)
                        message.append('record forced: %s' % json.loads(thedata).get('id'))

                        result = persistence.get_work(new_id)

                        if result:
                            response_json = {"message": message, "work": json.loads(result.get('wtf_json'))}
                            return make_response(json.dumps(response_json, indent=4), 201)
                        else:
                            response_json = {"message": "failed! record not indexed!", "work": json.loads(thedata)}
                            return make_response(json.dumps(response_json, indent=4), 500)
                    else:
                        return make_response('Bad request: work already exist!', 400)

                else:
                    form = display_vocabularies.PUBTYPE2FORM.get(json.loads(thedata).get('pubtype')).from_json(json.loads(thedata))
                    form.created.data = timestamp()
                    form.changed.data = timestamp()
                    new_id, message = persistence.record2solr(form, action='create', relitems=rel)

                    result = persistence.get_work(new_id)

                    if result:
                        response_json = {"message": message, "work": json.loads(result.get('wtf_json'))}
                        return make_response(json.dumps(response_json, indent=4), 201)
                    else:
                        response_json = {"message": "failed! record not indexed!", "work": json.loads(thedata)}
                        return make_response(json.dumps(response_json, indent=4), 500)
            else:
                return make_response('Unauthorized', 401)
        else:
            return make_response('Unauthorized', 401)

    else:
        return make_response('Bad request: invalid accept header!', 400)


@app.route('/api/work/<work_id>', methods=['PUT'])
@csrf.exempt
def work_put(work_id=''):
    """
        Update an existing work

        swagger_from_file: api_doc/work_put.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if is_token_valid(request.headers.get('Authorization')):

            result = persistence.get_work(work_id)

            if result:

                original_work = json.loads(result.get('wtf_json'))

                addition_work = ''
                try:
                    addition_work = json.loads(request.data.decode("utf-8"))
                    # print(addition_work)
                except:
                    pass

                if addition_work:
                    if addition_work.get('id') and addition_work.get('id') != original_work.get('id'):

                        return make_response(
                            'Conflict: The ID of the additional data already exists as "same_as"! Please check your data!', 409)
                    else:
                        # init merger "work"
                        with open('conf/works_merger.schema.json') as data_file:
                            schema_works_merger = json.load(data_file)

                        merger = Merger(schema_works_merger)

                        # merge it!
                        merged_work = merger.merge(original_work, addition_work)
                        # print(json.dumps(merged_work, indent=4))

                        # load it!
                        form = display_vocabularies.PUBTYPE2FORM.get(merged_work.get('pubtype')).from_json(merged_work)
                        form.changed.data = timestamp()

                        # store it
                        rel = str2bool(request.args.get('rel', 'true'))
                        new_id, message = persistence.record2solr(form, action='update', relitems=rel)

                        response_json = {"message": message, "work": merged_work}

                        return make_response(json.dumps(response_json, indent=4), 200)
                else:
                    # load it!
                    form = display_vocabularies.PUBTYPE2FORM.get(original_work.get('pubtype')).from_json(original_work)
                    form.changed.data = timestamp()

                    # store it
                    new_id, message = persistence.record2solr(form, action='update', relitems=False)

                    response_json = {"message": message, "work": original_work}

                    return make_response(json.dumps(response_json, indent=4), 200)
            else:
                return make_response('work resource \'%s\' not found!' % work_id, 404)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid accept header!', 400)


@app.route('/api/work/<work_id>', methods=['DELETE'])
@csrf.exempt
def work_delete(work_id=''):
    """
        Delete an existing work

        swagger_from_file: api_doc/work_delete.yml
    """

    if is_token_valid(request.headers.get('Authorization')):
        # TODO decide on base of the api key scopes
        # load work
        delete_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='hb2',
                                query='id:%s' % work_id)
        delete_work_solr.request()

        if delete_work_solr.results:
            thedata = json.loads(delete_work_solr.results[0].get('wtf_json'))
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # modify status to 'deleted'
            form.editorial_status.data = 'deleted'
            form.changed.data = timestamp()
            form.note.data = 'Deleted via REST API'
            # save work
            persistence.record2solr(form, action='delete')

            return make_response('work deleted!', 204)
        else:
            return make_response('work resource \'%s\' not found!' % work_id, 404)

    else:
        return make_response('Unauthorized', 401)


@app.route('/person/<person_id>', methods=['GET'])
@csrf.exempt
def person_get(person_id=''):
    """
        Get a person

        swagger_from_file: api_doc/person_get.yml
    """
    result = persistence.get_person(person_id=person_id)
    if result:

        thedata = json.loads(result.get('wtf_json'))

        # if not valid access_token then limit the data fields!
        if request.headers.get('Authorization'):

            if is_token_valid(request.headers.get('Authorization')):

                resp = make_response(json.dumps(thedata, indent=4), 200)
                resp.headers['Content-Type'] = 'application/json'
                return resp
            else:
                resp = make_response('UNAUTHORIZED: invalid token!', 401)
                resp.headers['Content-Type'] = 'text/plain'
                return resp
        else:
            limited_data = {}
            limited_data.setdefault('id', thedata.get('id'))
            limited_data.setdefault('same_as', thedata.get('same_as'))
            limited_data.setdefault('created', thedata.get('created'))
            limited_data.setdefault('changed', thedata.get('changed'))
            limited_data.setdefault('editorial_status', thedata.get('editorial_status'))

            limited_data.setdefault('name', thedata.get('name'))
            limited_data.setdefault('also_known_as', thedata.get('also_known_as'))
            limited_data.setdefault('gnd', thedata.get('gnd'))
            limited_data.setdefault('orcid', thedata.get('orcid'))
            limited_data.setdefault('affiliation', thedata.get('affiliation'))
            limited_data.setdefault('group', thedata.get('group'))

            resp = make_response(json.dumps(limited_data, indent=4), 200)
            resp.headers['Content-Type'] = 'application/json'
            return resp

    else:
        resp = make_response('NOT FOUND: person resource \'%s\' not found!' % person_id, 404)
        resp.headers['Content-Type'] = 'text/plain'
        return resp


@app.route('/api/person', methods=['POST'])
@csrf.exempt
def person_post():
    """
        Create a new person

        swagger_from_file: api_doc/person_post.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if request.headers.get('Authorization'):

            if is_token_valid(request.headers.get('Authorization')):

                thedata = request.data

                result = persistence.get_person(json.loads(thedata).get('id'))

                if result:

                    # TODO if force=true and existing id not equals posted id: add data
                    force = str2bool(request.args.get('force', 'false'))
                    rewrite = str2bool(request.args.get('rewrite', 'false'))

                    if (force and json.loads(thedata).get('id') != json.loads(result.get('wtf_json')).get('id')) or rewrite:
                        form = PersonAdminForm.from_json(json.loads(thedata))
                        form.created.data = timestamp()
                        form.changed.data = timestamp()
                        doit, new_id, message = persistence.person2solr(form, action='create')
                        message.append('record forced: %s' % json.loads(thedata).get('id'))

                        result = persistence.get_person(new_id)
                        if result:
                            response_json = {"message": message, "person": json.loads(result.get('wtf_json'))}
                            return make_response(json.dumps(response_json, indent=4), 201)
                        else:
                            response_json = {"message": "failed! record not indexed!", "person": json.loads(thedata)}
                            return make_response(json.dumps(response_json, indent=4), 500)
                    else:
                        return make_response('Bad request: person already exist!', 400)
                else:
                    form = PersonAdminForm.from_json(json.loads(thedata))
                    form.created.data = timestamp()
                    form.changed.data = timestamp()
                    doit, new_id, message = persistence.person2solr(form, action='create')

                    result = persistence.get_person(new_id)
                    if result:
                        response_json = {"message": message, "person": json.loads(result.get('wtf_json'))}
                        return make_response(json.dumps(response_json, indent=4), 201)
                    else:
                        response_json = {"message": "failed! record not indexed!", "person": json.loads(thedata)}
                        return make_response(json.dumps(response_json, indent=4), 500)
            else:
                return make_response('Unauthorized', 401)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid accept header!', 400)


@app.route('/api/person/<person_id>', methods=['PUT'])
@csrf.exempt
def person_put(person_id=''):
    """
        Update an existing person

        swagger_from_file: api_doc/person_put.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if is_token_valid(request.headers.get('Authorization')):

            addition_person = json.loads(request.data.decode("utf-8"))

            result = persistence.get_person(person_id)

            if result:

                original_person = json.loads(result.get('wtf_json'))

                if addition_person.get('id') and addition_person.get('id') != original_person.get('id'):

                    return make_response(
                        'Conflict: The ID of the additional data already exists as "same_as"! Please check your data!', 409)
                else:
                    # init merger "person"
                    with open('conf/person_merger.schema.json') as data_file:
                        schema_person_merger = json.load(data_file)

                    merger = Merger(schema_person_merger)

                    # merge it!
                    merged_person = merger.merge(original_person, addition_person)

                    # load it!
                    form = PersonAdminForm.from_json(merged_person)
                    form.changed.data = timestamp()
                    doit, new_id, message = persistence.person2solr(form, action='update')

                    response_json = {"message": message, "person": merged_person}

                    return make_response(json.dumps(response_json, indent=4), 201)
            else:
                return make_response('person resource \'%s\' not found!' % person_id, 404)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid accept header!', 400)


@app.route('/api/person/<person_id>', methods=['DELETE'])
@csrf.exempt
def person_delete(person_id=''):
    """
        Delete an existing person

        swagger_from_file: api_doc/person_delete.yml
    """

    if is_token_valid(request.headers.get('Authorization')):
        # TODO decide on base of the api key scopes
        # load group
        delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='person',
                                  query='id:%s' % person_id)
        delete_person_solr.request()

        if delete_person_solr.results:
            thedata = json.loads(delete_person_solr.results[0].get('wtf_json'))
            form = PersonAdminForm.from_json(thedata)
            # modify status to 'deleted'
            form.editorial_status.data = 'deleted'
            form.changed.data = timestamp()
            form.note.data = 'Deleted via REST API'
            # save group
            persistence.person2solr(form, action='delete')

            return make_response('person deleted!', 204)
        else:
            return make_response('person resource \'%s\' not found!' % person_id, 404)

    else:
        return make_response('Unauthorized', 401)


@app.route('/api/organisation/<orga_id>', methods=['GET'])
@csrf.exempt
def orga_get(orga_id=''):
    """
        Get an organisation

        swagger_from_file: api_doc/orga_get.yml
    """
    result = persistence.get_orga(orga_id=orga_id)

    if result:

        thedata = json.loads(result.get('wtf_json'))

        # if not valid access_token then limit the data fields!
        if request.headers.get('Authorization'):

            if is_token_valid(request.headers.get('Authorization')):

                resp = make_response(json.dumps(thedata, indent=4), 200)
                resp.headers['Content-Type'] = 'application/json'
                return resp
            else:
                resp = make_response('UNAUTHORIZED: invalid token!', 401)
                resp.headers['Content-Type'] = 'text/plain'
                return resp
        else:
            del thedata['correction_request']
            del thedata['dwid']
            del thedata['owner']
            del thedata['deskman']

            resp = make_response(json.dumps(thedata, indent=4), 200)
            resp.headers['Content-Type'] = 'application/json'
            return resp
    else:
        resp = make_response('organisation resource \'%s\' not found!' % orga_id, 404)
        resp.headers['Content-Type'] = 'text/plain'
        return resp


@app.route('/api/organisation', methods=['POST'])
@csrf.exempt
def orga_post():
    """
        Create a new organisation

        swagger_from_file: api_doc/orga_post.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if request.headers.get('Authorization'):

            if is_token_valid(request.headers.get('Authorization')):

                thedata = request.data

                result = persistence.get_orga(json.loads(thedata).get('id'))

                rel = str2bool(request.args.get('rel', 'true'))

                if result:

                    # TODO if force=true and existing id not equals posted id: add data
                    force = str2bool(request.args.get('force', 'false'))
                    rewrite = str2bool(request.args.get('rewrite', 'false'))

                    if (force and json.loads(thedata).get('id') != json.loads(result.get('wtf_json')).get('id')) or rewrite:
                        form = OrgaAdminForm.from_json(json.loads(thedata))
                        form.created.data = timestamp()
                        form.changed.data = timestamp()
                        new_id, message = persistence.orga2solr(form, action='create', relitems=rel)
                        message.append('record forced: %s' % json.loads(thedata).get('id'))

                        result = persistence.get_orga(new_id)
                        if result:
                            response_json = {"message": message, "orga": json.loads(result.get('wtf_json'))}
                            return make_response(json.dumps(response_json, indent=4), 201)
                        else:
                            response_json = {"message": "failed! record not indexed!", "orga": json.loads(thedata)}
                            return make_response(json.dumps(response_json, indent=4), 500)
                    else:
                        return make_response('Bad request: organisation already exist!', 400)
                else:
                    form = OrgaAdminForm.from_json(json.loads(thedata))
                    form.created.data = timestamp()
                    form.changed.data = timestamp()
                    new_id, message = persistence.orga2solr(form, action='create', relitems=rel)

                    result = persistence.get_orga(new_id)
                    if result:
                        response_json = {"message": message, "orga": json.loads(result.get('wtf_json'))}
                        return make_response(json.dumps(response_json, indent=4), 201)
                    else:
                        response_json = {"message": "failed! record not indexed!", "orga": json.loads(thedata)}
                        return make_response(json.dumps(response_json, indent=4), 500)
            else:
                return make_response('Unauthorized', 401)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid Content-Type header!', 400)


@app.route('/api/organisation/<orga_id>', methods=['PUT'])
@csrf.exempt
def orga_put(orga_id=''):
    """
        Update an existing organisation

        swagger_from_file: api_doc/orga_put.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if is_token_valid(request.headers.get('Authorization')):

            addition_orga = json.loads(request.data.decode("utf-8"))

            result = persistence.get_orga(orga_id)

            if result:

                original_orga = json.loads(result.get('wtf_json'))

                if addition_orga.get('id') and addition_orga.get('id') != original_orga.get('id'):

                    return make_response(
                        'Conflict: The ID of the additional data already exists as "same_as"! Please check your data!', 409)
                else:
                    # init merger "person"
                    with open('conf/orga_merger.schema.json') as data_file:
                        schema_orga_merger = json.load(data_file)

                    merger = Merger(schema_orga_merger)

                    # merge it!
                    merged_orga = merger.merge(original_orga, addition_orga)

                    # load it!
                    form = OrgaAdminForm.from_json(merged_orga)
                    form.changed.data = timestamp()
                    logging.info(form.data)
                    new_id, message = persistence.orga2solr(form, action='update')

                    response_json = {"message": message, "organisation": merged_orga}

                    return make_response(json.dumps(response_json, indent=4), 201)
            else:
                return make_response('organisation resource \'%s\' not found!' % orga_id, 404)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid Content-Type header!', 400)


@app.route('/api/organisation/<orga_id>', methods=['DELETE'])
@csrf.exempt
def orga_delete(orga_id=''):
    """
        Delete an existing organisation

        swagger_from_file: api_doc/orga_delete.yml
    """

    if is_token_valid(request.headers.get('Authorization')):
        # TODO decide on base of the api key scopes
        # load group
        delete_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='organisation',
                                query='id:%s' % orga_id)
        delete_orga_solr.request()

        if delete_orga_solr.results:
            thedata = json.loads(delete_orga_solr.results[0].get('wtf_json'))
            form = OrgaAdminForm.from_json(thedata)
            # modify status to 'deleted'
            form.editorial_status.data = 'deleted'
            form.changed.data = timestamp()
            form.note.data = 'Deleted via REST API'
            # save group
            persistence.orga2solr(form, action='delete')

            return make_response('organisation deleted!', 204)
        else:
            return make_response('organisation resource \'%s\' not found!' % orga_id, 404)

    else:
        return make_response('Unauthorized', 401)


@app.route('/api/group/<group_id>', methods=['GET'])
@csrf.exempt
def group_get(group_id=''):
    """
        Get a group

        swagger_from_file: api_doc/group_get.yml
    """
    result = persistence.get_group(group_id=group_id)

    if result:

        thedata = json.loads(result.get('wtf_json'))

        if request.headers.get('Authorization'):
            if is_token_valid(request.headers.get('Authorization')):

                resp = make_response(json.dumps(thedata, indent=4), 200)
                resp.headers['Content-Type'] = 'application/json'
                return resp
            else:
                resp = make_response('UNAUTHORIZED: invalid token!', 401)
                resp.headers['Content-Type'] = 'text/plain'
                return resp
        else:
            del thedata['correction_request']
            del thedata['owner']
            del thedata['deskman']

            resp = make_response(json.dumps(thedata, indent=4), 200)
            resp.headers['Content-Type'] = 'application/json'
            return resp
    else:
        resp = make_response('group resource \'%s\' not found!' % group_id, 404)
        resp.headers['Content-Type'] = 'text/plain'
        return resp


@app.route('/api/group', methods=['POST'])
@csrf.exempt
def group_post():
    """
        Create a new group

        swagger_from_file: api_doc/group_post.yml
    """

    if request.headers.get('Content-Type') == 'application/json':

        if request.headers.get('Authorization'):

            if is_token_valid(request.headers.get('Authorization')):

                thedata = request.data

                result = persistence.get_group(json.loads(thedata).get('id'))

                rel = str2bool(request.args.get('rel', 'true'))

                if result:
                    # TODO if force=true and existing id not equals posted id: add data
                    force = str2bool(request.args.get('force', 'false'))
                    rewrite = str2bool(request.args.get('rewrite', 'false'))

                    if (force and json.loads(thedata).get('id') != json.loads(result.get('wtf_json')).get('id')) or rewrite:
                        form = GroupAdminForm.from_json(json.loads(thedata))
                        form.created.data = timestamp()
                        form.changed.data = timestamp()
                        new_id, message = persistence.group2solr(form, action='create', relitems=rel)
                        message.append('record forced: %s' % json.loads(thedata).get('id'))

                        result = persistence.get_group(new_id)
                        if result:
                            response_json = {"message": message, "group": json.loads(result.get('wtf_json'))}
                            return make_response(json.dumps(response_json, indent=4), 201)
                        else:
                            response_json = {"message": "failed! record not indexed!", "group": json.loads(thedata)}
                            return make_response(json.dumps(response_json, indent=4), 500)
                    else:
                        return make_response('Bad request: group "%s" already exist!' % json.loads(thedata).get('id'), 400)
                else:
                    form = GroupAdminForm.from_json(json.loads(thedata))
                    form.created.data = timestamp()
                    form.changed.data = timestamp()
                    new_id, message = persistence.group2solr(form, action='create', relitems=rel)

                    result = persistence.get_group(new_id)

                    if result:
                        response_json = {"message": message, "group": json.loads(result.get('wtf_json'))}
                        return make_response(json.dumps(response_json, indent=4), 201)
                    else:
                        response_json = {"message": "failed! record not indexed!", "group": json.loads(thedata)}
                        return make_response(json.dumps(response_json, indent=4), 500)
            else:
                return make_response('Unauthorized', 401)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid accept header!', 400)


@app.route('/api/group/<group_id>', methods=['PUT'])
@csrf.exempt
def group_put(group_id=''):
    """
        Update an existing group

        swagger_from_file: api_doc/group_put.yml
    """

    if request.headers.get('Accept') == 'application/json':

        if is_token_valid(request.headers.get('Authorization')):

            addition_group = json.loads(request.data.decode("utf-8"))

            result = persistence.get_group(group_id)

            if result:

                original_group = json.loads(result.get('wtf_json'))

                if addition_group.get('id') and addition_group.get('id') != original_group.get('id'):

                    return make_response(
                        'Conflict: The ID of the additional data already exists as "same_as"! Please check your data!', 409)
                else:
                    # init merger "group"
                    with open('conf/group_merger.schema.json') as data_file:
                        schema_group_merger = json.load(data_file)

                    merger = Merger(schema_group_merger)

                    # merge it!
                    merged_group = merger.merge(original_group, addition_group)

                    # load it!
                    form = GroupAdminForm.from_json(merged_group)
                    form.changed.data = timestamp()
                    new_id, message = persistence.group2solr(form, action='update')

                    response_json = {"message": message, "group": merged_group}

                    return make_response(json.dumps(response_json, indent=4), 201)
            else:
                return make_response('group resource \'%s\' not found!' % group_id, 404)
        else:
            return make_response('Unauthorized', 401)
    else:
        return make_response('Bad request: invalid accept header!', 400)


@app.route('/api/group/<group_id>', methods=['DELETE'])
@csrf.exempt
def group_delete(group_id=''):
    """
        Delete an existing group

        swagger_from_file: api_doc/group_delete.yml
    """

    if is_token_valid(request.headers.get('Authorization')):
        # TODO decide on base of the api key scopes
        # load group
        delete_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                 application=secrets.SOLR_APP, core='group', query='id:%s' % group_id)
        delete_group_solr.request()

        if delete_group_solr.results:
            thedata = json.loads(delete_group_solr.results[0].get('wtf_json'))
            form = GroupAdminForm.from_json(thedata)
            # modify status to 'deleted'
            form.editorial_status.data = 'deleted'
            form.changed.data = timestamp()
            form.note.data = 'Deleted via REST API'
            # save group
            persistence.group2solr(form, action='delete')

            return make_response('group deleted!', 204)
        else:
            return make_response('group resource \'%s\' not found!' % group_id, 404)

    else:
        return make_response('Unauthorized', 401)


# validate JWT
def is_token_valid(token=''):

    if 'Bearer ' in token:

        try:
            jwt.decode(token.split('Bearer ')[1], secrets.API_SECRET, audience=secrets.API_JWT_AUD, algorithms=['HS256'])
            return True
        except JWTClaimsError:
            return False

    else:
        return False


def timestamp():
    date_string = str(datetime.datetime.now())[:-3]
    if date_string.endswith('0'):
        date_string = '%s1' % date_string[:-1]

    return date_string


def str2bool(v):
    if str(v).lower() in ("yes", "true",  "True", "t", "1"):
        return True
    else:
        return False


if __name__ == '__main__':
    app.run(port=secrets.APP_PORT)
