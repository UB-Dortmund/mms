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

import ast
import base64
import logging
import re
import time
import xmlrpc.client
from io import BytesIO
from logging.handlers import RotatingFileHandler
from urllib import parse

import orcid
import requests
import simplejson as json
import wtforms_json
from citeproc import Citation, CitationItem
from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import formatter
from citeproc.py2compat import *
from citeproc.source.json import CiteProcJSON
from datadiff import diff_dict
from flask import Flask, render_template, redirect, request, jsonify, flash, url_for, send_file
from flask import make_response
from flask_babel import Babel, gettext
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required, \
    make_secure_token
from flask_paginate import Pagination
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_humanize import Humanize
from flask_redis import Redis
from flask_wtf.csrf import CSRFProtect
from lxml import etree
from requests import RequestException

from forms.forms import *

from processors import crossref_processor
from processors import datacite_processor
from processors import mods_processor
from processors import openurl_processor
from processors import orcid_processor
from processors import wtf_csl

from utils import display_vocabularies
from utils.solr_handler import Solr
from utils import urlmarker

import persistence

try:
    import local_app_secrets as secrets
except ImportError:
    import app_secrets as secrets


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

app.config['REDIS_CONSOLIDATE_PERSONS_URL'] = secrets.REDIS_CONSOLIDATE_PERSONS_URL
Redis(app, 'REDIS_CONSOLIDATE_PERSONS')

app.config['REDIS_PUBLIST_CACHE_URL'] = secrets.REDIS_PUBLIST_CACHE_URL
Redis(app, 'REDIS_PUBLIST_CACHE')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

babel = Babel(app)
humanize_filter = Humanize(app)

bootstrap = Bootstrap(app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = secrets.BOOTSTRAP_SERVE_LOCAL

csrf = CSRFProtect(app)

wtforms_json.init()

socketio = SocketIO(app)

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
handler.setFormatter(log_formatter)
app.logger.addHandler(handler)

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
log.addHandler(handler)

FORM_COUNT_RE = re.compile('-\d+$')
GND_RE = re.compile('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]')
UUID_RE = re.compile('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


@humanize_filter.localeselector
@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(display_vocabularies.LANGUAGES.keys())
    # return 'de_DE'


@app.template_filter('rem_form_count')
def rem_form_count_filter(mystring):
    """Remove trailing form counts to display only categories in FormField/FieldList combinations."""
    return FORM_COUNT_RE.sub('', mystring)


@app.template_filter('mk_time')
def mk_time_filter(mytime):
    try:
        return datetime.datetime.strptime(mytime, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        return datetime.datetime.strptime(mytime, '%Y-%m-%dT%H:%M:%S.%fZ')


@app.template_filter('last_split')
def last_split_filter(category):
    return category.rsplit('-', 1)[1]


# Just a temporary hack...
@app.template_filter('get_name')
def get_name(record):
    return json.loads(record.get('wtf_json')).get('name')


@app.template_filter('filter_remove')
def filter_remove_filter(fqstring, category):
    re.compile()


@app.template_filter('deserialize_json')
def deserialize_json_filter(thejson):
    return json.loads(thejson)


@app.route('/dedup/<idtype>/<path:id>')
def dedup(idtype='', id=''):
    resp = {'duplicate': False}
    dedup_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP, 
                      fquery=['%s:%s' % (idtype, id)], facet='false')
    dedup_solr.request()
    logging.info(dedup_solr.count())
    if dedup_solr.count() > 0:
        logging.info('poop')
        resp['duplicate'] = True

    return jsonify(resp)


@app.route('/')
@app.route('/index')
@app.route('/homepage')
def homepage():
    gnd_id = ''
    if current_user.is_authenticated:
        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           core='person', query='email:"' + current_user.email + '"', facet='false')
        person_solr.request()

        gnd_id = ''
        if len(person_solr.results) == 0:

            if '@rub.de' in current_user.email:
                query = 'email:%s' % str(current_user.email).replace('@rub.de', '@ruhr-uni-bochum.de')
                person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                   fields=['wtf_json'])
                person_solr.request()
            elif '@ruhr-uni-bochum.de' in current_user.email:
                query = 'email:%s' % str(current_user.email).replace('@ruhr-uni-bochum.de', '@rub.de')
                person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                   fields=['wtf_json'])
                person_solr.request()

            if len(person_solr.results) == 0:
                flash(gettext("You are currently not registered as contributor of any work. Please register new works..."), 'warning')
            else:
                if person_solr.results[0].get('gnd'):
                    gnd_id = person_solr.results[0].get('gnd').strip()

        else:
            if person_solr.results[0].get('gnd'):
                gnd_id = person_solr.results[0].get('gnd').strip()

        if gnd_id != '':
            index_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                              query='pnd:"%s%s%s"' % (gnd_id, '%23', current_user.name), facet='false')
            index_solr.request()
            if index_solr.count() == 0:
                flash(gettext("You haven't registered any records with us yet. Please do so now..."), 'danger')
        else:
            gnd_id = '11354300X'

    # ORCID iD counter
    filterquery = []
    filterquery.append('orcid:["" TO *]')
    filterquery.append('catalog:"Technische Universität Dortmund"')
    persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                        query='*:*', rows=0, core='person',
                        fquery=filterquery)
    persons_solr.request()

    orcid_tudo = persons_solr.count()

    filterquery = []
    filterquery.append('orcid:["" TO *]')
    filterquery.append('catalog:"Ruhr-Universität Bochum"')
    persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                        query='*:*', rows=0, core='person',
                        fquery=filterquery)
    persons_solr.request()

    orcid_rubi = persons_solr.count()

    # Works counter
    index_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                      query='tudo:true', facet='false')
    index_solr.request()

    works_tudo = index_solr.count()

    index_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                      query='rubi:true', facet='false')
    index_solr.request()

    works_rubi = index_solr.count()

    return render_template('index.html', header=lazy_gettext('Home'), site=theme(request.access_route),
                           gnd_id=gnd_id,
                           orcid_tudo=orcid_tudo, orcid_rubi=orcid_rubi,
                           works_tudo=works_tudo, works_rubi=works_rubi)


@app.route('/stats/<affiliation>')
def stats(affiliation=''):

    if affiliation:

        stats = {}

        # ORCID iD counter
        filterquery = []
        filterquery.append('orcid:["" TO *]')
        if affiliation == 'tudo':
            filterquery.append('catalog:"Technische Universität Dortmund"')
        if affiliation == 'rub':
            filterquery.append('catalog:"Ruhr-Universität Bochum"')

        persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                            query='*:*', rows=0, core='person',
                            fquery=filterquery)
        persons_solr.request()

        stats.setdefault('orcid_%s' % affiliation, persons_solr.count())

        # Works counter
        if affiliation == 'rub':
            index_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                              query='rubi:true', facet='false')
        else:
            index_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                              query='%s:true' % affiliation, facet='false')

        index_solr.request()

        stats.setdefault('works_%s' % affiliation, index_solr.count())

        return jsonify(stats)

    else:
        return make_response('Bad request! Usage: /stats/<affiliation>', 400)


@app.route('/search')
def search():
    page = int(request.args.get('page', 1))
    extended = int(request.args.get('ext', 0))
    format = request.args.get('format', '')
    query = request.args.get('q', '')
    # logging.info(query)
    if query == '':
        query = '*:*'
    core = request.args.get('core', 'hb2')
    # logging.info(core)
    filterquery = request.values.getlist('filter')
    sorting = request.args.get('sort', '')
    if sorting == '':
        sorting = 'fdate desc'
    elif sorting == 'relevance':
        sorting = ''

    list = int(request.args.get('list', 0))
    if list == 1:
        handler = 'query'
    else:
        handler = 'select'

    if extended == 1:
        return render_template('search.html', header=lazy_gettext('Search'), site=theme(request.access_route))

    if format == 'csl':
        # TODO generate publication list using CSL
        export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query=query, export_field='wtf_json',
                           core=core)
        export_docs = export_solr.export()
        # logging.info(export_docs)
        return jsonify({'items': wtf_csl.wtf_csl(export_docs)})

    rows = 20
    search_solr = None

    if core == 'hb2':
        # logging.info('SORT: %s' % sorting)
        facets = secrets.SOLR_SEARCH_FACETS

        if not current_user.is_authenticated \
                or (current_user.role != 'admin' and current_user.role != 'superadmin' and 'owner:' not in request.full_path):
            if theme(request.access_route) == 'dortmund' and 'tudo:true' not in filterquery:
                filterquery.append('tudo:true')
            if theme(request.access_route) == 'bochum' and 'rubi:true' not in filterquery:
                filterquery.append('rubi:true')

            if '-editorial_status:deleted' not in filterquery:
                filterquery.append('-editorial_status:deleted')

        search_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           core=core, handler=handler, start=(page - 1) * rows, rows=rows,
                           query=query.replace('#', '\%23'),
                           fquery=filterquery, sort=sorting, json_facet=facets)
    if core == 'person':
        if sorting == '' or sorting == 'fdate desc':
            sorting = 'changed desc'
        # logging.info('SORT: %s' % sorting)
        search_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           core=core, handler=handler,  start=(page - 1) * rows, rows=rows, query=query.replace('#', '\%23'),
                           fquery=filterquery, sort=sorting, json_facet=secrets.SOLR_PERSON_FACETS)
    if core == 'organisation':
        if sorting == '' or sorting == 'fdate desc':
            sorting = 'changed desc'
        # logging.info('SORT: %s' % sorting)
        search_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           core=core, handler=handler,  start=(page - 1) * rows, rows=rows, query=query.replace('#', '\%23'),
                           fquery=filterquery, sort=sorting, json_facet=secrets.SOLR_ORGA_FACETS)
    if core == 'group':
        if sorting == '' or sorting == 'fdate desc':
            sorting = 'changed desc'
        # logging.info('SORT: %s' % sorting)
        search_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                           core=core, handler=handler,  start=(page - 1) * rows, rows=rows, query=query.replace('#', '\%23'),
                           fquery=filterquery, sort=sorting, json_facet=secrets.SOLR_GROUP_FACETS)
    search_solr.request()
    num_found = search_solr.count()
    if num_found == 1:
        if core == 'hb2':
            return redirect(url_for('show_record', record_id=search_solr.results[0].get('id'),
                                    pubtype=search_solr.results[0].get('pubtype')))
        if core == 'person':
            return redirect(url_for('show_person', person_id=search_solr.results[0].get('id')))
        if core == 'organisation':
            return redirect(url_for('show_orga', orga_id=search_solr.results[0].get('id')))
        if core == 'group':
            return redirect(url_for('show_group', group_id=search_solr.results[0].get('id')))
    elif num_found == 0:
        flash('%s: %s' % (gettext('Your Search Found no Results'), query), 'error')
        return redirect(url_for('homepage'))
        # return render_template('search.html', header=lazy_gettext('Search'), site=theme(request.access_route))
    else:
        pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                                record_name=lazy_gettext('titles'), per_page=rows,
                                search_msg=lazy_gettext('Showing {start} to {end} of {found} {record_name}'))
        mystart = 1 + (pagination.page - 1) * pagination.per_page

        if not current_user.is_authenticated or current_user.role == 'user':

            if 'tudo:true' in filterquery:
                del filterquery[filterquery.index('tudo:true')]
            if 'rubi:true' in filterquery:
                del filterquery[filterquery.index('rubi:true')]
            if '-editorial_status:deleted' in filterquery:
                del filterquery[filterquery.index('-editorial_status:deleted')]

        if core == 'hb2':
            return render_template('resultlist.html', records=search_solr.results, pagination=pagination,
                                   facet_data=search_solr.facets, header=lazy_gettext('Resultlist'), target='search',
                                   core=core, site=theme(request.access_route), offset=mystart - 1, query=query,
                                   filterquery=filterquery,
                                   role_map=display_vocabularies.ROLE_MAP,
                                   lang_map=display_vocabularies.LANGUAGE_MAP,
                                   pubtype_map=display_vocabularies.PUBTYPE2TEXT,
                                   subtype_map=display_vocabularies.SUBTYPE2TEXT,
                                   license_map=display_vocabularies.LICENSE_MAP,
                                   frequency_map=display_vocabularies.FREQUENCY_MAP,
                                   pubstatus_map=display_vocabularies.PUB_STATUS,
                                   edt_status_map=display_vocabularies.EDT_STATUS,
                                   list=list)
        if core == 'person':
            return render_template('personlist.html', records=search_solr.results, pagination=pagination,
                                   facet_data=search_solr.facets, header=lazy_gettext('Resultlist'), target='search',
                                   core=core, site=theme(request.access_route), offset=mystart - 1, query=query,
                                   filterquery=filterquery,
                                   list=list)
        if core == 'organisation':
            return render_template('orgalist.html', records=search_solr.results, pagination=pagination,
                                   facet_data=search_solr.facets, header=lazy_gettext('Resultlist'), target='search',
                                   core=core, site=theme(request.access_route), offset=mystart - 1, query=query,
                                   filterquery=filterquery,
                                   list=list)
        if core == 'group':
            return render_template('grouplist.html', records=search_solr.results, pagination=pagination,
                                   facet_data=search_solr.facets, header=lazy_gettext('Resultlist'), target='search',
                                   core=core, site=theme(request.access_route), offset=mystart - 1, query=query,
                                   filterquery=filterquery,
                                   list=list)


@app.route('/search/external/gbv', methods=['GET'])
def search_gbv():

    ppn = request.args.get('ppn', '')
    isbns = request.args.get('isbns', '').split('|')
    query = request.args.get('q', '')
    # logging.info(ppn)
    # logging.info(isbns)
    # logging.info(query)
    format = request.args.get('format', '')
    locale = request.args.get('locale', 'eng')
    style = request.args.get('style', 'modern-language-association-with-url')

    thedata = []
    if ppn != '':
        # logging.info("SRU GBV QUERY PPN")
        mods = etree.parse(
            'http://sru.gbv.de/gvk?version=1.1&operation=searchRetrieve&query=%s=%s&maximumRecords=10&recordSchema=mods'
            % ('pica.ppn', ppn))
        # logging.info(etree.tostring(mods))
        item = mods_processor.mods2csl(mods)
        # logging.info(item.get('items')[0])
        thedata.append(item.get('items')[0])

        thedata = {'items': thedata}

    elif len(isbns) > 0 and isbns[0] != '':
        # logging.info("SRU GBV QUERY ISBN")
        for isbn in isbns:
            mods = etree.parse(
                'http://sru.gbv.de/gvk?version=1.1&operation=searchRetrieve&query=%s=%s&maximumRecords=10&recordSchema=mods'
                % ('pica.isb', isbn))
            # logging.info(etree.tostring(mods))
            item = mods_processor.mods2csl(mods)
            # logging.info(item.get('items'))
            if len(item.get('items')) > 0:
                thedata.append(item.get('items')[0])

        thedata = {'items': thedata}

    elif query != '':
        # logging.info("SRU GBV QUERY ALL")
        mods = etree.parse(
            'http://sru.gbv.de/gvk?version=1.1&operation=searchRetrieve&query=%s=%s&maximumRecords=10&recordSchema=mods'
            % ('pica.all', query))
        # logging.info(etree.tostring(mods))
        thedata = mods_processor.mods2csl(mods)
        # logging.info(thedata)

    if format == 'html':
        return render_bibliography(docs=thedata.get('items'), format=format, locale=locale, style=style,
                                   commit_link=True, commit_system='gbv')
    else:
        return jsonify(thedata)


@app.route('/search/external/crossref', methods=['GET'])
def search_crossref():
    doi = request.args.get('doi', '')
    query = request.args.get('q', '')
    format = request.args.get('format', '')
    locale = request.args.get('locale', 'eng')
    style = request.args.get('style', 'harvard1')

    thedata = []
    if doi != '':
        thedata = crossref_processor.crossref2csl(doi=doi)
        # TODO if thedata == []: datacite request
        if len(thedata.get('items')) == 0:
            thedata = datacite_processor.datacite2csl(doi=doi)

    elif query != '':
        thedata = crossref_processor.crossref2csl(query=query)

    if format == 'html':
        return render_bibliography(docs=thedata.get('items'), format=format, locale=locale, style=style,
                                   commit_link=True, commit_system='crossref')
    else:
        return jsonify(thedata)


@app.route('/retrieve/external/wos/<path:doi>')
def fetch_wos(doi):
    ISI_NS = 'http://www.isinet.com/xrpc42'
    ISI = '{%s}' % ISI_NS
    lamr = etree.parse('lamr.xml')
    map_node = etree.Element('map')
    val_node = etree.SubElement(map_node, 'val')
    val_node.attrib['name'] = 'doi'
    val_node.text = doi
    lamr.xpath('.//isi:map[3]', namespaces={'isi': ISI_NS})[0].append(val_node)
    logging.error(etree.tostring(lamr).decode('utf8'))
    return etree.fromstring(
        requests.post('https://ws.isiknowledge.com/cps/xrpc', data=etree.tostring(lamr, xml_declaration=True).decode('utf8'),
                      headers={'Content-Type': 'application/xml'}).text.encode('utf8'))


def _record2solr(form, action, relitems=True):

    solr_data = {}
    has_part = []
    is_part_of = []
    other_version = []
    id = ''
    is_rubi = False
    is_tudo = False

    # logging.info('FORM: %s' % form.data)

    if form.data.get('id'):
        solr_data.setdefault('id', form.data.get('id').strip())
        id = form.data.get('id').strip()

    for field in form.data:
        # logging.info('%s => %s' % (field, form.data.get(field)))
        # record information
        if field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    solr_data.setdefault('same_as', []).append(same_as.strip())
        if field == 'created':
            if len(form.data.get(field).strip()) == 10:
                solr_data.setdefault('recordCreationDate', '%sT00:00:00.001Z' % form.data.get(field).strip())
            else:
                solr_data.setdefault('recordCreationDate', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        if field == 'changed':
            if len(form.data.get(field).strip()) == 10:
                solr_data.setdefault('recordChangeDate', '%sT00:00:00.001Z' % form.data.get(field).strip())
            else:
                solr_data.setdefault('recordChangeDate', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        if field == 'owner':
            for owner in form.data.get(field):
                solr_data.setdefault('owner', []).append(owner.strip())
        if field == 'catalog':
            for catalog in form.data.get(field):
                solr_data.setdefault('catalog', []).append(catalog.strip())
        if field == 'deskman' and form.data.get(field):
            solr_data.setdefault('deskman', form.data.get(field).strip())
        if field == 'editorial_status':
            solr_data.setdefault('editorial_status', form.data.get(field).strip())
        if field == 'apparent_dup':
            solr_data.setdefault('apparent_dup', form.data.get(field))

        if field == 'affiliation_context':
            for context in form.data.get(field):
                # logging.info(context)
                if len(context) > 0:
                    try:
                        query = 'id:%s' % context

                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='organisation', query=query,
                                           facet='false', fields=['wtf_json'])
                        parent_solr.request()

                        if len(parent_solr.results) == 0:

                            query = 'account:%s' % context

                            parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, core='organisation', query=query,
                                               facet='false', fields=['wtf_json'])
                            parent_solr.request()

                            if len(parent_solr.results) == 0:

                                query = 'same_as:%s' % context

                                parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                   application=secrets.SOLR_APP, core='organisation', query=query,
                                                   facet='false', fields=['wtf_json'])
                                parent_solr.request()

                                if len(parent_solr.results) == 0:
                                    solr_data.setdefault('fakultaet', []).append(context)
                                    if current_user.role == 'admin' or current_user.role == 'superadmin':
                                        flash(
                                            gettext(
                                                'IDs from relation "affiliation" could not be found! Ref: %s' % context),
                                            'warning')
                                else:
                                    for doc in parent_solr.results:
                                        myjson = json.loads(doc.get('wtf_json'))
                                        solr_data.setdefault('fakultaet', []).append(
                                            '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                        solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
                                        for catalog in myjson.get('catalog'):
                                            if 'Bochum' in catalog:
                                                # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                                solr_data.setdefault('frubi_orga', []).append(
                                                    '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                                is_rubi = True
                                            if 'Dortmund' in catalog:
                                                solr_data.setdefault('ftudo_orga', []).append(
                                                    '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                                is_tudo = True
                            else:
                                for doc in parent_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    solr_data.setdefault('fakultaet', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
                                    for catalog in myjson.get('catalog'):
                                        if 'Bochum' in catalog:
                                            # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                            solr_data.setdefault('frubi_orga', []).append(
                                                '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                            is_rubi = True
                                        if 'Dortmund' in catalog:
                                            solr_data.setdefault('ftudo_orga', []).append(
                                                '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                            is_tudo = True
                        else:
                            for doc in parent_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                solr_data.setdefault('fakultaet', []).append('%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                        solr_data.setdefault('frubi_orga', []).append(
                                            '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        solr_data.setdefault('ftudo_orga', []).append(
                                            '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                        is_tudo = True

                    except AttributeError as e:
                        logging.error(e)

        if field == 'group_context':
            for context in form.data.get(field):
                # logging.info(context)
                if len(context) > 0:
                    try:
                        query = 'id:%s' % context
                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='group', query=query, facet='false',
                                           fields=['wtf_json'])
                        parent_solr.request()

                        if len(parent_solr.results) == 0:
                            query = 'same_as:%s' % context
                            parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, core='group', query=query, facet='false',
                                               fields=['wtf_json'])
                            parent_solr.request()

                            if len(parent_solr.results) == 0:
                                solr_data.setdefault('group', []).append(context)
                                if current_user.role == 'admin' or current_user.role == 'superadmin':
                                    flash(
                                        gettext(
                                            'IDs from relation "group" could not be found! Ref: %s' % context),
                                        'warning')
                            else:
                                for doc in parent_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    solr_data.setdefault('group_id', []).append(myjson.get('id'))
                                    solr_data.setdefault('group', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    for catalog in myjson.get('catalog'):
                                        if 'Bochum' in catalog:
                                            # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                            solr_data.setdefault('frubi_orga', []).append(
                                                '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                            is_rubi = True
                                        if 'Dortmund' in catalog:
                                            solr_data.setdefault('ftudo_orga', []).append(
                                                '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                            is_tudo = True
                        else:
                            for doc in parent_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                solr_data.setdefault('group_id', []).append(myjson.get('id'))
                                solr_data.setdefault('group', []).append('%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                        solr_data.setdefault('frubi_orga', []).append(
                                            '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        solr_data.setdefault('ftudo_orga', []).append(
                                            '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                        is_tudo = True
                    except AttributeError as e:
                        logging.error(e)

        if field == 'locked':
            solr_data.setdefault('locked', form.data.get(field))

        # the work
        if field == 'publication_status':
            solr_data.setdefault('publication_status', form.data.get(field).strip())
        if field == 'pubtype':
            solr_data.setdefault('pubtype', form.data.get(field).strip())
        if field == 'subtype':
            solr_data.setdefault('subtype', form.data.get(field).strip())
        if field == 'title':
            solr_data.setdefault('title', form.data.get(field).strip())
            solr_data.setdefault('exacttitle', form.data.get(field).strip())
            solr_data.setdefault('sorttitle', form.data.get(field).strip())
        if field == 'subtitle':
            solr_data.setdefault('subtitle', form.data.get(field).strip())
            solr_data.setdefault('other_title', form.data.get(field).strip())
        if field == 'title_supplement':
            solr_data.setdefault('other_title', form.data.get(field).strip())
        if field == 'other_title':
            for other_tit in form.data.get(field):
                # logging.info(other_tit)
                if other_tit.get('other_title'):
                    solr_data.setdefault('parallel_title', other_tit.get('other_title').strip())
                    solr_data.setdefault('other_title', other_tit.get('other_title').strip())
        if field == 'issued':
            if form.data.get(field):
                solr_data.setdefault('date', form.data.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', form.data.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'application_date':
            if form.data.get(field):
                solr_data.setdefault('date', form.data.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', form.data.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'priority_date':
            if form.data.get(field):
                solr_data.setdefault('date', form.data.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', form.data.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'publisher':
            solr_data.setdefault('publisher', form.data.get(field).strip())
            solr_data.setdefault('fpublisher', form.data.get(field).strip())
        if field == 'peer_reviewed':
            solr_data.setdefault('peer_reviewed', form.data.get(field))
        if field == 'language':
            for lang in form.data.get(field):
                solr_data.setdefault('language', []).append(lang)
        if field == 'person':
            # für alle personen
            for idx, person in enumerate(form.data.get(field)):
                # hat die person einen namen?
                if person.get('name'):
                    solr_data.setdefault('person', []).append(person.get('name').strip())
                    solr_data.setdefault('fperson', []).append(person.get('name').strip())
                    # hat die person eine gnd-id?
                    if person.get('gnd'):
                        # logging.info('drin: gnd: %s' % person.get('gnd'))
                        solr_data.setdefault('pnd', []).append(
                            '%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                        # prüfe, ob eine 'person' mit GND im System ist. Wenn ja, setze affiliation_context, wenn nicht
                        # schon belegt.
                        try:
                            query = 'id:%s' % person.get('gnd')
                            gnd_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                            application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                            fields=['wtf_json'])
                            gnd_solr.request()
                            if len(gnd_solr.results) == 0:
                                # logging.info('keine Treffer zu gnd: %s' % person.get('gnd'))
                                if current_user.role == 'admin' or current_user.role == 'superadmin':
                                    flash(
                                        gettext(
                                            'IDs from relation "person" could not be found! Ref: %s' % person.get('gnd')),
                                        'warning')
                            else:
                                # setze den parameter für die boolesche zugehörigkeit
                                myjson = json.loads(gnd_solr.results[0].get('wtf_json'))
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (person.get('name'), person.get('gnd')))
                                        form.person[idx].rubi.data = True
                                        solr_data.setdefault('frubi_pers', []).append('%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        form.person[idx].tudo.data = True
                                        solr_data.setdefault('ftudo_pers', []).append('%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                                        is_tudo = True
                                # details zur zugeörigkeit ermitteln
                                for idx1, doc in enumerate(gnd_solr.results):
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson)
                                    if myjson.get('affiliation') and len(myjson.get('affiliation')) > 0:
                                        for affiliation in myjson.get('affiliation'):
                                            affiliation_id = affiliation.get('organisation_id')
                                            # logging.info(affiliation_id)
                                            # füge affiliation_context dem wtf_json hinzu
                                            # TODO wollen wir das?
                                            # if affiliation_id not in form.data.get('affiliation_context'):
                                                # form.affiliation_context.append_entry(affiliation_id)
                        except AttributeError as e:
                            logging.error(e)
                    else:
                        # TODO versuche Daten aus dem'person'-Index zu holen (vgl. is_part_of oder has_part)
                        # die gndid muss dann aber auch dem 'wtf' hinzugefügt werden
                        solr_data.setdefault('pnd', []).append(
                            '%s#person-%s#%s' % (form.data.get('id'), idx, person.get('name').strip()))
        if field == 'corporation':
            for idx, corporation in enumerate(form.data.get(field)):
                if corporation.get('name'):
                    solr_data.setdefault('institution', []).append(corporation.get('name').strip())
                    solr_data.setdefault('fcorporation', []).append(corporation.get('name').strip())
                    # TODO reicht gnd hier aus? eher nein, oder?
                    if corporation.get('gnd'):
                        solr_data.setdefault('gkd', []).append(
                            '%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                        # prüfe, ob eine 'person' mit GND im System ist. Wenn ja, setze affiliation_context, wenn nicht
                        # schon belegt.
                        try:
                            query = 'id:%s' % corporation.get('gnd')
                            gnd_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, core='organisation', query=query, facet='false',
                                            fields=['wtf_json'])
                            gnd_solr.request()
                            if len(gnd_solr.results) == 0:
                                # logging.info('keine Treffer zu gnd: %s' % person.get('gnd'))
                                if current_user.role == 'admin' or current_user.role == 'superadmin':
                                    flash(
                                        gettext(
                                            'IDs from relation "corporation" could not be found! Ref: %s' % corporation.get('gnd')),
                                        'warning')
                            else:
                                # setze den parameter für die boolesche zugehörigkeit
                                myjson = json.loads(gnd_solr.results[0].get('wtf_json'))
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                        form.corporation[idx].rubi.data = True
                                        solr_data.setdefault('frubi_orga', []).append('%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        form.corporation[idx].tudo.data = True
                                        solr_data.setdefault('ftudo_orga', []).append('%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                                        is_tudo = True
                                # details zur zugeörigkeit ermitteln
                                for idx1, doc in enumerate(gnd_solr.results):
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson)
                                    if myjson.get('affiliation') and len(myjson.get('affiliation')) > 0:
                                        for affiliation in myjson.get('affiliation'):
                                            affiliation_id = affiliation.get('organisation_id')
                                            # logging.info(affiliation_id)
                                            # füge affiliation_context dem wtf_json hinzu
                                            if affiliation_id not in form.data.get('affiliation_context'):
                                                form.affiliation_context.append_entry(affiliation_id)
                        except AttributeError as e:
                            logging.error(e)
                    else:
                        solr_data.setdefault('gkd', []).append(
                            '%s#corporation-%s#%s' % (form.data.get('id'), idx, corporation.get('name').strip()))
                if corporation.get('role'):
                    if 'RadioTVProgram' in form.data.get('pubtype') and corporation.get('role')[0] == 'edt':
                        form.corporation[idx].role.data = 'brd'
                    if 'Thesis' in form.data.get('pubtype') and corporation.get('role')[0] == 'ctb':
                        form.corporation[idx].role.data = 'dgg'

        # content and subjects
        if field == 'abstract':
            for abstract in form.data.get(field):
                if abstract.get('sharable'):
                    solr_data.setdefault('abstract', []).append(abstract.get('content').strip())
                else:
                    solr_data.setdefault('ro_abstract', []).append(abstract.get('content').strip())
        if field == 'keyword':
            for keyword in form.data.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())
        if field == 'keyword_temporal':
            for keyword in form.data.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())
        if field == 'keyword_geographic':
            for keyword in form.data.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())
        if field == 'swd_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        if field == 'ddc_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('ddc', []).append(keyword.get('label').strip())
        if field == 'mesh_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('mesh_term', []).append(keyword.get('label').strip())
        if field == 'stw_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('stwterm_de', []).append(keyword.get('label').strip())
        if field == 'lcsh_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        if field == 'thesoz_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        # IDs
        if field == 'DOI':
            try:
                for doi in form.data.get(field):
                    solr_data.setdefault('doi', []).append(doi.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ISSN':
            try:
                for issn in form.data.get(field):
                    solr_data.setdefault('issn', []).append(issn.strip())
                    solr_data.setdefault('isxn', []).append(issn.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ZDBID':
            try:
                for zdbid in form.data.get(field):
                    solr_data.setdefault('zdbid', []).append(zdbid.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ISBN':
            try:
                for isbn in form.data.get(field):
                    solr_data.setdefault('isbn', []).append(isbn.strip())
                    solr_data.setdefault('isxn', []).append(isbn.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ISMN':
            try:
                for ismn in form.data.get(field):
                    solr_data.setdefault('ismn', []).append(ismn.strip())
                    solr_data.setdefault('isxn', []).append(ismn.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'PMID':
            solr_data.setdefault('pmid', form.data.get(field).strip())
        if field == 'WOSID':
            solr_data.setdefault('isi_id', form.data.get(field).strip())
        if field == 'orcid_put_code':
            solr_data.setdefault('orcid_put_code', form.data.get(field).strip())

        # funding
        if field == 'note':
            if 'funded by the Deutsche Forschungsgemeinschaft' in form.data.get(field):
                form.DFG.data = True
                solr_data.setdefault('dfg', form.data.get('DFG'))

        if field == 'DFG':
            solr_data.setdefault('dfg', form.data.get('DFG'))

        # related entities
        if field == 'event':
            for event in form.data.get(field):
                solr_data.setdefault('other_title', event.get('event_name').strip())
        if field == 'container_title':
            solr_data.setdefault('journal_title', form.data.get(field).strip())
            solr_data.setdefault('fjtitle', form.data.get(field).strip())

        if field == 'is_part_of' and len(form.data.get(field)) > 0:
            ipo_ids = []
            ipo_index = {}
            try:
                for idx, ipo in enumerate(form.data.get(field)):
                    if ipo:
                        # logging.info(ipo)
                        if 'is_part_of' in ipo:
                            # logging.info('POOP')
                            if ipo.get('is_part_of') != '':
                                ipo_ids.append(ipo.get('is_part_of').strip())
                                ipo_index.setdefault(ipo.get('is_part_of').strip(), idx)
                        else:
                            # logging.info('PEEP')
                            ipo_ids.append(ipo)
                            ipo_index.setdefault(ipo, idx)
                query = ''
                if len(ipo_ids) > 1:
                    query = '{!terms f=id}%s' % ','.join(ipo_ids)
                if len(ipo_ids) == 1:
                    query = 'id:%s' % ipo_ids[0]
                if len(ipo_ids) > 0:
                    ipo_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, query=query, rows=len(ipo_ids), facet='false',
                                    fields=['wtf_json'])
                    ipo_solr.request()
                    if len(ipo_solr.results) == 0:
                        if current_user.role == 'admin' or current_user.role == 'superadmin':
                            flash(gettext(
                                'Not all IDs from relation "is part of" could be found! Ref: %s' % form.data.get('id')),
                                'warning')
                    for doc in ipo_solr.results:
                        myjson = json.loads(doc.get('wtf_json'))
                        is_part_of.append(myjson.get('id'))
                        idx = ipo_index.get(myjson.get('id'))
                        title = myjson.get('title')
                        if myjson.get('subseries'):
                            title = '%s / %s' % (title, myjson.get('subseries'))
                        solr_data.setdefault('is_part_of_id', []).append(myjson.get('id'))
                        solr_data.setdefault('is_part_of', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                  'id': myjson.get('id'),
                                                                                  'title': title,
                                                                                  'issn': myjson.get('issn'),
                                                                                  'isbn': myjson.get('isbn'),
                                                                                  'page_first': form.data.get(field)[
                                                                                      idx].get('page_first', ''),
                                                                                  'page_last': form.data.get(field)[
                                                                                      idx].get('page_last', ''),
                                                                                  'volume': form.data.get(field)[
                                                                                      idx].get('volume', ''),
                                                                                  'issue': form.data.get(field)[
                                                                                      idx].get('issue', '')}))
            except AttributeError as e:
                logging.error(e)

        if field == 'has_part' and len(form.data.get(field)) > 0:

            hp_ids = []
            try:
                for idx, hp in enumerate(form.data.get(field)):
                    if hp:
                        if 'has_part' in hp:
                            if hp.get('has_part') != '':
                                hp_ids.append(hp.get('has_part').strip())
                        else:
                            # logging.info('PEEP')
                            hp_ids.append(hp)
                queries = []
                if len(hp_ids) == 1:
                    queries.append('id:%s' % hp_ids[0])
                if len(hp_ids) > 1:
                    query = '{!terms f=id}'
                    tmp = []
                    for hp_id in hp_ids:
                        if len(tmp) < 2:
                            tmp.append(hp_id)
                        elif len(query + ','.join(tmp) + ',' + hp_id) < 7168:
                            tmp.append(hp_id)
                        else:
                            queries.append('{!terms f=id}%s' % ','.join(tmp))
                            tmp = [hp_id]
                    if len(tmp) > 0:
                        queries.append('{!terms f=id}%s' % ','.join(tmp))
                if len(queries) > 0:
                    for query in queries:
                        hp_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, query=query, rows=len(hp_ids), facet='false',
                                       fields=['wtf_json'])
                        hp_solr.request()
                        if len(hp_solr.results) == 0:
                            if current_user.role == 'admin' or current_user.role == 'superadmin':
                                flash(
                                    gettext(
                                        'Not all IDs from relation "has part" could be found! Ref: %s' % form.data.get(
                                            'id')),
                                    'warning')
                        for doc in hp_solr.results:
                            myjson = json.loads(doc.get('wtf_json'))
                            has_part.append(myjson.get('id'))
                            # logging.debug('PARTS: myjson.get(\'is_part_of\') = %s' % myjson.get('is_part_of'))
                            if len(myjson.get('is_part_of')) > 0:
                                for host in myjson.get('is_part_of'):
                                    # logging.debug('PARTS: host = %s' % host)
                                    # logging.debug('PARTS: %s vs. %s' % (host.get('is_part_of'), id))
                                    if host.get('is_part_of') == id:
                                        solr_data.setdefault('has_part_id', []).append(myjson.get('id'))
                                        solr_data.setdefault('has_part', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                                'id': myjson.get('id'),
                                                                                                'title': myjson.get('title'),
                                                                                                'page_first': host.get('page_first', ''),
                                                                                                'page_last': host.get('page_last', ''),
                                                                                                'volume': host.get('volume', ''),
                                                                                                'issue': host.get('issue', '')}))
                            # logging.info(solr_data.get('has_part'))
            except AttributeError as e:
                logging.error('has_part: %s' % e)

        if field == 'other_version' and len(form.data.get(field)) > 0:
            # for myov in form.data.get(field):
            # logging.info('OV ' + myov)
            ov_ids = []
            try:
                for version in form.data.get(field):
                    if version.get('other_version') != '':
                        ov_ids.append(version.get('other_version'))
                query = ''
                if len(ov_ids) > 0:
                    query = '{!terms f=id}%s' % ','.join(ov_ids)
                if len(ov_ids) == 1:
                    query = 'id:%s' % ov_ids[0]
                if len(ov_ids) > 0:
                    ov_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, query=query, facet='false', fields=['wtf_json'])
                    ov_solr.request()
                    if len(ov_solr.results) == 0:
                        if current_user.role == 'admin' or current_user.role == 'superadmin':
                            flash(
                                gettext(
                                    'Not all IDs from relation "other version" could be found! Ref: %s' % form.data.get(
                                        'id')),
                                'warning')
                    for doc in ov_solr.results:
                        # logging.info(json.loads(doc.get('wtf_json')))
                        myjson = json.loads(doc.get('wtf_json'))
                        other_version.append(myjson.get('id'))
                        solr_data.setdefault('other_version_id', []).append(myjson.get('id'))
                        solr_data.setdefault('other_version', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                     'id': myjson.get('id'),
                                                                                     'title': myjson.get('title'),}))
            except AttributeError as e:
                logging.error(e)

    solr_data.setdefault('rubi', is_rubi)
    solr_data.setdefault('tudo', is_tudo)

    wtf_json = json.dumps(form.data).replace(' "', '"')
    solr_data.setdefault('wtf_json', wtf_json)

    csl_json = json.dumps(wtf_csl.wtf_csl(wtf_records=[json.loads(wtf_json)]))
    solr_data.setdefault('csl_json', csl_json)

    # TODO build openurl
    open_url = openurl_processor.wtf_openurl(json.loads(wtf_json))
    solr_data.setdefault('bibliographicCitation', open_url)

    record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2', data=[solr_data])
    record_solr.update()
    # reload all records listed in has_part, is_part_of, other_version
    # logging.debug('relitems = %s' % relitems)
    # logging.info('has_part: %s' % has_part)
    # logging.info('is_part_of: %s' % is_part_of)
    # logging.info('other_version: %s' % other_version)
    if relitems:
        for record_id in has_part:
            # lock record
            lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': record_id, 'locked': {'set': 'true'}}])
            lock_record_solr.update()
            # search record
            edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                    application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
            edit_record_solr.request()
            # load record in form and modify changeDate
            thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # add is_part_of to form if not exists
            exists = False
            if form.data.get('is_part_of'):
                for ipo in form.data.get('is_part_of'):
                    if ipo.get('is_part_of') == id:
                        exists = True
                        break
            if not exists:
                try:
                    is_part_of_form = IsPartOfForm()
                    is_part_of_form.is_part_of.data = id
                    form.is_part_of.append_entry(is_part_of_form.data)
                    form.changed.data = timestamp()
                    # save record
                    _record2solr(form, action='update', relitems=False)
                except AttributeError as e:
                    flash(gettext('ERROR linking from %s: %s' % (record_id, str(e))), 'error')
            else:
                # save record
                _record2solr(form, action='update', relitems=False)
            # unlock record
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()
        for record_id in is_part_of:
            # lock record
            lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': record_id, 'locked': {'set': 'true'}}])
            lock_record_solr.update()
            # search record
            edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                    application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
            edit_record_solr.request()
            # load record in form and modify changeDate
            thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
            # logging.info('is_part_of-Item: %s' % thedata)
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # add has_part to form
            exists = False
            if form.data.get('has_part'):
                for hpo in form.data.get('has_part'):
                    if hpo.get('has_part') == id:
                        exists = True
                        break
            if not exists:
                try:
                    has_part_form = HasPartForm()
                    has_part_form.has_part.data = id
                    form.has_part.append_entry(has_part_form.data)
                    form.changed.data = timestamp()
                    # save record
                    _record2solr(form, action='update', relitems=False)
                except AttributeError as e:
                    flash(gettext('ERROR linking from %s: %s' % (record_id, str(e))), 'error')
            else:
                # save record
                _record2solr(form, action='update', relitems=False)

            # unlock record
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()
        for record_id in other_version:
            # lock record
            lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': record_id, 'locked': {'set': 'true'}}])
            lock_record_solr.update()
            # search record
            edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                    application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
            edit_record_solr.request()
            # load record in form and modify changeDate
            thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # add is_part_of to form
            exists = False
            if form.data.get('other_version'):
                for ovo in form.data.get('other_version'):
                    if ovo.get('other_version') == id:
                        exists = True
                        break
            if not exists:
                try:
                    other_version_form = OtherVersionForm()
                    other_version_form.other_version.data = id
                    form.other_version.append_entry(other_version_form.data)
                    form.changed.data = timestamp()
                    # save record
                    _record2solr(form, action='update', relitems=False)
                except AttributeError as e:
                    flash(gettext('ERROR linking from %s: %s' % (record_id, str(e))), 'error')
            else:
                # save record
                _record2solr(form, action='update', relitems=False)
            # unlock record
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()


def _person2solr(form, action):
    tmp = {}

    if not form.data.get('editorial_status'):
        form.editorial_status.data = 'new'

    if not form.data.get('owner'):
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
    else:
        tmp.setdefault('owner', form.data.get('owner'))

    new_id = form.data.get('id')
    for field in form.data:
        if field == 'name':
            form.name.data = form.data.get(field).strip()
            tmp.setdefault('name', form.data.get(field).strip())
        elif field == 'also_known_as':
            for also_known_as in form.data.get(field):
                if len(also_known_as.strip()) > 0:
                    tmp.setdefault('also_known_as', []).append(str(also_known_as).strip())
        elif field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'gnd':
            if len(form.data.get(field).strip()) > 0:
                tmp.setdefault('gnd', form.data.get(field).strip())
                new_id = form.data.get(field).strip()
        elif field == 'dwid':
            tmp.setdefault('dwid', form.data.get(field))
            logging.info('%s vs. %s' % (form.data.get(field).strip(), form.data.get('gnd')))
            if len(form.data.get('gnd')) == 0 and len(form.data.get(field).strip()) > 0:
                new_id = form.data.get(field).strip().strip()
        elif field == 'email':
            tmp.setdefault('email', form.data.get(field))
        elif field == 'rubi':
            tmp.setdefault('rubi', form.data.get(field))
        elif field == 'tudo':
            tmp.setdefault('tudo', form.data.get(field))
        elif field == 'created':
            tmp.setdefault('created', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'status':
            for status in form.data.get(field):
                tmp.setdefault('personal_status', []).append(status.strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', form.data.get(field))
        elif field == 'deskman' and form.data.get(field):
            tmp.setdefault('deskman', form.data.get(field).strip())
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'research_interest':
            for research_interest in form.data.get(field):
                tmp.setdefault('research_interest', []).append(research_interest.strip())
        elif field == 'url':
            for url in form.data.get(field):
                tmp.setdefault('url', []).append(url.get('label').strip())
        elif field == 'membership':
            for membership in form.data.get(field):
                if membership.get('label'):
                    tmp.setdefault('membership', []).append(membership.get('label').strip())
        elif field == 'award':
            for award in form.data.get(field):
                if award.get('label'):
                    tmp.setdefault('award', []).append(award.get('label').strip())
        elif field == 'project':
            for project in form.data.get(field):
                if project.get('label'):
                    tmp.setdefault('project', []).append(project.get('label').strip())
                if project.get('project_id') and project.get('label'):
                    tmp.setdefault('project_id', []).append(
                        '%s#%s' % (project.get('project_id').strip(), project.get('label').strip()))
                if project.get('project_type'):
                    tmp.setdefault('project_type', []).append(project.get('project_type'))
        elif field == 'thesis':
            for thesis in form.data.get(field):
                if thesis.get('label'):
                    tmp.setdefault('thesis', []).append(thesis.get('label').strip())
        elif field == 'cv':
            for cv in form.data.get(field):
                if cv.get('label'):
                    tmp.setdefault('cv', []).append(cv.get('label').strip())
        elif field == 'editor':
            for editor in form.data.get(field):
                if editor.get('label'):
                    tmp.setdefault('editor', []).append(editor.get('label').strip())
                if editor.get('issn'):
                    tmp.setdefault('editor_issn', []).append(editor.get('issn'))
                if editor.get('zdbid'):
                    tmp.setdefault('editor_zdbid', []).append(editor.get('zdbid'))
        elif field == 'reviewer':
            for reviewer in form.data.get(field):
                if reviewer.get('label'):
                    tmp.setdefault('reviewer', []).append(reviewer.get('label').strip())
                if reviewer.get('issn'):
                    tmp.setdefault('reviewer_issn', []).append(reviewer.get('issn'))
                if reviewer.get('zdbid'):
                    tmp.setdefault('reviewer_zdbid', []).append(reviewer.get('zdbid'))
        elif field == 'data_supplied':
            if form.data.get(field).strip() != "":
                tmp.setdefault('data_supplied', '%sT00:00:00.001Z' % form.data.get(field).strip())

        elif field == 'affiliation':
            for idx, affiliation in enumerate(form.data.get(field)):
                if affiliation.get('organisation_id'):
                    tmp.setdefault('affiliation_id', affiliation.get('organisation_id'))
                    try:
                        query = 'id:%s' % affiliation.get('organisation_id')
                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='organisation', query=query,
                                           facet='false', fields=['wtf_json'])
                        parent_solr.request()
                        if len(parent_solr.results) == 0:
                            query = 'account:%s' % affiliation.get('organisation_id')
                            parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, core='organisation', query=query,
                                               facet='false', fields=['wtf_json'])
                            parent_solr.request()
                            if len(parent_solr.results) == 0:
                                query = 'same_as:%s' % affiliation.get('organisation_id')
                                parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                   application=secrets.SOLR_APP, core='organisation', query=query,
                                                   facet='false', fields=['wtf_json'])
                                parent_solr.request()
                                if len(parent_solr.results) == 0:
                                    flash(
                                        gettext(
                                            'IDs from relation "organisation_id" could not be found! Ref: %s' % affiliation.get(
                                                'organisation_id')),
                                        'warning')
                                else:
                                    for doc in parent_solr.results:
                                        myjson = json.loads(doc.get('wtf_json'))
                                        # logging.info(myjson.get('pref_label'))
                                        label = myjson.get('pref_label').strip()
                                        form.affiliation[idx].pref_label.data = label
                                        tmp.setdefault('affiliation', []).append(label)
                                        tmp.setdefault('faffiliation', []).append(label)
                            else:
                                for doc in parent_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson.get('pref_label'))
                                    label = myjson.get('pref_label').strip()
                                    form.affiliation[idx].pref_label.data = label
                                    tmp.setdefault('affiliation', []).append(label)
                                    tmp.setdefault('faffiliation', []).append(label)
                        else:
                            for doc in parent_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                # logging.info(myjson.get('pref_label'))
                                label = myjson.get('pref_label').strip()
                                form.affiliation[idx].pref_label.data = label
                                tmp.setdefault('affiliation', []).append(label)
                                tmp.setdefault('faffiliation', []).append(label)
                    except AttributeError as e:
                        logging.error(e)
                elif affiliation.get('pref_label'):
                    tmp.setdefault('affiliation', []).append(affiliation.get('pref_label').strip())
                    tmp.setdefault('faffiliation', []).append(affiliation.get('pref_label').strip())

        elif field == 'group':
            for idx, group in enumerate(form.data.get(field)):
                if group.get('group_id'):
                    tmp.setdefault('group_id', group.get('group_id'))
                    try:
                        query = 'id:%s' % group.get('group_id')
                        group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                          application=secrets.SOLR_APP, core='group', query=query, facet='false',
                                          fields=['wtf_json'])
                        group_solr.request()
                        if len(group_solr.results) == 0:
                            query = 'same_as:%s' % group.get('group_id')
                            group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                              application=secrets.SOLR_APP, core='group', query=query,
                                              facet='false', fields=['wtf_json'])
                            group_solr.request()
                            if len(group_solr.results) == 0:
                                flash(
                                    gettext(
                                        'IDs from relation "group_id" could not be found! Ref: %s' % group.get(
                                            'group_id')),
                                    'warning')
                            else:
                                for doc in group_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson.get('pref_label'))
                                    label = myjson.get('pref_label').strip()
                                    form.affiliation[idx].pref_label.data = label
                                    tmp.setdefault('group', []).append(label)
                                    tmp.setdefault('fgroup', []).append(label)
                        else:
                            for doc in group_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                # logging.info(myjson.get('pref_label'))
                                label = myjson.get('pref_label').strip()
                                form.group[idx].pref_label.data = label
                                tmp.setdefault('group', []).append(label)
                                tmp.setdefault('fgroup', []).append(label)
                    except AttributeError as e:
                        logging.error(e)
                elif group.get('pref_label'):
                    tmp.setdefault('group', []).append(group.get('pref_label').strip())
                    tmp.setdefault('fgroup', []).append(group.get('pref_label').strip())

    doit = False
    if action == 'create':
        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='person', query='id:%s' % new_id,
                           facet='false', fields=['wtf_json'])
        person_solr.request()
        if len(person_solr.results) == 0:
            doit = True
    else:
        doit = True

    # logging.info('new_id: %s for %s' % (new_id, form.data.get('id')))
    # logging.info('doit: %s for %s' % (doit, form.data.get('id')))

    if doit:
        if new_id != form.data.get('id'):
            form.same_as.append_entry(form.data.get('id'))
            tmp.setdefault('same_as', []).append(form.data.get('id'))
            # delete record with current id
            try:
                delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                          application=secrets.SOLR_APP, core='person', del_id=form.data.get('id'))
                delete_person_solr.delete()
            except AttributeError as e:
                logging.error(e)
            form.id.data = new_id
        tmp.setdefault('id', new_id)
        wtf_json = json.dumps(form.data)
        tmp.setdefault('wtf_json', wtf_json)
        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='person', data=[tmp])
        person_solr.update()

    return doit, new_id


def _orga2solr(form, action, relitems=True):
    tmp = {}
    parents = []
    children = []
    projects = []

    id = form.data.get('id').strip()
    logging.info('ID: %s' % id)
    dwid = form.data.get('dwid')
    logging.info('DWID: %s' % dwid)

    if not form.data.get('editorial_status'):
        form.editorial_status.data = 'new'

    if not form.data.get('owner'):
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
    else:
        tmp.setdefault('owner', form.data.get('owner'))

    for field in form.data:
        if field == 'orga_id':
            tmp.setdefault('orga_id', form.data.get(field))
        elif field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'pref_label':
            tmp.setdefault('pref_label', form.data.get(field).strip())
        elif field == 'alt_label':
            for alt_label in form.data.get(field):
                tmp.setdefault('alt_label', []).append(alt_label.strip())
        elif field == 'dwid':
            for account in form.data.get(field):
                tmp.setdefault('account', []).append(account.strip())
            if len(form.data.get('gnd')) == 0 and len(form.data.get(field)[0].strip()) > 0:
                form.id.data = form.data.get(field)[0].strip()
        elif field == 'gnd':
            if len(form.data.get(field)) > 0:
                tmp.setdefault('gnd', form.data.get(field).strip())
                form.id.data = form.data.get(field).strip()
        elif field == 'created':
            tmp.setdefault('created', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'deskman' and form.data.get(field):
            tmp.setdefault('deskman', form.data.get(field).strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', form.data.get(field))
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'destatis':
            for destatis in form.data.get(field):
                if destatis.get('destatis_label'):
                    tmp.setdefault('destatis_label', []).append(destatis.get('destatis_label').strip())
                if destatis.get('destatis_id'):
                    tmp.setdefault('destatis_id', []).append(destatis.get('destatis_id').strip())

        elif field == 'parent':
            parent = form.data.get(field)[0]
            # logging.info('parent: %s' % parent)
            if parent.get('parent_id'):
                # remember ID for work on related entity
                parents.append(parent.get('parent_id'))
                # prepare index data and enrich form data
                tmp.setdefault('parent_id', parent.get('parent_id'))
                try:
                    query = 'id:%s' % parent.get('parent_id')
                    parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='organisation', query=query,
                                       facet='false',
                                       fields=['wtf_json'])
                    parent_solr.request()
                    # logging.info('Treffer für %s: %s' % (parent.get('id'), len(parent_solr.results)))
                    if len(parent_solr.results) == 0:
                        flash(
                        gettext(
                            'IDs from relation "parent" could not be found! Ref: %s' % parent.get('parent_id')),
                        'warning')
                    else:
                        for doc in parent_solr.results:
                            myjson = json.loads(doc.get('wtf_json'))
                            label = myjson.get('pref_label').strinp()
                            tmp.setdefault('parent_label', label)
                            tmp.setdefault('fparent', '%s#%s' % (myjson.get('id').strip(), label))
                            form.parent[0].parent_label.data = label
                except AttributeError as e:
                    logging.error('ORGA: parent_id=%s: %s' % (parent.get('parent_id'), e))
            elif parent.get('parent_label') and len(parent.get('parent_label')) > 0:
                tmp.setdefault('fparent', parent.get('parent_label'))
                tmp.setdefault('parent_label', parent.get('parent_label'))

        elif field == 'children':
            # logging.info('children in form of %s : %s' % (id, form.data.get(field)))
            for idx, child in enumerate(form.data.get(field)):
                if child:
                    if 'child_id' in child and 'child_label' in child:
                        if child.get('child_id'):
                            # remember ID for work on related entity
                            children.append(child.get('child_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % child.get('child_id')
                                child_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                  application=secrets.SOLR_APP, core='organisation',
                                                  query=query,
                                                  facet='false', fields=['wtf_json'])
                                child_solr.request()
                                if len(child_solr.results) > 0:
                                    for doc in child_solr.results:
                                        myjson = json.loads(doc.get('wtf_json'))
                                        label = myjson.get('pref_label').strip()
                                        form.children[idx].child_label.data = label
                                        tmp.setdefault('children', []).append(
                                            json.dumps({'id': myjson.get('id').strip(),
                                                        'label': label,
                                                        'type': 'organisation'}))
                                        tmp.setdefault('fchildren', []).append(
                                            '%s#%s' % (myjson.get('id').strip(), label))
                                else:
                                    child_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                      application=secrets.SOLR_APP, core='group',
                                                      query=query,
                                                      facet='false', fields=['wtf_json'])
                                    child_solr.request()
                                    if len(child_solr.results) > 0:
                                        for doc in child_solr.results:
                                            myjson = json.loads(doc.get('wtf_json'))
                                            label = myjson.get('pref_label').strip()
                                            form.children[idx].child_label.data = label
                                            tmp.setdefault('children', []).append(json.dumps({'id': myjson.get('id').strip(),
                                                                                              'label': label,
                                                                                              'type': 'group'}))
                                            tmp.setdefault('fchildren', []).append(
                                                '%s#%s' % (myjson.get('id').strip(), label))

                                    else:
                                        flash(
                                            gettext(
                                                'IDs from relation "child" could not be found! Ref: %s' % child.get(
                                                    'child_id')),
                                            'warning')

                            except AttributeError as e:
                                logging.error('ORGA: child_id=%s: %s' % (child.get('child_id'), e))
                        elif child.get('child_label'):
                            tmp.setdefault('children', []).append(json.dumps({'id': '',
                                                                              'label': child.get('child_label').strip(),
                                                                              'type': ''}))
                            tmp.setdefault('fchildren', []).append(child.get('child_label').strip())

        elif field == 'projects':
            # logging.info('projects in form of %s : %s' % (id, form.data.get(field)))
            for idx, project in enumerate(form.data.get(field)):
                if project:
                    if 'project_id' in project and 'project_label' in project:
                        if project.get('project_id'):
                            # remember ID for work on related entity
                            projects.append(project.get('project_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % project.get('project_id')
                                project_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                    application=secrets.SOLR_APP, core='group', query=query,
                                                    facet='false', fields=['wtf_json'])
                                project_solr.request()
                                if len(project_solr.results) == 0:
                                    flash(
                                        gettext(
                                            'IDs from relation "projects" could not be found! Ref: %s' % project.get('project_id')),
                                        'warning')
                                for doc in project_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    form.projects[idx].project_label.data = label
                                    tmp.setdefault('projects', []).append(json.dumps({'id': myjson.get('id').strip(),
                                                                                      'label': label}))
                                    tmp.setdefault('fprojects', []).append('%s#%s' % (myjson.get('id').strip(), label))

                            except AttributeError as e:
                                logging.error('GROUP: project_id=%s: %s' % (project.get('project_id'), e))
                        elif project.get('project_label'):
                            tmp.setdefault('fprojects', []).append(project.get('project_label').strip())

    # search record
    search_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='organisation', rows=1000, query='parent_id:%s' % id)
    search_orga_solr.request()
    if len(search_orga_solr.results) > 0:
        children = form.data.get('children')
        for result in search_orga_solr.results:
            exists = False
            for project in children:
                logging.info('%s vs. %s' % (project.get('child_id'), result.get('id')))
                if project.get('child_id') == result.get('id'):
                    exists = True
                    break
            if not exists:
                childform = ChildForm()
                childform.child_id.data = result.get('id')
                childform.child_label.data = result.get('pref_label')
                form.children.append_entry(childform.data)

    # save record to index
    try:
        # logging.info('%s vs. %s' % (id, form.data.get('id')))
        if id != form.data.get('id'):
            delete_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='organisation', del_id=id)
            delete_orga_solr.delete()
            form.same_as.append_entry(id)
            tmp.setdefault('id', form.data.get('id'))
            tmp.setdefault('same_as', []).append(id)

            id = form.data.get('id')
        else:
            tmp.setdefault('id', id)
        # build json
        wtf_json = json.dumps(form.data)
        tmp.setdefault('wtf_json', wtf_json)
        # logging.info(tmp)
        orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                         application=secrets.SOLR_APP, core='organisation', data=[tmp])
        orga_solr.update()
    except AttributeError as e:
        logging.error(e)

    same_as = form.data.get('same_as')
    # logging.info('same_as: %s' % same_as)

    # add link to parent
    if relitems:
        # logging.info('parents: %s' % parents)
        for parent_id in parents:
            # search record
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query='id:%s' % parent_id)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': parent_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add child to form if not exists
                    exists = False
                    for project in form.data.get('children'):
                        # logging.info('%s == %s ?' % (project.get('child_id'), id))
                        if project.get('child_id'):
                            if project.get('child_id') == id:
                                exists = True
                                break
                            elif project.get('child_id') in dwid:
                                exists = True
                                break
                            elif project.get('child_id') in same_as:
                                exists = True
                                break
                    if not exists:
                        try:
                            childform = ChildForm()
                            childform.child_id.data = id
                            form.children.append_entry(childform.data)
                            form.changed.data = timestamp()
                            # save record
                            _orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (parent_id, str(e))), 'error')
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        _orga2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedate: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': parent_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                logging.info('Currently there is no record for parent_id %s!' % parent_id)

        # logging.info('children: %s' % children)
        for child_id in children:
            # search record
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query='id:%s' % child_id)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': child_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add parent to form if not exists
                    if not form.data.get('parent'):
                        try:
                            parentform = ParentForm()
                            parentform.parent_id = id
                            form.parent.append_entry(parentform.data)
                            form.changed.data = timestamp()
                            # save record
                            _orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (child_id, str(e))), 'error')
                    else:
                        try:
                            form.parent[0].parent_id = id
                            form.changed.data = timestamp()
                            # save record
                            _orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (child_id, str(e))), 'error')
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedate: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': child_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                edit_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group', query='id:%s' % child_id)
                edit_group_solr.request()
                # load orga in form and modify changeDate
                if len(edit_group_solr.results) > 0:
                    # lock record
                    lock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='group',
                                           data=[{'id': child_id, 'locked': {'set': 'true'}}])
                    lock_group_solr.update()
                    # edit
                    try:
                        thedata = json.loads(edit_group_solr.results[0].get('wtf_json'))
                        form = GroupAdminForm.from_json(thedata)
                        # add parent to form if not exists
                        if not form.data.get('parent'):
                            try:
                                parentform = ParentForm()
                                parentform.parent_id = id
                                form.parent.append_entry(parentform.data)
                                form.changed.data = timestamp()
                                # save record
                                _group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                flash(gettext('ERROR linking from %s: %s' % (child_id, str(e))), 'error')
                        else:
                            try:
                                form.parent[0].parent_id = id
                                form.changed.data = timestamp()
                                # save record
                                _group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                flash(gettext('ERROR linking from %s: %s' % (child_id, str(e))), 'error')
                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedate: %s' % edit_group_solr.results[0].get('wtf_json'))
                    # unlock record
                    unlock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                             application=secrets.SOLR_APP, core='group',
                                             data=[{'id': child_id, 'locked': {'set': 'false'}}])
                    unlock_group_solr.update()

                else:
                    logging.info('Currently there is no record for child_id %s!' % child_id)

        # logging.debug('partners: %s' % partners)
        for project_id in projects:
            # search record
            query = 'id:%s' % project_id
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='group', query=query)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='group',
                                      data=[{'id': project_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = GroupAdminForm.from_json(thedata)
                    # add project to form if not exists
                    exists = False
                    for partner in form.data.get('partners'):
                        # logging.info('%s == %s ?' % (project.get('project_id'), id))
                        if partner.get('partner_id'):
                            if partner.get('partner_id') == id:
                                exists = True
                                break
                            elif partner.get('partner_id') in same_as:
                                exists = True
                                break
                    # logging.debug('exists? %s' % exists)
                    if not exists:
                        try:
                            partnerform = PartnerForm()
                            partnerform.partner_id.data = id
                            form.partners.append_entry(partnerform.data)
                            form.changed.data = timestamp()
                            # save record
                            _group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (project_id, str(e))), 'error')
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        _group2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='group',
                                        data=[{'id': project_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                logging.info('Currently there is no record for project_id %s!' % project_id)

        # store work records again
        works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, core='hb2',
                          query='affiliation_id:%s' % id, facet=False, rows=500000)
        works_solr.request()

        for work in works_solr.results:
            # lock record
            lock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='hb2',
                                  data=[{'id': work.get('id'), 'locked': {'set': 'true'}}])
            lock_work_solr.update()

            # edit
            try:
                thedata = json.loads(work.get('wtf_json'))
                form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                form.changed.data = timestamp()
                _record2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % work.get('wtf_json'))

            # unlock record
            unlock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': work.get('id'), 'locked': {'set': 'false'}}])
            unlock_work_solr.update()

        # store person records again
        persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='person',
                            query='affiliation_id:%s' % id, facet=False, rows=500000)
        persons_solr.request()

        for person in persons_solr.results:
            # lock record
            lock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    data=[{'id': person.get('id'), 'locked': {'set': 'true'}}])
            lock_person_solr.update()

            # edit
            try:
                thedata = json.loads(person.get('wtf_json'))
                form = PersonAdminForm.from_json(thedata)
                form.changed.data = timestamp()
                _person2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % person.get('wtf_json'))

            # unlock record
            unlock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='person',
                                      data=[{'id': person.get('id'), 'locked': {'set': 'false'}}])
            unlock_person_solr.update()

    return id


def _group2solr(form, action, relitems=True):
    tmp = {}
    parents = []
    children = []
    partners = []

    id = form.data.get('id').strip()
    logging.info('ID: %s' % id)

    if not form.data.get('editorial_status'):
        form.editorial_status.data = 'new'

    if action == 'update':
        if form.data.get('editorial_status') == 'new':
            form.editorial_status.data = 'in_process'

    if not form.data.get('owner'):
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
    else:
        tmp.setdefault('owner', form.data.get('owner'))

    for field in form.data:
        if field == 'id':
            tmp.setdefault('id', form.data.get(field))
        elif field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'funds':
            for funder in form.data.get(field):
                if len(funder.get('organisation').strip()) > 0:
                    tmp.setdefault('funder_id', []).append(funder.get('organisation_id').strip())
                    tmp.setdefault('funder', []).append(funder.get('organisation').strip())
                    tmp.setdefault('ffunder', []).append(funder.get('organisation').strip())
        elif field == 'pref_label':
            tmp.setdefault('pref_label', form.data.get(field).strip())
        elif field == 'alt_label':
            for alt_label in form.data.get(field):
                tmp.setdefault('alt_label', []).append(alt_label.data.strip())
        elif field == 'dwid':
            tmp.setdefault('account', form.data.get(field))
        elif field == 'gnd':
            if len(form.data.get(field)) > 0:
                tmp.setdefault('gnd', form.data.get(field).strip())
                form.id.data = form.data.get(field).strip()
        elif field == 'created':
            tmp.setdefault('created', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'deskman' and form.data.get(field):
            tmp.setdefault('deskman', form.data.get(field).strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', form.data.get(field))
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'destatis':
            for destatis in form.data.get(field):
                if destatis.get('destatis_label'):
                    tmp.setdefault('destatis_label', []).append(destatis.get('destatis_label').strip())
                if destatis.get('destatis_id'):
                    tmp.setdefault('destatis_id', []).append(destatis.get('destatis_id').strip())

        elif field == 'parent':
            parent = form.data.get(field)[0]
            # logging.info('parent: %s' % parent)
            if parent.get('parent_id'):
                # remember ID for work on related entity
                parents.append(parent.get('parent_id'))
                # prepare index data and enrich form data
                tmp.setdefault('parent_id', parent.get('parent_id'))
                try:
                    query = 'id:%s' % parent.get('parent_id')
                    parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group', query=query,
                                       facet='false',
                                       fields=['wtf_json'])
                    parent_solr.request()
                    # logging.info('Treffer für %s: %s' % (parent.get('id'), len(parent_solr.results)))
                    results = []
                    type = ''
                    if len(parent_solr.results) == 0:

                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='organisation', query=query,
                                           facet='false',
                                           fields=['wtf_json'])
                        parent_solr.request()

                        if len(parent_solr.results) == 0:
                            flash(
                                gettext(
                                    'IDs from relation "parent" could not be found! Ref: %s' % parent.get('parent_id')),
                                'warning')
                        else:
                            results = parent_solr.results
                            type = 'organisation'
                    else:
                        results = parent_solr.results
                        type = 'group'

                    if results:
                        for doc in parent_solr.results:
                            myjson = json.loads(doc.get('wtf_json'))
                            tmp.setdefault('parent_type', type)
                            tmp.setdefault('parent_label', myjson.get('pref_label'))
                            tmp.setdefault('fparent', '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                            form.parent[0].parent_label.data = myjson.get('pref_label')

                except AttributeError as e:
                    logging.error('GROUP: parent_id=%s: %s' % (parent.get('parent_id'), e))
            elif parent.get('parent_label'):
                tmp.setdefault('fparent', parent.get('parent_label'))
                tmp.setdefault('parent_label', parent.get('parent_label'))

        elif field == 'children':
            # logging.info('children in form of %s : %s' % (id, form.data.get(field)))
            for idx, child in enumerate(form.data.get(field)):
                if child:
                    if 'child_id' in child and 'child_label' in child:
                        if child.get('child_id'):
                            # remember ID for work on related entity
                            children.append(child.get('child_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % child.get('child_id')
                                child_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                  application=secrets.SOLR_APP, core='group',
                                                  query=query,
                                                  facet='false', fields=['wtf_json'])
                                child_solr.request()
                                if len(child_solr.results) == 0:
                                    flash(
                                        gettext(
                                            'IDs from relation "child" could not be found! Ref: %s' % child.get(
                                                'child_id')),
                                        'warning')
                                for doc in child_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    form.children[idx].child_label.data = label
                                    tmp.setdefault('children', []).append(json.dumps({'id': myjson.get('id'),
                                                                                      'label': label}))
                                    tmp.setdefault('fchildren', []).append('%s#%s' % (myjson.get('id'), label))
                            except AttributeError as e:
                                logging.error('GROUP: child_id=%s: %s' % (child.get('child_id'), e))
                        elif child.get('child_label'):
                            tmp.setdefault('children', []).append(child.get('child_label'))
                            tmp.setdefault('fchildren', []).append(child.get('child_label'))

        elif field == 'partners':
            # logging.info('partners in form of %s : %s' % (id, form.data.get(field)))
            for idx, partner in enumerate(form.data.get(field)):
                if partner:
                    if 'partner_id' in partner and 'partner_label' in partner:
                        if partner.get('partner_id'):
                            # remember ID for work on related entity
                            partners.append(partner.get('partner_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % partner.get('partner_id')
                                partner_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                    application=secrets.SOLR_APP, core='organisation', query=query,
                                                    facet='false', fields=['wtf_json'])
                                partner_solr.request()
                                # TODO same_as
                                if len(partner_solr.results) == 0:
                                    flash(
                                        gettext(
                                            'IDs from relation "partners" could not be found! Ref: %s' % partner.get('partner_id')),
                                        'warning')
                                for doc in partner_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    form.partners[idx].partner_label.data = label
                                    tmp.setdefault('partners', []).append(json.dumps({'id': myjson.get('id'),
                                                                                      'label': label}))
                                    tmp.setdefault('fpartners', []).append('%s#%s' % (myjson.get('id'), label))
                            except AttributeError as e:
                                logging.error('ORGA: partner_id=%s: %s' % (partner.get('partner_id'), e))
                        elif partner.get('partner_label'):
                            tmp.setdefault('partners', []).append(partner.get('partner_label'))
                            tmp.setdefault('fpartners', []).append(partner.get('partner_label'))

    # save record to index
    try:
        logging.info('%s vs. %s' % (id, form.data.get('id')))
        if id != form.data.get('id'):
            delete_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                     application=secrets.SOLR_APP, core='group', del_id=id)
            delete_group_solr.delete()
            form.same_as.append_entry(id)
            tmp.setdefault('id', form.data.get('id'))
            tmp.setdefault('same_as', []).append(id)

            id = form.data.get('id')
        else:
            tmp.setdefault('id', id)
        # build json
        wtf_json = json.dumps(form.data)
        tmp.setdefault('wtf_json', wtf_json)
        # logging.info(tmp)
        groups_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='group', data=[tmp])
        groups_solr.update()
    except AttributeError as e:
        logging.error(e)

    same_as = form.data.get('same_as')
    # logging.info('same_as: %s' % same_as)

    # add links to related entities
    if relitems:
        # logging.debug('parents: %s' % parents)
        for parent_id in parents:
            # search record
            query = 'id:%s' % parent_id
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query=query)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': parent_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add child to form if not exists
                    exists = False
                    for child in form.data.get('children'):
                        # logging.info('%s == %s ?' % (child.get('child_id'), id))
                        if child.get('child_id') == id:
                            exists = True
                            break
                        elif child.get('child_id') in same_as:
                            exists = True
                            break
                    if not exists:
                        try:
                            childform = ChildForm()
                            childform.child_id.data = id
                            form.children.append_entry(childform.data)
                            form.changed.data = timestamp()
                            # save record
                            _orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (parent_id, str(e))), 'error')
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        _orga2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': parent_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                edit_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group', query=query)
                edit_group_solr.request()
                # load group in form and modify changeDate
                if len(edit_group_solr.results) > 0:
                    # lock record
                    lock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='group',
                                           data=[{'id': parent_id, 'locked': {'set': 'true'}}])
                    lock_group_solr.update()
                    # edit
                    try:
                        thedata = json.loads(edit_group_solr.results[0].get('wtf_json'))
                        form = GroupAdminForm.from_json(thedata)
                        # add child to form if not exists
                        exists = False
                        for child in form.data.get('children'):
                            # logging.info('%s == %s ?' % (child.get('child_id'), id))
                            if child.get('child_id') == id:
                                exists = True
                                break
                            elif child.get('child_id') in same_as:
                                exists = True
                                break
                        if not exists:
                            try:
                                childform = ChildForm()
                                childform.child_id.data = id
                                form.children.append_entry(childform.data)
                                form.changed.data = timestamp()
                                # save record
                                _group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                flash(gettext('ERROR linking from %s: %s' % (parent_id, str(e))), 'error')
                        else:
                            # possibly rewrite label
                            form.changed.data = timestamp()
                            _group2solr(form, action='update', relitems=False)
                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % edit_group_solr.results[0].get('wtf_json'))
                    # unlock record
                    unlock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                             application=secrets.SOLR_APP, core='group',
                                             data=[{'id': parent_id, 'locked': {'set': 'false'}}])
                    unlock_group_solr.update()
                else:
                    logging.info('Currently there is no record for parent_id %s!' % parent_id)

        # logging.debug('children: %s' % children)
        for child_id in children:
            # search record
            edit_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, core='group', query='id:%s' % child_id)
            edit_group_solr.request()
            # load orga in form and modify changeDate
            if len(edit_group_solr.results) > 0:
                # lock record
                lock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group',
                                       data=[{'id': child_id, 'locked': {'set': 'true'}}])
                lock_group_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_group_solr.results[0].get('wtf_json'))
                    form = GroupAdminForm.from_json(thedata)
                    # add parent to form if not exists
                    if not form.data.get('parent'):
                        try:
                            parentform = ParentForm()
                            parentform.parent_id = id
                            form.parent.append_entry(parentform.data)
                            form.changed.data = timestamp()
                            # save record
                            _group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (parent_id, str(e))), 'error')
                    else:
                        try:
                            form.parent[0].parent_id = id
                            form.changed.data = timestamp()
                            # save record
                            _group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (parent_id, str(e))), 'error')
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_group_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                         application=secrets.SOLR_APP, core='group',
                                         data=[{'id': child_id, 'locked': {'set': 'false'}}])
                unlock_group_solr.update()
            else:
                logging.info('Currently there is no record for parent_id %s!' % parent_id)

        # logging.debug('partners: %s' % partners)
        for partner_id in partners:
            # search record
            query = 'id:%s' % partner_id
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query=query)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': partner_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add project to form if not exists
                    exists = False
                    for project in form.data.get('projects'):
                        # logging.info('%s == %s ?' % (project.get('project_id'), id))
                        if project.get('project_id'):
                            if project.get('project_id') == id:
                                exists = True
                                break
                            elif project.get('project_id') in same_as:
                                exists = True
                                break
                    # logging.debug('exists? %s' % exists)
                    if not exists:
                        try:
                            projectmemberform = ProjectMemberForm()
                            projectmemberform.project_id.data = id
                            form.projects.append_entry(projectmemberform.data)
                            form.changed.data = timestamp()
                            # save record
                            _orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (partner_id, str(e))), 'error')
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        _orga2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': partner_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                logging.info('Currently there is no record for partner_id %s!' % partner_id)

        # store work records again
        works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, core='hb2',
                          query='group_id:%s' % id, facet=False, rows=500000)
        works_solr.request()

        for work in works_solr.results:
            # lock record
            lock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='hb2',
                                  data=[{'id': work.get('id'), 'locked': {'set': 'true'}}])
            lock_work_solr.update()

            # edit
            try:
                thedata = json.loads(work.get('wtf_json'))
                form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                form.changed.data = timestamp()
                _record2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % work.get('wtf_json'))

            # unlock record
            unlock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': work.get('id'), 'locked': {'set': 'false'}}])
            unlock_work_solr.update()

        # store person records again
        persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='person',
                            query='group_id:%s' % id, facet=False, rows=500000)
        persons_solr.request()

        for person in persons_solr.results:
            # lock record
            lock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    data=[{'id': person.get('id'), 'locked': {'set': 'true'}}])
            lock_person_solr.update()

            # edit
            try:
                thedata = json.loads(person.get('wtf_json'))
                form = PersonAdminForm.from_json(thedata)
                form.changed.data = timestamp()
                _person2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % person.get('wtf_json'))

            # unlock record
            unlock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='person',
                                      data=[{'id': person.get('id'), 'locked': {'set': 'false'}}])
            unlock_person_solr.update()

    return id


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    page = int(request.args.get('page', 1))
    sorting = request.args.get('sort', '')
    if sorting == '':
        sorting = 'recordCreationDate desc'
    elif sorting == 'relevance':
        sorting = ''
    mystart = 0
    query = '*:*'
    filterquery = request.values.getlist('filter')
    logging.info(filterquery)

    dashboard_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, start=(page - 1) * 10, query=query,
                          sort=sorting, json_facet=secrets.DASHBOARD_FACETS, fquery=filterquery)
    dashboard_solr.request()

    num_found = dashboard_solr.count()
    pagination = ''
    if num_found == 0:
        flash(gettext('There Are No Records Yet!'), 'danger')
    else:
        pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                                record_name=lazy_gettext('titles'),
                                search_msg=lazy_gettext('Showing {start} to {end} of {found} {record_name}'))
        mystart = 1 + (pagination.page - 1) * pagination.per_page

    return render_template('dashboard.html', records=dashboard_solr.results, facet_data=dashboard_solr.facets,
                           header=lazy_gettext('Dashboard'), site=theme(request.access_route), offset=mystart - 1,
                           query=query, filterquery=filterquery, pagination=pagination, now=datetime.datetime.now(),
                           core='hb2', target='dashboard', del_redirect='dashboard', numFound=num_found,
                           role_map=display_vocabularies.ROLE_MAP,
                           lang_map=display_vocabularies.LANGUAGE_MAP,
                           pubtype_map=display_vocabularies.PUBTYPE2TEXT,
                           subtype_map=display_vocabularies.SUBTYPE2TEXT,
                           license_map=display_vocabularies.LICENSE_MAP,
                           frequency_map=display_vocabularies.FREQUENCY_MAP,
                           pubstatus_map=display_vocabularies.PUB_STATUS,
                           edtstatus_map=display_vocabularies.EDT_STATUS
                           )


@app.route('/dashboard/doc/<page>')
@login_required
def docs(page='index'):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    return render_template('doc/%s.html' % page, header=lazy_gettext('Documentation'), site=theme(request.access_route))


@app.route('/dashboard/news')
@login_required
def news():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    return render_template('news.html', header=lazy_gettext('News'), site=theme(request.access_route))


@app.route('/persons')
@login_required
def persons():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    page = int(request.args.get('page', 1))
    sorting = request.args.get('sort', '')
    if sorting == '':
        sorting = 'changed desc'
    elif sorting == 'relevance':
        sorting = ''
    mystart = 0
    query = '*:*'
    filterquery = request.values.getlist('filter')

    # get persons
    persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                        query=query, start=(page - 1) * 10, core='person',
                        sort=sorting, json_facet=secrets.DASHBOARD_PERS_FACETS, fquery=filterquery)
    persons_solr.request()

    num_found = persons_solr.count()

    if num_found == 0:
        flash(gettext('There Are No Persons Yet!'))
        return render_template('persons.html', header=lazy_gettext('Persons'), site=theme(request.access_route),
                               facet_data=persons_solr.facets, results=persons_solr.results,
                               offset=mystart - 1, query=query, filterquery=filterquery,
                               now=datetime.datetime.now())
    else:
        pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                                record_name=lazy_gettext('titles'),
                                search_msg=lazy_gettext('Showing {start} to {end} of {found} Persons'))
        mystart = 1 + (pagination.page - 1) * pagination.per_page

    return render_template('persons.html', header=lazy_gettext('Persons'), site=theme(request.access_route),
                           facet_data=persons_solr.facets, results=persons_solr.results,
                           offset=mystart - 1, query=query, filterquery=filterquery, pagination=pagination,
                           now=datetime.datetime.now(), del_redirect='persons', core='person')


@app.route('/organisations')
@login_required
def orgas():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    page = int(request.args.get('page', 1))
    mystart = 0
    query = '*:*'
    filterquery = request.values.getlist('filter')

    orgas_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                      application=secrets.SOLR_APP, query=query, start=(page - 1) * 10, core='organisation',
                      sort='changed desc', json_facet=secrets.DASHBOARD_ORGA_FACETS, fquery=filterquery)
    orgas_solr.request()

    num_found = orgas_solr.count()

    if num_found == 0:
        flash(gettext('There Are No Organisations Yet!'))
        return render_template('orgas.html', header=lazy_gettext('Organisations'), site=theme(request.access_route),
                               facet_data=orgas_solr.facets, results=orgas_solr.results,
                               offset=mystart - 1, query=query, filterquery=filterquery, now=datetime.datetime.now())
    else:
        pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                                record_name=lazy_gettext('titles'),
                                search_msg=lazy_gettext('Showing {start} to {end} of {found} Organisational Units'))
        mystart = 1 + (pagination.page - 1) * pagination.per_page

    return render_template('orgas.html', header=lazy_gettext('Organisations'), site=theme(request.access_route),
                           facet_data=orgas_solr.facets, results=orgas_solr.results,
                           offset=mystart - 1, query=query, filterquery=filterquery, pagination=pagination,
                           now=datetime.datetime.now(), core='organisation')


@app.route('/groups')
@login_required
def groups():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    page = int(request.args.get('page', 1))
    mystart = 0
    query = '*:*'
    filterquery = request.values.getlist('filter')

    groups_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, query=query, start=(page - 1) * 10, core='group',
                       sort='changed desc', json_facet=secrets.DASHBOARD_GROUP_FACETS, fquery=filterquery)
    groups_solr.request()

    num_found = groups_solr.count()

    if num_found == 0:
        flash(gettext('There Are No Working Groups Yet!'))
        return render_template('groups.html', header=lazy_gettext('Working Groups'), site=theme(request.access_route),
                               facet_data=groups_solr.facets, results=groups_solr.results,
                               offset=mystart - 1, query=query, filterquery=filterquery, now=datetime.datetime.now())
    else:
        pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                                record_name=lazy_gettext('titles'),
                                search_msg=lazy_gettext('Showing {start} to {end} of {found} Working Groups'))
        mystart = 1 + (pagination.page - 1) * pagination.per_page
    return render_template('groups.html', header=lazy_gettext('Working Groups'), site=theme(request.access_route),
                           facet_data=groups_solr.facets, results=groups_solr.results,
                           offset=mystart - 1, query=query, filterquery=filterquery, pagination=pagination,
                           now=datetime.datetime.now(), core='group')


@app.route('/units')
def units():
    return 'Not Implemented Yet'


@app.route('/serials')
def serials():
    return 'Not Implemented Yet'


@app.route('/containers')
def containers():
    return 'poop'


@app.route('/create/<pubtype>', methods=['GET', 'POST'])
@login_required
def new_record(pubtype='ArticleJournal'):
    form = display_vocabularies.PUBTYPE2FORM.get(pubtype)()
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        form = display_vocabularies.PUBTYPE2USERFORM.get(pubtype)()

    # logging.info(form)

    if request.is_xhr:
        logging.info('REQUEST: %s' % request.form)
        form = display_vocabularies.PUBTYPE2FORM.get(pubtype)(request.form)
        # logging.debug('ID: %s' % form.data.get('id').strip())
        # logging.debug('CHANGE pubtype: wtf = %s' % json.dumps(form.data))
        if current_user.role != 'admin' and current_user.role != 'superadmin':
            form = display_vocabularies.PUBTYPE2USERFORM.get(pubtype)(request.form)
        # logging.debug(form.data)
        # logging.debug(form.title.data)
        # logging.debug('CHANGE pubtype: wtf = %s' % json.dumps(form.data))
        # Do we have any data already?
        if not form.title.data:
            solr_data = {}

            wtf = json.dumps(form.data)
            solr_data.setdefault('wtf_json', wtf)

            for field in form.data:
                # logging.info('%s => %s' % (field, form.data.get(field)))
                # TODO Die folgenden Daten müssen auch ins Formular
                if field == 'id':
                    solr_data.setdefault('id', form.data.get(field).strip())
                if field == 'created':
                    solr_data.setdefault('recordCreationDate', form.data.get(field).strip().replace(' ', 'T') + 'Z')
                if field == 'changed':
                    solr_data.setdefault('recordChangeDate', form.data.get(field).strip().replace(' ', 'T') + 'Z')
                if field == 'owner':
                    solr_data.setdefault('owner', form.data.get(field)[0].strip())
                if field == 'pubtype':
                    solr_data.setdefault('pubtype', form.data.get(field).strip())
                if field == 'editorial_status':
                    solr_data.setdefault('editorial_status', form.data.get(field).strip())
            # logging.debug('CHANGE pubtype: wtf = %s' % json.dumps(form.data))
            record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, core='hb2', data=[solr_data])
            record_solr.update()
        else:
            persistence.record2solr(form, action='create')
        return jsonify({'status': 200})

    for person in form.person:
        if current_user.role == 'admin' or current_user.role == 'superadmin':
            if pubtype != 'Patent':
                person.role.choices = forms_vocabularies.ADMIN_ROLES
        else:
            if pubtype != 'Patent':
                person.role.choices = forms_vocabularies.USER_ROLES

    if current_user.role == 'admin' or current_user.role == 'superadmin':
        form.pubtype.choices = forms_vocabularies.ADMIN_PUBTYPES
    else:
        form.pubtype.choices = forms_vocabularies.USER_PUBTYPES

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', form=form, header=lazy_gettext('New Record'),
                               site=theme(request.access_route), action='create', pubtype=pubtype)

    if valid:
        try:
            if current_user.role == 'user':
                form.owner[0].data = current_user.email
            if current_user.role == 'admin' or current_user.role == 'superadmin':
                if form.data.get('editorial_status') == 'new':
                    form.editorial_status.data = 'in_process'
            if len(form.data.get('owner')) == 0 or form.data.get('owner')[0] == '':
                form.owner[0].data = current_user.email
            if len(form.data.get('catalog')) == 0 or form.data.get('catalog')[0] == '':
                if current_user.affiliation == 'tudo':
                    form.catalog.data = ['Technische Universität Dortmund']
                if current_user.affiliation == 'rub':
                    form.catalog.data = ['Ruhr-Universität Bochum']
        except AttributeError:
            pass

        new_id, message = persistence.record2solr(form, action='create')
        if current_user.role != 'user':
            for msg in message:
                flash(msg, category='warning')

        return redirect(url_for('show_record', pubtype=pubtype, record_id=form.data.get('id').strip()))

    if request.args.get('subtype'):
        form.subtype.data = request.args.get('subtype')
    form.id.data = str(uuid.uuid4())

    form.created.data = timestamp()
    form.changed.data = timestamp()
    form.owner[0].data = current_user.email
    form.pubtype.data = pubtype

    # logging.info('FORM: %s' % form.data)

    return render_template('tabbed_form.html', form=form, header=lazy_gettext('New Record'),
                           site=theme(request.access_route), pubtype=pubtype, action='create',
                           record_id=form.id.data)


@app.route('/create/publication')
@login_required
def new_by_form():
    return render_template('pubtype_list.html', header=lazy_gettext('New Record by Publication Type'),
                           site=theme(request.access_route))


@app.route('/create/from_identifiers')
@login_required
def new_by_identifiers():
    doi = request.args.get('doi', '')
    id = request.args.get('id', '')
    source = request.args.get('source', '')

    if doi != '':
        wtf_json = crossref_processor.crossref2wtfjson(doi)

        # TODO if wtf_json = '' >> datacite
        logging.debug(wtf_json)
        if not wtf_json.get('id'):
            wtf_json = datacite_processor.datacite2wtfjson(doi)

        if not wtf_json.get('catalog') or wtf_json.get('catalog')[0] == '':
            if current_user and current_user.affiliation and current_user.affiliation == 'tudo':
                wtf_json.setdefault('catalog', []).append('Technische Universität Dortmund')
            elif current_user and current_user.affiliation and current_user.affiliation == 'rub':
                wtf_json.setdefault('catalog', []).append('Ruhr-Universität Bochum')
            else:
                wtf_json.setdefault('catalog', []).append('Temporäre Daten')

        form = display_vocabularies.PUBTYPE2FORM.get(wtf_json.get('pubtype')).from_json(wtf_json)
        if current_user.role != 'admin' and current_user.role != 'superadmin':
            try:
                form = display_vocabularies.PUBTYPE2USERFORM.get(wtf_json.get('pubtype')).from_json(wtf_json)
            except Exception:
                form = display_vocabularies.PUBTYPE2USERFORM.get('Report').from_json(wtf_json)
        # logging.info('FORM from CSL: %s' % form.data)

        if current_user.role == 'admin' or current_user.role == 'superadmin':
            for person in form.person:
                if current_user.role == 'admin' or current_user.role == 'superadmin':
                    person.role.choices = forms_vocabularies.ADMIN_ROLES
                else:
                    person.role.choices = forms_vocabularies.USER_ROLES

        if current_user.role == 'admin' or current_user.role == 'superadmin':
            form.pubtype.choices = forms_vocabularies.ADMIN_PUBTYPES
        else:
            form.pubtype.choices = forms_vocabularies.USER_PUBTYPES

        form.owner[0].data = current_user.email

        return render_template('tabbed_form.html', form=form, header=lazy_gettext('Register New %s' % form.data.get('pubtype')),
                               site=theme(request.access_route), pubtype=form.data.get('pubtype'), action='create',
                               record_id=form.id.data)

    elif id != '' and source != '':

        wtf_json = ''

        if source == 'gbv':
            wtf_json = mods_processor.mods2wtfjson(id)
            logging.info(wtf_json)

        if wtf_json != '':

            if not wtf_json.get('catalog') or wtf_json.get('catalog')[0] == '':
                if current_user and current_user.affiliation and current_user.affiliation == 'tudo':
                    wtf_json.setdefault('catalog', []).append('Technische Universität Dortmund')
                elif current_user and current_user.affiliation and current_user.affiliation == 'rub':
                    wtf_json.setdefault('catalog', []).append('Ruhr-Universität Bochum')
                else:
                    wtf_json.setdefault('catalog', []).append('Temporäre Daten')

            form = display_vocabularies.PUBTYPE2FORM.get(wtf_json.get('pubtype')).from_json(wtf_json)
            if current_user.role != 'admin' and current_user.role != 'superadmin':
                try:
                    form = display_vocabularies.PUBTYPE2USERFORM.get(wtf_json.get('pubtype')).from_json(wtf_json)
                except Exception:
                    form = display_vocabularies.PUBTYPE2USERFORM.get('Report').from_json(wtf_json)
            # logging.info('FORM from CSL: %s' % form.data)

            if current_user.role == 'admin' or current_user.role == 'superadmin':
                for person in form.person:
                    if current_user.role == 'admin' or current_user.role == 'superadmin':
                        person.role.choices = forms_vocabularies.ADMIN_ROLES
                    else:
                        person.role.choices = forms_vocabularies.USER_ROLES

            if current_user.role == 'admin' or current_user.role == 'superadmin':
                form.pubtype.choices = forms_vocabularies.ADMIN_PUBTYPES
            else:
                form.pubtype.choices = forms_vocabularies.USER_PUBTYPES

            form.owner[0].data = current_user.email

            return render_template('tabbed_form.html', form=form, header=lazy_gettext('Register New %s' % form.data.get('pubtype')),
                                   site=theme(request.access_route), pubtype=form.data.get('pubtype'), action='create',
                                   record_id=form.id.data)

    else:
        return render_template('search_external.html', header=lazy_gettext('Register New Work'),
                               site=theme(request.access_route), type='by_id')


@app.route('/create/from_search')
@login_required
def new_by_search():
    return render_template('search_external.html', header=lazy_gettext('Register New Work'),
                           site=theme(request.access_route), type='by_search')


@app.route('/create/from_file', methods=['GET', 'POST'])
@login_required
def file_upload():
    form = FileUploadForm()
    if form.validate_on_submit() or request.method == 'POST':
        # logging.info(form.file.data.headers)
        if 'tu-dortmund' in current_user.email:
            upload_resp = requests.post(secrets.REDMINE_URL + 'uploads.json',
                                        headers={'Content-type': 'application/octet-stream',
                                                 'X-Redmine-API-Key': secrets.REDMINE_KEY},
                                        data=form.file.data.stream.read())
            logging.info(upload_resp.status_code)
            logging.info(upload_resp.headers)
            logging.info(upload_resp.text)
            logging.info(upload_resp.json())
            data = {}
            data.setdefault('issue', {}).setdefault('project_id', secrets.REDMINE_PROJECT)
            data.setdefault('issue', {}).setdefault('tracker_id', 6)
            data.setdefault('issue', {}).setdefault('status_id', 1)
            data.setdefault('issue', {}).setdefault('subject', 'Publikationsliste %s (%s)' % (current_user.name, timestamp()))
            uploads = {}
            uploads.setdefault('token', upload_resp.json().get('upload').get('token'))
            uploads.setdefault('filename', form.file.data.filename)
            uploads.setdefault('content_type', form.file.data.mimetype)
            data.setdefault('issue', {}).setdefault('uploads', []).append(uploads)
            description = ''
            description += 'Dateiname: %s\n' % form.file.data.filename
            description += 'Melder-Mail: %s\n' % current_user.email
            description += 'Melder-Name: %s\n' % current_user.name
            description += u'Mime-Type: %s\n' % form.file.data.mimetype
            data.setdefault('issue', {}).setdefault('description', description)
            logging.info(json.dumps(data))
            issue_resp = requests.post(secrets.REDMINE_URL + 'issues.json', headers={'Content-type': 'application/json',
                                                                                     'X-Redmine-API-Key': secrets.REDMINE_KEY},
                                       data=json.dumps(data))
            logging.info(issue_resp.status_code)
            logging.info(issue_resp.text)
        else:
            trac = xmlrpc.client.ServerProxy(
                secrets.TRAC_URL % (secrets.TRAC_USER, secrets.TRAC_PW))
            attrs = {
                'component': 'Dateneingang',
                'owner': 'hbbot',
                'milestone': 'Kampagne2015',
                'type': 'task',
            }
            admin_record = ''
            admin_record += 'Dateiname: %s\n' % form.file.data.filename
            admin_record += 'Melder-Mail: %s\n' % current_user.email
            admin_record += 'Melder-Name: %s\n' % current_user.name
            admin_record += u'Mime-Type: %s\n' % form.file.data.mimetype
            logging.info(admin_record)
            ticket = trac.ticket.create('Datendatei: %s' % form.file.data.filename, admin_record, attrs, True)
            attachment = trac.ticket.putAttachment(str(ticket), form.file.data.filename, 'Datei zur Dateneingabe',
                                                   form.file.data.stream.read(), True)
            # return redirect('http://bibliographie-trac.ub.rub.de/ticket/' + str(ticket))
        flash(gettext(
            'Thank you for uploading your data! We will now edit them and make them available as soon as possible.'))
    return render_template('file_upload.html', header=lazy_gettext('Upload a List of Citations'), site=theme(request.access_route),
                           form=form)


@csrf.exempt
@app.route('/create/from_json', methods=['POST'])
@login_required
def new_by_json():
    # TODO API-KEY management
    if request.headers.get('Content-Type') and request.headers.get('Content-Type') == 'applications/json':
        record = json.loads(request.data)
        if type(record) is 'dict':
            try:
                form = display_vocabularies.PUBTYPE2FORM.get(record.get('pubtype')).from_json(record)
                return _record2solr(form, action='create', relitems=True)
            except AttributeError as e:
                logging.error(e)
                make_response(jsonify(record), 500)
        elif type(record) is 'list':
            for item in record:
                try:
                    form = display_vocabularies.PUBTYPE2FORM.get(item.get('pubtype')).from_json(item)
                    return _record2solr(form, action='create', relitems=True)
                except AttributeError as e:
                    logging.error(e)
                    make_response(jsonify(item), 500)
        else:
            return make_response(jsonify({'error': 'Bad Request: Invalid Data!'}), 400)

        return make_response(jsonify(record), 200)
    else:
        return make_response(jsonify({'error': 'Bad Request: Content-Type not valid!'}), 400)


@app.route('/create/person', methods=['GET', 'POST'])
@login_required
def new_person():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    form = PersonAdminForm()

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', header=lazy_gettext('New Person'), site=theme(request.access_route),
                               form=form, action='create', pubtype='person')

    if valid:
        if current_user.role == 'admin' or current_user.role == 'superadmin':
            if form.data.get('editorial_status') == 'new':
                form.editorial_status.data = 'in_process'
        # logging.info(form.data)
        doit, new_id, message = persistence.person2solr(form, action='create')
        if doit:

            return show_person(form.data.get('id').strip())
            # return redirect(url_for('persons'))
        else:
            flash(gettext('A person with id %s already exists!' % new_id), 'danger')
            return render_template('tabbed_form.html', header=lazy_gettext('New Person'),
                                   site=theme(request.access_route), form=form, action='create', pubtype='person')

    form.created.data = timestamp()
    form.changed.data = timestamp()
    form.id.data = uuid.uuid4()
    form.owner[0].data = current_user.email

    return render_template('tabbed_form.html', header=lazy_gettext('New Person'), site=theme(request.access_route),
                           form=form, action='create', pubtype='person')


@app.route('/create/person_from_gnd', methods=['GET', 'POST'])
@login_required
def new_person_from_gnd():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    gndid = request.args.get('gndid', '')
    if gndid == '':
        # render id request form
        form = PersonFromGndForm()
        if form.validate_on_submit():
            return redirect(url_for('new_person_from_gnd', gndid=form.data.get('gnd')))

        return render_template('linear_form.html', header=lazy_gettext('New Person from GND'),
                               site=theme(request.access_route), form=form, action='create', pubtype='person_from_gnd')
    else:
        # get data fron GND and render pre filled person form
        url = 'http://d-nb.info/gnd/%s/about/lds.rdf' % gndid

        # get data, convert and put to PersonAdminForm
        RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        GNDO = 'http://d-nb.info/standards/elementset/gnd#'
        OWL = 'http://www.w3.org/2002/07/owl#'
        NSDICT = {'r': RDF, 'g': GNDO, 'o': OWL}

        record = etree.parse(url)
        logging.info(etree.tostring(record))

        if record:
            form = PersonAdminForm()

            if record.xpath('//g:preferredNameForThePerson', namespaces=NSDICT):
                logging.info('Name: %s' % record.xpath('//g:preferredNameForThePerson', namespaces=NSDICT)[0].text)
                form.name.data = record.xpath('//g:preferredNameForThePerson', namespaces=NSDICT)[0].text
            if record.xpath('//g:gender', namespaces=NSDICT):
                logging.info('Gender: %s' % record.xpath('//g:gender/@r:resource', namespaces=NSDICT)[0])
                if 'male' in record.xpath('//g:gender/@r:resource', namespaces=NSDICT)[0]:
                    form.salutation.data = 'm'
                elif 'female' in record.xpath('//g:gender/@r:resource', namespaces=NSDICT)[0]:
                    form.salutation.data = 'f'
            if record.xpath('//o:sameAs', namespaces=NSDICT):
                if 'orcid' in record.xpath('//o:sameAs/@r:resource', namespaces=NSDICT)[0]:
                    logging.info(
                        'ORCID: %s' % record.xpath('//o:sameAs/@r:resource', namespaces=NSDICT)[0].split('org/')[1])
                    form.orcid.data = record.xpath('//o:sameAs/@r:resource', namespaces=NSDICT)[0].split('org/')[1]
            if record.xpath('//g:affiliation', namespaces=NSDICT):
                logging.info('Affiliation: %s' %
                             record.xpath('//g:affiliation/@r:resource', namespaces=NSDICT)[0].split('/gnd/')[1])
                form.affiliation[0].organisation_id.data = \
                record.xpath('//g:affiliation/@r:resource', namespaces=NSDICT)[0].split('/gnd/')[1]

            form.gnd.data = gndid

            form.created.data = timestamp()
            form.changed.data = timestamp()
            form.id.data = uuid.uuid4()
            form.owner[0].data = current_user.email

            # is gndid or name or orcid currently in hb2?
            try:
                query = 'gnd:%s' % form.data.get('gnd')
                person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                   fields=['id'])
                person_solr.request()
                if len(person_solr.results) > 0:
                    flash('%s is apparently duplicate: %s! (GND id found.)' % (gndid, person_solr.results[0].get('id')),
                          category='warning')
                else:
                    query = 'orcid:%s' % form.data.get('orcid')
                    person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                       fields=['id'])
                    person_solr.request()
                    if len(person_solr.results) > 0:
                        flash('%s is apparently duplicate: %s! (ORCID found.)' % (
                        gndid, person_solr.results[0].get('id')), category='warning')
                    else:
                        query = 'name:%s' % form.data.get('name')
                        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                           fields=['id'])
                        person_solr.request()
                        if len(person_solr.results) > 0:
                            for person in person_solr.results:
                                flash('%s is apparently duplicate: %s! (Name found.)' % (gndid, person.get('id')),
                                      category='warning')
            except AttributeError as e:
                logging.error(e)

            return render_template('tabbed_form.html', form=form,
                                   header=lazy_gettext('Edit: %(person)s', person=form.data.get('name')),
                                   locked=True, site=theme(request.access_route), action='update', pubtype='person',
                                   record_id=form.data.get('id'))
        else:
            flash(gettext('The requested ID %s is not known in GND!' % gndid))
            return redirect(url_for('/create/person_from_gnd'))


@app.route('/create/person_from_orcid', methods=['GET', 'POST'])
@login_required
def new_person_from_orcid(orcid=''):
    if request.method == 'GET':
        # render id request form
        return render_template('person_from_orcid.html')
    else:
        # get data fron ORCID and render pre filled person form
        url = 'http://d-nb.info/gnd/%s/about/lds.xml' % orcid

        # get data, convert and put to PersonAdminForm

        return render_template('tabbed_form.html', form=form,
                               header=lazy_gettext('Edit: %(person)s', person=form.data.get('name')),
                               locked=True, site=theme(request.access_route), action='update', pubtype='person',
                               record_id=person_id)


@app.route('/create/organisation', methods=['GET', 'POST'])
@login_required
def new_orga():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    form = OrgaAdminForm()

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', header=lazy_gettext('New Organisation'),
                               site=theme(request.access_route), form=form, action='create', pubtype='organisation')

    if valid:
        if current_user.role == 'admin' or current_user.role == 'superadmin':
            if form.data.get('editorial_status') == 'new':
                form.editorial_status.data = 'in_process'
        if len(form.data.get('owner')) == 0 or form.data.get('owner')[0] == '':
            form.owner[0].data = current_user.email
        if len(form.data.get('catalog')) == 0 or form.data.get('catalog')[0] == '':
            # TODO use config data
            if current_user.affiliation == 'tudo':
                form.catalog.data = ['Technische Universität Dortmund']
            if current_user.affiliation == 'rub':
                form.catalog.data = ['Ruhr-Universität Bochum']
        # logging.info(form.data)
        redirect_id, message = persistence.orga2solr(form, action='create')
        for msg in message:
            flash(msg, category='warning')

        return show_orga(form.data.get('id').strip())
        # return redirect(url_for('orgas'))

    form.id.data = uuid.uuid4()
    form.owner[0].data = current_user.email
    form.created.data = timestamp()
    form.changed.data = timestamp()
    return render_template('tabbed_form.html', header=lazy_gettext('New Organisation'),
                           site=theme(request.access_route), form=form, action='create', pubtype='organisation')


@app.route('/create/group', methods=['GET', 'POST'])
@login_required
def new_group():
    form = GroupAdminForm()
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        form = GroupAdminUserForm()

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', header=lazy_gettext('New Working Group'),
                               site=theme(request.access_route), form=form, action='create', pubtype='group')

    if valid:
        if current_user.role == 'admin' or current_user.role == 'superadmin':
            if form.data.get('editorial_status') == 'new':
                form.editorial_status.data = 'in_process'
        if len(form.data.get('owner')) == 0 or form.data.get('owner')[0] == '':
            form.owner[0].data = current_user.email
        if len(form.data.get('catalog')) == 0 or form.data.get('catalog')[0] == '':
            # TODO use config data
            if current_user.affiliation == 'tudo':
                form.catalog.data = ['Technische Universität Dortmund']
            if current_user.affiliation == 'rub':
                form.catalog.data = ['Ruhr-Universität Bochum']

        # logging.info(form.data)
        redirect_id, message = persistence.group2solr(form, action='create')
        for msg in message:
            flash(msg, category='warning')

        return show_group(form.data.get('id').strip())
        # return redirect(url_for('groups'))

    form.id.data = uuid.uuid4()
    form.owner[0].data = current_user.email
    form.created.data = timestamp()
    form.changed.data = timestamp()

    return render_template('tabbed_form.html', header=lazy_gettext('New Working Group'),
                           site=theme(request.access_route), form=form, action='create', pubtype='group')


@app.route('/is_locked/<pubtype>/<record_id>')
@csrf.exempt
def is_record_locked(pubtype, record_id):

    is_locked = False

    show_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, query='id:%s' % record_id)
    show_record_solr.request()

    if len(show_record_solr.results) > 0:
        is_locked = bool(show_record_solr.results[0].get('locked'))

    return jsonify({'is_locked': is_locked})


@app.route('/retrieve/<pubtype>/<record_id>')
@app.route('/retrieve/<pubtype>/<record_id>/')
def show_record(pubtype, record_id=''):

    result = persistence.get_work(record_id)

    if result:
        is_part_of = result.get('is_part_of')
        has_part = result.get('has_part')
        other_version = result.get('other_version')

        affiliation = result.get('fakultaet')
        group = result.get('group')
        csl_json = wtf_csl.wtf_csl([json.loads(result.get('wtf_json'))])
        orcid_json = orcid_processor.wtf_orcid([json.loads(result.get('wtf_json'))])
        if result.get('bibliographicCitation'):
            openurl = result.get('bibliographicCitation')
        else:
            openurl = openurl_processor.wtf_openurl(json.loads(result.get('wtf_json')))

        thedata = json.loads(result.get('wtf_json'))
        locked = result.get('locked')

        editable = False
        user_eq_actor = False
        if current_user.is_authenticated:
            for person in thedata.get('person'):
                if person.get('gnd'):
                    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, query='gnd:%s' % person.get('gnd'),
                                       core='person', fields=['email'], facet='false')
                    get_request.request()

                    if len(get_request.results) > 0:
                        if get_request.results[0].get('email') == current_user.email:
                            user_eq_actor = True
                            break

            if (current_user.role == 'admin' and thedata.get('editorial_status') != 'deleted') \
                    or current_user.role == 'superadmin' \
                    or (current_user.email in thedata.get('owner') and thedata.get('editorial_status') == 'new') \
                    or (user_eq_actor and thedata.get('editorial_status') == 'new'):
                editable = True

        title = thedata.get('title')
        if is_part_of:
            for host in is_part_of:
                host_data = json.loads(host)
                if thedata.get('title') == host_data.get('volume'):
                    title = '%s / %s' % (host_data.get('title'), host_data.get('volume'))
                    break
        if thedata.get('subseries_sort'):
            title = '%s / %s' % (thedata.get('title'), thedata.get('subseries_sort'))

        form = display_vocabularies.PUBTYPE2FORM.get(pubtype).from_json(thedata)
        return render_template('record.html', record=form, header=title,
                               site=theme(request.access_route), action='retrieve', record_id=record_id,
                               del_redirect=url_for('dashboard'), pubtype=pubtype,
                               role_map=display_vocabularies.ROLE_MAP,
                               lang_map=display_vocabularies.LANGUAGE_MAP,
                               pubtype_map=display_vocabularies.PUBTYPE2TEXT,
                               subtype_map=display_vocabularies.SUBTYPE2TEXT,
                               license_map=display_vocabularies.LICENSE_MAP,
                               frequency_map=display_vocabularies.FREQUENCY_MAP,
                               pubstatus_map=display_vocabularies.PUB_STATUS,
                               locked=locked,
                               is_part_of=is_part_of, has_part=has_part, other_version=other_version,
                               affiliation=affiliation, group=group, openurl=openurl,
                               core='hb2', csl_json=json.dumps(csl_json, indent=4),
                               wtf_json=json.dumps(thedata, indent=4),
                               orcid_json=json.dumps(orcid_json, indent=4),
                               editable=editable, user_eq_actor=user_eq_actor)

    else:
        flash('The requested record %s was not found!' % record_id, category='warning')
        return redirect(url_for('dashboard'))


@app.route('/retrieve/person/<person_id>')
def show_person(person_id=''):

    result = persistence.get_person(person_id)

    if result:
        thedata = json.loads(result.get('wtf_json'))
        form = PersonAdminForm.from_json(thedata)
        locked = result.get('locked')

        return render_template('person.html', record=form, header=form.data.get('name'),
                               site=theme(request.access_route), action='retrieve', record_id=person_id,
                               pubtype='person', del_redirect=url_for('persons'),
                               url_map=display_vocabularies.URL_TYPE_MAP,
                               pers_status_map=display_vocabularies.PERS_STATUS_MAP,
                               locked=locked,
                               core='person', wtf_json=json.dumps(thedata, indent=4))
    else:
        flash('The requested person %s was not found!' % person_id, category='warning')
        return redirect(url_for('dashboard'))


@app.route('/retrieve/organisation/<orga_id>')
def show_orga(orga_id=''):

    result = persistence.get_orga(orga_id)

    if result:
        thedata = json.loads(result.get('wtf_json'))
        parent_type = result.get('parent_type')
        form = OrgaAdminForm.from_json(thedata)
        locked = result.get('locked')

        return render_template('orga.html', record=form, header=form.data.get('pref_label'),
                               site=theme(request.access_route), action='retrieve', record_id=orga_id,
                               pubtype='organisation', del_redirect=url_for('orgas'),
                               locked=locked, core='organisation',
                               parent_type=parent_type, wtf_json=json.dumps(thedata, indent=4))
    else:
        flash('The requested organisation %s was not found!' % orga_id, category='warning')
        return redirect(url_for('dashboard'))


@app.route('/retrieve/organisation/<orga_id>/links')
def show_orga_links(orga_id=''):
    linked_entities = {}
    # TODO get all orgas with parent_id=orga_id plus parent_id of orga_id
    children = []
    get_orgas_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                          application=secrets.SOLR_APP, query='parent_id:%s' % orga_id, core='organisation', facet='false')
    get_orgas_solr.request()
    if len(get_orgas_solr.results) > 0:
        for child in get_orgas_solr.results:
            children.append(child.get('id'))

    parents = []
    show_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                          application=secrets.SOLR_APP, query='id:%s' % orga_id, core='organisation', facet='false')
    show_orga_solr.request()
    thedata = json.loads(show_orga_solr.results[0].get('wtf_json'))
    form = OrgaAdminForm.from_json(thedata)
    if form.data.get('parent_id') and len(form.data.get('parent_id')) > 0:
        parents.append(form.data.get('parent_id'))

    linked_entities.setdefault('parents', parents)
    linked_entities.setdefault('children', children)

    # TODO get all persons with affiliation.organisation_id=orga_id
    persons = []
    ## TODO export der personen!!!
    get_persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                            application=secrets.SOLR_APP, query='*:*', core='person', facet='false')
    get_persons_solr.request()
    if len(get_persons_solr.results) > 0:
        for person in get_persons_solr.results:
            thedata = json.loads(person.get('wtf_json'))
            logging.info(thedata)
            affiliations = thedata.get('affiliation')
            logging.info(affiliations)
            for affiliation in affiliations:
                if affiliation.get('organisation_id') == orga_id:
                    persons.append(person.get('id'))

    linked_entities.setdefault('persons', persons)

    # TODO get all publications with affiliation_context=orga_id
    publications = []
    get_publications_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                 application=secrets.SOLR_APP, query='affiliation_context:%s' % orga_id, core='hb2', 
                                 facet='false')
    get_publications_solr.request()
    if len(get_publications_solr.results) > 0:
        for record in get_publications_solr.results:
            publications.append(record.get('id'))

    linked_entities.setdefault('publications', publications)

    return jsonify(linked_entities)


@app.route('/retrieve/group/<group_id>')
@csrf.exempt
def show_group(group_id=''):

    result = persistence.get_group(group_id)

    if result:
        thedata = json.loads(result.get('wtf_json'))
        parent_type = result.get('parent_type')
        form = GroupAdminForm.from_json(thedata)
        locked = result.get('locked')

        return render_template('group.html', record=form, header=form.data.get('pref_label'),
                               site=theme(request.access_route), action='retrieve', record_id=group_id,
                               pubtype='group', del_redirect=url_for('groups'),
                               locked=locked, core='group',
                               url_map=display_vocabularies.URL_TYPE_MAP, parent_type=parent_type,
                               wtf_json=json.dumps(thedata, indent=4))
    else:
        flash('The requested working group %s was not found!' % group_id, category='warning')
        return redirect(url_for('dashboard'))


@app.route('/update/<pubtype>/<record_id>', methods=['GET', 'POST'])
@login_required
def edit_record(record_id='', pubtype=''):

    cptask = request.args.get('cptask', False)
    # logging.info('cptask = %s' % cptask)
    user_is_actor = request.args.get('user_is_actor', False)
    # logging.info('user_is_actor = %s' % cptask)

    lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='hb2',
                            data=[{'id': record_id, 'locked': {'set': 'true'}}])
    lock_record_solr.update()

    edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
    edit_record_solr.request()

    thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))

    if request.method == 'POST':
        # logging.info('POST')
        form = display_vocabularies.PUBTYPE2FORM.get(pubtype)()
        if current_user.role != 'admin' and current_user.role != 'superadmin':
            form = display_vocabularies.PUBTYPE2USERFORM.get(pubtype)()
            # TODO insert GND-IDs and DataCatalog
        # logging.info(form.data)
    elif request.method == 'GET':
        # logging.info('GET')
        form = display_vocabularies.PUBTYPE2FORM.get(pubtype).from_json(thedata)
        if current_user.role != 'admin' and current_user.role != 'superadmin':
            form = display_vocabularies.PUBTYPE2USERFORM.get(pubtype).from_json(thedata)
        # logging.info(form.data)

    do_unlock = True
    if current_user.role == 'admin' or current_user.role == 'superadmin' or (current_user.role == 'user' and form.data.get('editorial_status') == 'new'):

        if current_user.role == 'admin' or current_user.role == 'superadmin':
            form.pubtype.choices = forms_vocabularies.ADMIN_PUBTYPES
        else:
            form.pubtype.choices = forms_vocabularies.USER_PUBTYPES

        if thedata.get('pubtype') != pubtype:
            diff = _diff_struct(thedata, form.data)
            if len(diff) > 0:
                flash(Markup(lazy_gettext(
                    '<p><i class="fa fa-exclamation-triangle fa-3x"></i> <h3>The publication type for the following data has changed. Please check the data.</h3></p>')) + diff,
                      'warning')
            form.pubtype.data = pubtype

        if current_user.role == 'admin' or current_user.role == 'superadmin':
            for person in form.person:
                if current_user.role == 'admin' or current_user.role == 'superadmin':
                    if pubtype != 'Patent':
                        person.role.choices = forms_vocabularies.ADMIN_ROLES
                else:
                    if pubtype != 'Patent':
                        person.role.choices = forms_vocabularies.USER_ROLES

        valid = form.validate_on_submit()
        # logging.info('form.errors: %s' % valid)
        # logging.info('form.errors: %s' % form.errors)

        if not valid and form.errors:
            flash_errors(form)
            return render_template('tabbed_form.html', form=form,
                                   header=lazy_gettext('Edit: %(title)s', title=form.data.get('title')),
                                   site=theme(request.access_route), action='update', pubtype=pubtype)

        if valid:

            try:
                if current_user.role == 'user':
                    form.owner[0].data = current_user.email
                    if len(form.data.get('catalog')) == 0 or form.data.get('catalog')[0] == '':
                        if current_user.affiliation == 'tudo':
                            form.catalog.data = ['Technische Universität Dortmund']
                        if current_user.affiliation == 'rub':
                            form.catalog.data = ['Ruhr-Universität Bochum']
                else:
                    if form.data.get('editorial_status') == 'new':
                        form.editorial_status.data = 'in_process'
                    if form.data.get('editorial_status') == 'edited' and current_user.role == 'superadmin':
                        form.editorial_status.data = 'final_editing'
            except AttributeError:
                pass

            new_id, message = persistence.record2solr(form, action='update')
            if current_user.role != 'user':
                for msg in message:
                    flash(msg, category='warning')
            if new_id != record_id:
                do_unlock = False

            # if cptask: delete redis record for record_id
            if cptask:
                # wenn trotzdem nicht verlinkt wurde, muss der Datensatz als behandelt in Redis
                # verzeichnet werden!
                get_record = Solr(application=secrets.SOLR_APP, facet='false', rows=2000000,
                                  query='id:%s' % record_id, fields=['pnd', 'id', 'title', 'pubtype', 'catalog'])
                get_record.request()

                is_relevant = True
                for gnd in get_record.results[0].get('pnd'):
                    ids = gnd.split('#')
                    if len(ids) != 3:
                        is_relevant = False
                        break

                if is_relevant:
                    # mark as not relevant anymore in redis
                    try:
                        storage_consolidate_persons = app.extensions['redis']['REDIS_CONSOLIDATE_PERSONS']
                        storage_consolidate_persons.hset('marked', record_id, timestamp())
                    except Exception as e:
                        logging.info('REDIS ERROR: %s' % e)
                        flash('Could not mark task for %s as not relevant anymore' % record_id, 'danger')
                # delete from tasks list
                try:
                    storage_consolidate_persons = app.extensions['redis']['REDIS_CONSOLIDATE_PERSONS']
                    storage_consolidate_persons.delete(record_id)
                except Exception as e:
                    logging.info('REDIS ERROR: %s' % e)
                    flash('Could not delete task for %s' % record_id, 'danger')

            return redirect(url_for('show_record', pubtype=pubtype, record_id=form.data.get('id').strip()))

        form.changed.data = timestamp()
        form.deskman.data = current_user.email

        return render_template('tabbed_form.html', form=form, header=lazy_gettext('Edit: %(title)s',
                                                                                  title=form.data.get('title')),
                               locked=True, site=theme(request.access_route), action='update',
                               pubtype=pubtype, record_id=record_id, cptask=str2bool(cptask))

    else:
        if do_unlock:
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()

        flash(lazy_gettext('You are not allowed to modify the record data, because the record is in editorial process. Please contact out team!'), 'warning')
        return redirect(url_for('show_record', pubtype=pubtype, record_id=record_id))


@app.route('/update/person/<person_id>', methods=['GET', 'POST'])
@login_required
def edit_person(person_id=''):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='person',
                            data=[{'id': person_id, 'locked': {'set': 'true'}}])
    lock_record_solr.update()

    person = persistence.get_person(person_id)

    if request.method == 'POST':
        form = PersonAdminForm()
    else:
        if person:
            thedata = json.loads(person.get('wtf_json'))
            form = PersonAdminForm.from_json(thedata)
        else:
            flash('The requested person %s was not found!' % person_id, category='warning')
            return redirect(url_for('persons'))

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', form=form,
                               header=lazy_gettext('Edit: %(title)s', title=form.data.get('title')),
                               site=theme(request.access_route), action='update')

    if valid:

        if form.data.get('editorial_status') == 'new':
            form.editorial_status.data = 'in_process'
        if form.data.get('editorial_status') == 'edited' and current_user.role == 'superadmin':
            form.editorial_status.data = 'final_editing'

        doit, redirect_id, message = persistence.person2solr(form, action='update')
        for msg in message:
            flash(msg, category='warning')
        if redirect_id == person_id:
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='person',
                                      data=[{'id': redirect_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()

        return show_person(form.data.get('id').strip())
        # return redirect(url_for('persons'))

    form.changed.data = timestamp()

    return render_template('tabbed_form.html', form=form,
                           header=lazy_gettext('Edit: %(person)s', person=form.data.get('name')),
                           locked=True, site=theme(request.access_route), action='update', pubtype='person',
                           record_id=person_id)


@app.route('/update/organisation/<orga_id>', methods=['GET', 'POST'])
@login_required
def edit_orga(orga_id=''):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='organisation',
                            data=[{'id': orga_id, 'locked': {'set': 'true'}}])
    lock_record_solr.update()

    orga = persistence.get_orga(orga_id)

    if request.method == 'POST':
        form = OrgaAdminForm()
    else:
        if orga:
            thedata = json.loads(orga.get('wtf_json'))
            form = OrgaAdminForm.from_json(thedata)
        else:
            flash('The requested organisation %s was not found!' % orga_id, category='warning')
            return redirect(url_for('orgas'))

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', form=form,
                               header=lazy_gettext('Edit: %(title)s', title=form.data.get('title')),
                               site=theme(request.access_route), action='update')

    if valid:

        if form.data.get('editorial_status') == 'new':
            form.editorial_status.data = 'in_process'
        if form.data.get('editorial_status') == 'edited' and current_user.role == 'superadmin':
            form.editorial_status.data = 'final_editing'

        # redirect_id, message = persistence.orga2solr(form, action='update', getchildren=True, relitems=False)
        redirect_id, message = persistence.orga2solr(form, action='update')
        for msg in message:
            flash(msg, category='warning')
        if redirect_id == orga_id:
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': redirect_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()

        return show_orga(redirect_id)
        # return redirect(url_for('orgas'))

    form.changed.data = timestamp()

    return render_template('tabbed_form.html', form=form,
                           header=lazy_gettext('Edit: %(orga)s', orga=form.data.get('pref_label')),
                           locked=True, site=theme(request.access_route), action='update', pubtype='organisation',
                           record_id=orga_id)


@app.route('/update/group/<group_id>', methods=['GET', 'POST'])
@login_required
def edit_group(group_id=''):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='group',
                            data=[{'id': group_id, 'locked': {'set': 'true'}}])
    lock_record_solr.update()

    group = persistence.get_group(group_id)

    if request.method == 'POST':
        form = GroupAdminForm()
    else:
        if group:
            thedata = json.loads(group.get('wtf_json'))
            form = GroupAdminForm.from_json(thedata)
        else:
            flash('The requested group %s was not found!' % group_id, category='warning')
            return redirect(url_for('groups'))

    valid = form.validate_on_submit()
    # logging.info('form.errors: %s' % valid)
    # logging.info('form.errors: %s' % form.errors)

    if not valid and form.errors:
        flash_errors(form)
        return render_template('tabbed_form.html', form=form,
                               header=lazy_gettext('Edit: %(title)s', title=form.data.get('title')),
                               site=theme(request.access_route), action='update')

    if valid:
        if form.data.get('editorial_status') == 'edited' and current_user.role == 'superadmin':
            form.editorial_status.data = 'final_editing'

        # logging.info('FORM: %s' % form.data)
        redirect_id, message = persistence.group2solr(form, action='update')
        for msg in message:
            flash(msg, category='warning')
        if redirect_id == group_id:
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='group',
                                      data=[{'id': redirect_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()

        return show_group(redirect_id)
        # return redirect(url_for('groups'))

    form.changed.data = timestamp()

    return render_template('tabbed_form.html', form=form,
                           header=lazy_gettext('Edit: %(group)s', group=form.data.get('pref_label')),
                           locked=True, site=theme(request.access_route), action='update', pubtype='group',
                           record_id=group_id)


@app.route('/delete/<record_id>')
def delete_record(record_id=''):
    # TODO owner darf löschen!
    if current_user.role == 'admin':
        # load record
        edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
        edit_record_solr.request()
        thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
        pubtype = thedata.get('pubtype')
        form = display_vocabularies.PUBTYPE2FORM.get(pubtype).from_json(thedata)
        # TODO if exists links of type 'other_version' (proof via Solr-Queries if not exists is_other_version_of), 'has_parts', then ERROR!
        # modify status to 'deleted'
        form.editorial_status.data = 'deleted'
        form.changed.data = timestamp()
        form.deskman.data = current_user.email
        # save record
        _record2solr(form, action='update')
        # return
        flash(gettext('Set editorial status of %s to deleted!' % record_id))

        return jsonify({'deleted': True})
    elif current_user.role == 'superadmin':
        delete_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                  application=secrets.SOLR_APP, core='hb2', del_id=record_id)
        delete_record_solr.delete()
        flash(gettext('Record %s deleted!' % record_id))

        return jsonify({'deleted': True})
    else:
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))


@app.route('/delete/person/<person_id>')
def delete_person(person_id=''):
    # TODO if admin
    if current_user.role == 'admin':
        flash(gettext('Set status of %s to deleted!' % person_id))
        # load person
        edit_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                application=secrets.SOLR_APP, core='person', query='id:%s' % person_id)
        edit_person_solr.request()

        thedata = json.loads(edit_person_solr.results[0].get('wtf_json'))
        form = PersonAdminForm.from_json(thedata)
        # modify status to 'deleted'
        form.editorial_status.data = 'deleted'
        form.changed.data = timestamp()
        form.deskman.data = current_user.email
        # save person
        _person2solr(form, action='delete')

        return jsonify({'deleted': True})
    # TODO if superadmin
    elif current_user.role == 'superadmin':
        delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                  application=secrets.SOLR_APP, core='person', del_id=person_id)
        delete_person_solr.delete()
        flash(gettext('Person %s deleted!' % person_id))

        return jsonify({'deleted': True})
    else:
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))


@app.route('/delete/organisation/<orga_id>')
def delete_orga(orga_id=''):
    # TODO if admin
    if current_user.role == 'admin':
        flash(gettext('Set status of %s to deleted!' % orga_id))
        # load orga
        edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                              application=secrets.SOLR_APP, core='organisation', query='id:%s' % orga_id)
        edit_orga_solr.request()

        thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
        form = OrgaAdminForm.from_json(thedata)
        # modify status to 'deleted'
        form.editorial_status.data = 'deleted'
        form.changed.data = timestamp()
        form.deskman.data = current_user.email
        # save orga
        _orga2solr(form, action='delete')

        return jsonify({'deleted': True})
    # TODO if superadmin
    elif current_user.role == 'superadmin':
        delete_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                application=secrets.SOLR_APP, core='organisation', del_id=orga_id)
        delete_orga_solr.delete()
        flash(gettext('Organisation %s deleted!' % orga_id))

        return jsonify({'deleted': True})
    else:
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))


@app.route('/delete/group/<group_id>')
def delete_group(group_id=''):
    # TODO if admin
    if current_user.role == 'admin':
        flash(gettext('Set status of %s to deleted!' % group_id))
        # load group
        edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                              application=secrets.SOLR_APP, core='group', query='id:%s' % group_id)
        edit_orga_solr.request()

        thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
        form = GroupAdminForm.from_json(thedata)
        # modify status to 'deleted'
        form.editorial_status.data = 'deleted'
        form.changed.data = timestamp()
        form.deskman.data = current_user.email
        # save group
        _group2solr(form, action='delete')

        return jsonify({'deleted': True})
    # TODO if superadmin
    elif current_user.role == 'superadmin':
        delete_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                 application=secrets.SOLR_APP, core='group', del_id=group_id)
        delete_group_solr.delete()
        flash(gettext('Working Group %s deleted!' % group_id))

        return jsonify({'deleted': True})
    else:
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))


@app.route('/delete/user/<user_id>')
def delete_user(user_id=''):
    # if superadmin
    if current_user.role == 'superadmin':
        delete_user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='hb2_users', del_id=user_id)
        delete_user_solr.delete()
        flash(gettext('User %s deleted!' % user_id))

        return jsonify({'deleted': True})
    else:
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))


@app.route('/add/file', methods=['GET', 'POST'])
def add_file():
    form = FileUploadForm()
    if form.validate_on_submit() or request.method == 'POST':
        # logging.info(form.file.data.headers)
        if 'tu-dortmund' in current_user.email:
            # TODO where to save the data from form
            data = form.file.data.stream.read()
        else:
            # TODO where to save the data from form
            data = form.file.data.stream.read()

        flash(gettext(
            'Thank you for uploading your data! We will now edit them and make them available as soon as possible.'))
    return render_template('file_upload.html', header=lazy_gettext('Upload File'), site=theme(request.access_route),
                           form=form)


@csrf.exempt
@app.route('/apparent_duplicate', methods=['GET', 'POST'])
def apparent_dup():
    if request.method == 'POST':
        logging.info(request.form.get('id'))
        logging.info(request.form.get('apparent_dup'))
        data = {}
        data.setdefault('id', request.form.get('id'))
        data.setdefault('apparent_dup', {}).setdefault('set', request.form.get('apparent_dup'))
        # requests.post('http://%s:%s/solr/%s/update' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_CORE),
        #              headers={'Content-type': 'application/json'}, data=json.dumps(data))
        app_dup_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP, core='hb2', data=[data])
        app_dup_solr.update()
    return jsonify(data)


@app.route('/duplicates')
def duplicates():
    pagination = ''
    page = int(request.args.get('page', 1))
    duplicates_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                           application=secrets.SOLR_APP, start=(page - 1) * 10, fquery=['dedupid:[* TO *]'],
                           group='true', group_field='dedupid', group_limit=100, facet='false')
    duplicates_solr.request()
    logging.info(duplicates_solr.response)
    num_found = duplicates_solr.count()
    if num_found == 0:
        flash(gettext('There are currently no Duplicates!'))
        return redirect(url_for('dashboard'))
    pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                            record_name=lazy_gettext('duplicate groups'),
                            search_msg=lazy_gettext('Showing {start} to {end} of {found} {record_name}'))
    mystart = 1 + (pagination.page - 1) * pagination.per_page
    return render_template('duplicates.html', groups=duplicates_solr.results, pagination=pagination,
                           header=lazy_gettext('Duplicates'), site=theme(request.access_route), offset=mystart - 1)


@app.route('/consolidate/persons')
@login_required
def consolidate_persons():
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))
    # Die ursprünglich hier definierte Funktion ist aus Gründen der Perfomance in ein separates Skript ausgelagert
    # worden. Diese kann nun zb. einmal täglich ausgeführt werden. Die Ergebnisse landen in einer Redis-Instanz.
    # Hier werden nun die Ergebnisse aus dieser Redis-Instanz geholt und angezeigt.
    catalog = request.args.get('catalog', '')

    try:
        storage_consolidate_persons = app.extensions['redis']['REDIS_CONSOLIDATE_PERSONS']

        results = []
        if catalog == '':
            catalog = current_user.affiliation
        # logging.info('CP catalog = %s' % catalog)
        tasks = storage_consolidate_persons.hgetall(catalog)
        # logging.info('CP tasks: %s' % len(tasks))
        # logging.info('CP tasks: %s' % tasks.keys())

        cnt = 0
        for task in tasks.keys():
            # logging.info('CP task %s: %s' % (task.decode('UTF-8'), storage_consolidate_persons.hget(catalog, task.decode('UTF-8'))))
            logging.info('CP result: %s' % ast.literal_eval(storage_consolidate_persons.hget(catalog, task.decode('UTF-8')).decode('UTF-8')))
            results.append(ast.literal_eval(storage_consolidate_persons.hget(catalog, task.decode('UTF-8')).decode('UTF-8')))
            cnt += 1
            if cnt == 25:
                break

        # for key in storage_consolidate_persons.keys('*'):
        #     thedata = storage_consolidate_persons.get(key)
        #     results.append(ast.literal_eval(thedata.decode('UTF-8')))

        # logging.info(results)
        # return 'TASKS to consolidate persons: %s / %s' % (len(results), json.dumps(results[0], indent=4))
        return render_template('consolidate_persons.html', results=results, num_found=len(tasks), count=len(results), catalog=catalog,
                               header=lazy_gettext('Consolidate Persons'), site=theme(request.access_route))

    except Exception as e:
        logging.info('REDIS ERROR: %s' % e)
        return 'failed to read data'


@app.route('/retrieve/related_items/<relation>/<record_ids>')
def show_related_item(relation='', record_ids=''):
    query = '{!terms f=id}%s' % record_ids
    if ',' not in record_ids:
        query = 'id:%s' % record_ids
    relation_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                         application=secrets.SOLR_APP, query=query, facet='false')
    relation_solr.request()

    return jsonify({'relation': relation, 'docs': relation_solr.results})


@app.route('/show_members/organisation/<orga_id>')
def show_members_of_orga(orga_id=''):
    # get orga doc
    orga = persistence.get_orga(orga_id)

    if not orga:
        return redirect(url_for('show_orga', orga_id=orga_id))
    else:
        thedata = json.loads(orga.get('wtf_json'))
        name = thedata.get('pref_label')

        orgas = {}
        orgas.setdefault(orga_id, name)
        # get all children
        if orga.get('children'):
            children = thedata.get('children')
            for child in children:
                # child = json.loads(child_json)
                if child.get('child_id'):
                    orgas.setdefault(child.get('child_id'), child.get('child_label'))
        # for each orga get all persons

        query = ''
        idx_p = 0
        for oid in orgas.keys():
            query += 'affiliation_id:%s' % oid
            idx_p += 1
            if idx_p < len(orgas) and query != '':
                query += ' OR '

        return redirect('%s?q=%s&core=person&list=1' % (url_for('search'), query))


@app.route('/show_works/organisation/<orga_id>')
def show_works_of_orga(orga_id=''):
    # get orga doc
    orga = persistence.get_orga(orga_id)

    if not orga:
        return redirect(url_for('show_orga', orga_id=orga_id))
    else:
        thedata = json.loads(orga.get('wtf_json'))
        name = thedata.get('pref_label')

        orgas = {}
        orgas.setdefault(orga_id, name)
        # get all children
        if orga.get('children'):
            children = thedata.get('children')
            for child in children:
                # child = json.loads(child_json)
                if child.get('child_id'):
                    orgas.setdefault(child.get('child_id'), child.get('child_label'))
        # for each orga get all persons

        query = ''
        idx_o = 0
        for oid in orgas.keys():
            member_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP,
                               query='affiliation_id:"%s"' % oid,
                               fquery=['gnd:[\'\' TO *]'], fields=['gnd', 'name'], rows=100000,
                               core='person')
            member_solr.request()

            query_part = ''

            if member_solr.results and len(member_solr.results) > 0:
                # logging.debug('members: %s' % len(member_solr.results))
                idx_p = 0
                for member in member_solr.results:
                    # TODO später nur pndid
                    query_part += 'pnd:"%s%s%s"' % (member.get('gnd'), '%23', member.get('name'))
                    idx_p += 1
                    if idx_p < len(member_solr.results) and query_part != '' and not query_part.endswith(' OR '):
                        query_part += ' OR '

                if query_part != '':
                    query += query_part

            idx_o += 1
            if idx_o < len(orgas) and query != '' and not query.endswith(' OR '):
                query += ' OR '

        while query.endswith(' OR '):
            query = query[:-4]

        url = '%s?q=%s&list=1' % (url_for('search'), query)
        return redirect(url.replace('//', '/'))
        # return 'poop'


@app.route('/show_members/group/<group_id>')
def show_members_of_group(group_id=''):
    return 'poop'


@app.route('/show_works/group/<group_id>')
def show_works_of_group(group_id=''):
    return 'poop'


@app.route('/embed_works')
def embed_works():
    return render_template('publists.html', header=lazy_gettext('Embed your work list'),
                           site=theme(request.access_route))


# ---------- SUPER_ADMIN ----------


@app.route('/superadmin', methods=['GET'])
@login_required
def superadmin():
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    # Get locked records that were last changed more than one hour ago...
    page = int(request.args.get('page', 1))
    locked_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                       core='hb2',
                       fquery=['locked:true', 'recordChangeDate:[* TO NOW-1HOUR]'], sort='recordChangeDate asc',
                       start=(page - 1) * 10)
    locked_solr.request()
    num_found = locked_solr.count()
    pagination = Pagination(page=page, total=num_found, found=num_found, bs_version=3, search=True,
                            record_name=lazy_gettext('records'),
                            search_msg=lazy_gettext('Showing {start} to {end} of {found} {record_name}'))
    mystart = 1 + (pagination.page - 1) * pagination.per_page

    solr_dumps = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP,
                      core='hb2_users', query='id:*.json', facet='false', rows=10000)
    solr_dumps.request()
    num_found = solr_dumps.count()
    form = FileUploadForm()

    return render_template('superadmin.html', locked_records=locked_solr.results,
                           header=lazy_gettext('Superadmin Board'),
                           import_records=solr_dumps.results, offset=mystart - 1, pagination=pagination,
                           del_redirect='superadmin', form=form, site=theme(request.access_route))


@app.route('/make_user/<user_id>')
@app.route('/superadmin/make_user/<user_id>')
@login_required
def make_user(user_id=''):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    if user_id:
        ma_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2_users', data=[{'id': user_id, 'role': {'set': 'user'}}])
        ma_solr.update()
        flash(gettext('%s downgraded to user!' % user_id), 'success')
        return redirect(url_for('superadmin'))
    else:
        flash(gettext('You did not supply an ID!'), 'danger')
        return redirect(url_for('superadmin'))


@app.route('/make_admin/<user_id>')
@app.route('/superadmin/make_admin/<user_id>')
@login_required
def make_admin(user_id=''):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    if user_id:
        ma_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2_users', data=[{'id': user_id, 'role': {'set': 'admin'}}])
        ma_solr.update()
        flash(gettext('%s made to admin!' % user_id), 'success')
        return redirect(url_for('superadmin'))
    else:
        flash(gettext('You did not supply an ID!'), 'danger')
        return redirect(url_for('superadmin'))


@app.route('/make_superadmin/<user_id>')
@app.route('/superadmin/make_superadmin/<user_id>')
@login_required
def make_superadmin(user_id=''):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    if user_id:
        ma_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2_users',
                       data=[{'id': user_id, 'role': {'set': 'superadmin'}}])
        ma_solr.update()
        flash(gettext('%s upgraded to superadmin!' % user_id), 'success')
        return redirect(url_for('superadmin'))
    else:
        flash(gettext('You did not supply an ID!'), 'danger')
        return redirect(url_for('superadmin'))


@app.route('/unlock/<record_id>', methods=['GET'])
@login_required
def unlock(record_id=''):
    # deaktiviert wegen owner-Rechten
    # if current_user.role != 'superadmin':
        # flash(gettext('For SuperAdmins ONLY!!!'))
        # return redirect(url_for('homepage'))
    if record_id:
        unlock_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='hb2',
                           data=[{'id': record_id, 'locked': {'set': 'false'}}])
        unlock_solr.update()

    redirect_url = 'superadmin'
    if get_redirect_target():
        redirect_url = get_redirect_target()

    return redirect(url_for(redirect_url))


@app.route('/unlock/person/<person_id>', methods=['GET'])
@login_required
def unlock_person(person_id=''):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    if person_id:
        unlock_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='person',
                           data=[{'id': person_id, 'locked': {'set': 'false'}}])
        unlock_solr.update()

    redirect_url = 'superadmin'
    if get_redirect_target():
        redirect_url = get_redirect_target()

    return redirect(url_for(redirect_url))


@app.route('/unlock/organisation/<orga_id>', methods=['GET'])
@login_required
def unlock_orga(orga_id=''):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    if orga_id:
        unlock_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='organisation',
                           data=[{'id': orga_id, 'locked': {'set': 'false'}}])
        unlock_solr.update()

    redirect_url = 'superadmin'
    if get_redirect_target():
        redirect_url = get_redirect_target()

    return redirect(url_for(redirect_url))


@app.route('/unlock/group/<group_id>', methods=['GET'])
@login_required
def unlock_group(group_id=''):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))
    if group_id:
        unlock_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='group',
                           data=[{'id': group_id, 'locked': {'set': 'false'}}])
        unlock_solr.update()

    redirect_url = 'superadmin'
    if get_redirect_target():
        redirect_url = get_redirect_target()

    return redirect(url_for(redirect_url))


@app.route('/redis/stats/<db>')
@login_required
def redis_stats(db='0'):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))

    if db == '0':
        storage = app.extensions['redis']['REDIS_CONSOLIDATE_PERSONS']

        return 'dbsize: %s' % storage.dbsize()
    elif db == '1':
        storage = app.extensions['redis']['REDIS_PUBLIST_CACHE']

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


@app.route('/redis/clean/<db>')
@login_required
def redis_clean(db='0'):
    if current_user.role != 'superadmin':
        flash(gettext('For SuperAdmins ONLY!!!'))
        return redirect(url_for('homepage'))

    if db == '0':
        storage = app.extensions['redis']['REDIS_CONSOLIDATE_PERSONS']
        storage.flushdb()
        return 'dbsize: %s' % storage.dbsize()
    elif db == '1':
        storage = app.extensions['redis']['REDIS_PUBLIST_CACHE']
        storage.flushdb()
        return 'dbsize: %s' % storage.dbsize()
    else:
        return 'No database with ID %s exists!' % db


@app.route('/consolidate_email/<affiliation>')
@login_required
def consolidate_email(affiliation=''):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    if affiliation:
        persons = []
        if affiliation == 'rub':
            query = '*:*'
            fquery = ['catalog:"Ruhr-Universität Bochum"']
            hb2_users_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='person', handler='query',
                                  query=query, facet='false', rows=100000,
                                  fquery=fquery)
            hb2_users_solr.request()
            persons = hb2_users_solr.results

        elif affiliation == 'tudo':
            query = '*:*'
            fquery = ['catalog:"Technische Universität Dortmund"']
            hb2_users_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='person', handler='query',
                                  query=query, facet='false', rows=100000,
                                  fquery=fquery)
            hb2_users_solr.request()
            persons = hb2_users_solr.results

        if len(persons) > 0:
            csv = 'ID; Name; RUBi; TUDo; E-Mail (IDM); E-Mail (Kontakt)\n'
            for person in persons:
                thedata = json.loads(person.get('wtf_json'))
                csv += '"%s"; "%s"; %s; %s; %s; "%s"\n' % (thedata.get('id'), thedata.get('name'), person.get('rubi'), person.get('tudo'), thedata.get('email'), thedata.get('contact'))

            resp = make_response(csv, 200)
            resp.headers['Content-Type'] = 'text/csv'
            return resp
        else:
            return make_response('No results', 404)

    else:
        return make_response('Please set affiliation parameter', 400)


# ---------- EXPORT ----------

@app.route('/export/openapc/<year>', methods=['GET'])
@csrf.exempt
def export_openapc(year=''):

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


# ---------- ORCID ----------


class OrcidForm(FlaskForm):
    read_limited = BooleanField(lazy_gettext('read limited'), validators=[Optional()], default='checked')
    update_activities = BooleanField(lazy_gettext('update activities'), validators=[Optional()], default='checked')
    update_person = BooleanField(lazy_gettext('update personal information'), validators=[Optional()], default='checked')


@app.route('/orcid2name/<orcid_id>')
@login_required
def orcid2name(orcid_id=''):
    if orcid_id:
        bio = requests.get('https://pub.orcid.org/%s/orcid-bio/' % orcid_id,
                           headers={'Accept': 'application/json'}).json()
        # logging.info(bio.get('orcid-profile').get('orcid-bio').get('personal-details').get('family-name'))
    return jsonify({'name': '%s, %s' % (
    bio.get('orcid-profile').get('orcid-bio').get('personal-details').get('family-name').get('value'),
    bio.get('orcid-profile').get('orcid-bio').get('personal-details').get('given-names').get('value'))})


@app.route('/orcid', methods=['GET', 'POST'])
@login_required
def orcid_start():

    if request.method == 'POST':
        read_limited = request.form.get('read_limited', False)
        update_activities = request.form.get('update_activities', False)
        update_person = request.form.get('update_person', False)

        # scope params
        orcid_scopes = []
        if read_limited:
            orcid_scopes.append('/read-limited')
        if update_activities:
            orcid_scopes.append('/activities/update')
        if update_person:
            orcid_scopes.append('/person/update')

        if len(orcid_scopes) == 0:
            flash(gettext('You haven\'t granted any of the scopes!'), 'error')
            return redirect(url_for('orcid_start'))
        else:
            # write selected scopes to hb2_users
            user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                             application=secrets.SOLR_APP, core='hb2_users',
                             data=[{'id': current_user.id, 'orcidscopes': {'set': orcid_scopes}}], facet='false')
            user_solr.update()
            # try to get authorization code
            # logging.info('current_user.affiliation = %s' % current_user.affiliation)
            sandbox = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox')
            client_id = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox_client_id')
            client_secret = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox_client_secret')
            redirect_uri = secrets.orcid_app_data.get(current_user.affiliation).get('redirect_uri')
            if not sandbox:
                client_id = secrets.orcid_app_data.get(current_user.affiliation).get('client_id')
                client_secret = secrets.orcid_app_data.get(current_user.affiliation).get('client_secret')

            api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

            url = api.get_login_url(orcid_scopes, '%s/%s' % (redirect_uri, url_for('orcid_login')),
                                    email=current_user.email)
            return redirect(url)

    # get ORCID and Token from Solr
    # logging.info('current_user.id = %s' % current_user.id)
    user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, application=secrets.SOLR_APP, core='hb2_users',
                     query='id:%s' % current_user.id, facet='false')
    user_solr.request()

    if user_solr.count() > 0:

        # flash(user_solr.results[0])

        orcid_id = ''
        if user_solr.results[0].get('orcidid'):
            orcid_id = user_solr.results[0].get('orcidid')
        orcid_access_token = ''
        if user_solr.results[0].get('orcidaccesstoken'):
            orcid_access_token = user_solr.results[0].get('orcidaccesstoken')
        orcid_refresh_token = ''
        if user_solr.results[0].get('orcidrefreshtoken'):
            orcid_refresh_token = user_solr.results[0].get('orcidrefreshtoken')
        orcid_token_revoked = False
        if user_solr.results[0].get('orcidtokenrevoked'):
            orcid_token_revoked = user_solr.results[0].get('orcidtokenrevoked')

        # flash('%s, %s, %s, %s' % (orcid_id, orcid_access_token, orcid_refresh_token, orcid_token_revoked))

        is_linked = False
        if len(orcid_id) > 0 and len(orcid_access_token) > 0 and not orcid_token_revoked:
            is_linked = True
            # flash('You are already linked to ORCID!')

        if is_linked:
            sandbox = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox')
            client_id = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox_client_id')
            client_secret = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox_client_secret')
            redirect_uri = secrets.orcid_app_data.get(current_user.affiliation).get('redirect_uri')
            if not sandbox:
                client_id = secrets.orcid_app_data.get(current_user.affiliation).get('client_id')
                client_secret = secrets.orcid_app_data.get(current_user.affiliation).get('client_secret')

            api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

            try:
                member_info = api.read_record_member(orcid_id=orcid_id, request_type='activities',
                                                     token=orcid_access_token)
                # TODO show linking information
                # flash('You have granted us rights to update your ORCID profile! %s' % current_user.orcidscopes)
            except RequestException as e:
                orcid_token_revoked = True
                # write true to hb2_users for orcidtokenrevoked field
                user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                 application=secrets.SOLR_APP, core='hb2_users',
                                 data=[{'id': current_user.id, 'orcidtokenrevoked': {'set': 'true'}}], facet='false')
                user_solr.update()
                flash('Your granted rights to your ORCID record are revoked!', 'danger')
        else:
            is_linked = False
            # flash('You are not linked to ORCID!', 'warning')

        form = OrcidForm()

        return render_template('orcid.html', form=form, header=lazy_gettext('Link to your ORCID iD'), site=theme(request.access_route),
                               is_linked=is_linked, token_revoked=orcid_token_revoked,
                               orcid_scopes=current_user.orcidscopes)


@app.route('/orcid/register', methods=['GET', 'POST'])
@login_required
def orcid_login():
    code = request.args.get('code', '')

    sandbox = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox')
    client_id = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox_client_id')
    client_secret = secrets.orcid_app_data.get(current_user.affiliation).get('sandbox_client_secret')
    redirect_uri = secrets.orcid_app_data.get(current_user.affiliation).get('redirect_uri')
    if not sandbox:
        client_id = secrets.orcid_app_data.get(current_user.affiliation).get('client_id')
        client_secret = secrets.orcid_app_data.get(current_user.affiliation).get('client_secret')

    api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

    if code == '':
        user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                         application=secrets.SOLR_APP, core='hb2_users',
                         data=[{'id': current_user.id, 'orcidtokenrevoked': {'set': 'true'}}], facet='false')
        user_solr.update()
        flash(gettext('You haven\'t granted the selected rights!'), 'error')
        logging.error('You haven\'t granted the selected rights! (code==\'\')')
        return redirect(url_for('orcid_start'))
    else:
        try:
            token = api.get_token_from_authorization_code(code, '%s/%s' % (redirect_uri, url_for('orcid_login')))
            orcid_id = token.get('orcid')
            logging.info('ORCID: %s' % orcid_id)
            logging.info('ORCID: token = %s' % token)

            # add orcid_id to person if exists. if not exists person then create an entity
            try:
                person_results = []

                query = 'email:%s' % current_user.email
                person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                   fields=['wtf_json'])
                person_solr.request()
                person_results = person_solr.results

                if len(person_results) == 0:

                    if '@rub.de' in current_user.email:
                        query = 'email:%s' % str(current_user.email).replace('@rub.de', '@ruhr-uni-bochum.de')
                        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                           fields=['wtf_json'])
                        person_solr.request()
                        person_results = person_solr.results
                    elif '@ruhr-uni-bochum.de' in current_user.email:
                        query = 'email:%s' % str(current_user.email).replace('@ruhr-uni-bochum.de', '@rub.de')
                        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                           fields=['wtf_json'])
                        person_solr.request()
                        person_results = person_solr.results
                    # TODO TU alternatives

                if len(person_results) == 0:
                    logging.info('keine Treffer zu email in person: %s' % current_user.email)
                    new_person_json = {}
                    new_person_json.setdefault('id', str(uuid.uuid4()))
                    new_person_json.setdefault('name', current_user.name)
                    new_person_json.setdefault('email', current_user.email)
                    new_person_json.setdefault('orcid', orcid_id)
                    new_person_json.setdefault('status', '')
                    if current_user.affiliation == 'tudo':
                        new_person_json.setdefault('tudo', True)
                    if current_user.affiliation == 'rub':
                        new_person_json.setdefault('rubi', True)
                    new_person_json.setdefault('created', timestamp())
                    new_person_json.setdefault('changed', timestamp())
                    new_person_json.setdefault('note', gettext('Added in linking process to ORCID record!'))
                    new_person_json.setdefault('owner', []).append(secrets.orcid_app_data.get(current_user.affiliation).get('orcid_contact_mail'))
                    new_person_json.setdefault('editorial_status', 'new')
                    if current_user.affiliation == 'tudo':
                        new_person_json.setdefault('catalog', []).append('Technische Universität Dortmund')
                    if current_user.affiliation == 'rub':
                        new_person_json.setdefault('catalog', []).append('Ruhr-Universität Bochum')

                    form = PersonAdminForm.from_json(new_person_json)

                    logging.info(form.data)

                    _person2solr(form, action='create')

                    query = 'id:%s' % new_person_json.get('id')
                    person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                       fields=['wtf_json'])
                    person_solr.request()
                    person_results = person_solr.results

                for doc in person_results:
                    myjson = json.loads(doc.get('wtf_json'))
                    # logging.info('id: %s' % myjson.get('id'))
                    lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, core='person',
                                            data=[{'id': myjson.get('id'), 'locked': {'set': 'true'}}])
                    lock_record_solr.update()

                    edit_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, query='id:%s' % myjson.get('id'),
                                            core='person', facet='false')
                    edit_person_solr.request()

                    thedata = json.loads(edit_person_solr.results[0].get('wtf_json'))

                    form = PersonAdminForm.from_json(thedata)
                    form.changed.data = timestamp()
                    form.orcid.data = orcid_id

                    _person2solr(form, action='update')
                    unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                              application=secrets.SOLR_APP, core='person',
                                              data=[{'id': myjson.get('id'), 'locked': {'set': 'false'}}])
                    unlock_record_solr.update()

                    # TODO if existing record contains external-ids
                    # then push them to the ORCID record if they don't exist there
                    if '/orcid-bio/update' in current_user.orcidscopes:
                        scopus_ids = myjson.get('scopus_id')
                        researcher_id = myjson.get('researcher_id')
                        gnd_id = myjson.get('gnd')

                # add orcid_token_data to hb2_users; orcid_token_revoked = True
                tmp = {
                    'id': current_user.id,
                    'orcidid': {'set': orcid_id},
                    'orcidaccesstoken': {'set': token.get('access_token')},
                    'orcidrefreshtoken': {'set': token.get('refresh_token')},
                    'orcidtokenrevoked': {'set': 'false'}
                }
                logging.info('ORCID: hb2_users.data = %s' % tmp)
                user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                 application=secrets.SOLR_APP, core='hb2_users',
                                 data=[tmp], facet='false')
                user_solr.update()

                # if current_user.orcid_scopes contains 'update_activities'
                if '/activities/update' in current_user.orcidscopes:
                    # add institution to employment if not already existing
                    doit = True
                    member_info = api.read_record_member(orcid_id=orcid_id, request_type='activities', token=token.get('access_token'))
                    if member_info.get('employments'):
                        for orga in member_info.get('employments').get('employment-summary'):
                            affilliation = {
                                'organization': {
                                    'address': orga.get('organization').get('address'),
                                    'name': orga.get('organization').get('name')
                                }
                            }
                            if json.dumps(secrets.orcid_app_data.get(current_user.affiliation).get('organization')) == json.dumps(affilliation):
                                doit = False
                    if doit:
                        api.add_record(orcid_id=orcid_id, token=token.get('access_token'), request_type='employment',
                                       data=secrets.orcid_app_data.get(current_user.affiliation).get('organization'))

            except AttributeError as e:
                logging.error(e)
            flash(gettext('Your institutional account %s is now linked to your ORCID iD %s!' % (current_user.id, orcid_id)))
            # flash(gettext('The response: %s' % token))
            # flash(gettext('We added the following data to our system: {%s, %s}!' % (token.get('access_token'), token.get('refresh_token'))))
            return redirect(url_for('orcid_start'))
        except RequestException as e:
            logging.error(e.response.text)
            flash(gettext('ORCID-ERROR: %s' % e.response.text), 'error')
            return redirect(url_for('orcid_start'))


@app.route('/orcid/linked_users/<affiliation>')
@login_required
def linked_users(affiliation=''):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    if affiliation:
        query = 'orcidscopes:[\'\' TO *]'
        fquery = ['affiliation:%s' % affiliation]
        hb2_users_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2_users', handler='query',
                              query=query, facet='false', rows=100000,
                              fquery=fquery)
        hb2_users_solr.request()

        csv = 'ID; ORCID iD; Name; E-Mail-Adresse; ORCID in Personendatesatz; ORCID token revoked; Recht 1; Recht 2; Recht 3\n'

        if len(hb2_users_solr.results) > 0:
            for hb2_user in hb2_users_solr.results:
                is_orcid_in_person_record = False
                if hb2_user.get('orcidid'):
                    persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='person', handler='query',
                                        query='orcid:%s' % hb2_user.get('orcidid'), facet='false')
                    persons_solr.request()
                    if len(persons_solr.results) > 0:
                        is_orcid_in_person_record = True
                csv += '%s; %s; "%s"; %s; %s; %s; %s\n' % (hb2_user.get('id'), hb2_user.get('orcidid'), hb2_user.get('name'), hb2_user.get('email'), is_orcid_in_person_record, hb2_user.get('orcidtokenrevoked'), '; '.join([str(x) for x in hb2_user.get('orcidscopes')]))

        query = 'orcidid:[\'\' TO *] AND -orcidscopes:[\'\' TO *]'
        fquery = ['affiliation:%s' % affiliation]
        hb2_users_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2_users', handler='query',
                              query=query, facet='false', rows=100000,
                              fquery=fquery)
        hb2_users_solr.request()

        if len(hb2_users_solr.results) > 0:
            for hb2_user in hb2_users_solr.results:
                is_orcid_in_person_record = False
                if hb2_user.get('orcidid'):
                    persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='person', handler='query',
                                        query='orcid:%s' % hb2_user.get('orcidid'), facet='false')
                    persons_solr.request()
                    if len(persons_solr.results) > 0:
                        is_orcid_in_person_record = True
                csv += '%s; %s; "%s"; %s; %s; %s; %s\n' % (hb2_user.get('id'), hb2_user.get('orcidid'), hb2_user.get('name'), hb2_user.get('email'), is_orcid_in_person_record, hb2_user.get('orcidtokenrevoked'), '; '.join([str(x) for x in hb2_user.get('orcidscopes')]))

        resp = make_response(csv, 200)
        resp.headers['Content-Type'] = 'text/csv'
        return resp

    else:
        return make_response('Please set affiliation parameter', 400)


@app.route('/orcid/link_failed/<affiliation>')
@login_required
def link_failed(affiliation=''):
    if current_user.role != 'admin' and current_user.role != 'superadmin':
        flash(gettext('For Admins ONLY!!!'))
        return redirect(url_for('homepage'))

    if affiliation:
        query = '-orcidid:[\'\' TO *] AND orcidscopes:[\'\' TO *]'
        fquery = ['role:user', 'affiliation:%s' % affiliation]
        hb2_users_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2_users', handler='query',
                              query=query, facet='false', rows=100000,
                              fquery=fquery)
        hb2_users_solr.request()

        if len(hb2_users_solr.results) > 0:
            csv = ''
            for hb2_user in hb2_users_solr.results:
                csv += '%s; %s; %s; "%s"\n' % (hb2_user.get('id'), hb2_user.get('name'), hb2_user.get('email'), hb2_user.get('orcidscopes'))

            resp = make_response(csv, 200)
            resp.headers['Content-Type'] = 'text/csv'
            return resp
        else:
            return make_response('No results', 404)

    else:
        return make_response('Please set affiliation parameter', 400)


# ---------- LOGIN / LOGOUT ----------


class UserNotFoundError(Exception):
    pass


class User(UserMixin):
    def __init__(self, id, role='', name='', email='', accesstoken='', gndid='', orcidid='', orcidaccesstoken='',
                 orcidrefreshtoken='', orcidtokenrevoked=False, affiliation='', orcidscopes=[]):
        self.id = id
        self.name = name
        self.role = role
        self.email = email
        self.gndid = gndid
        self.accesstoken = accesstoken
        self.affiliation = affiliation
        self.orcidid = orcidid
        self.orcidscopes = orcidscopes
        self.orcidaccesstoken = orcidaccesstoken
        self.orcidrefreshtoken = orcidrefreshtoken
        self.orcidtokenrevoked = orcidtokenrevoked

        user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                         application=secrets.SOLR_APP, core='hb2_users', query='id:%s' % id, facet='false')
        user_solr.request()

        if user_solr.count() > 0:
            _user = user_solr.results[0]
            self.name = _user.get('name')
            self.role = _user.get('role')
            self.email = _user.get('email')
            self.gndid = _user.get('gndid')
            self.accesstoken = _user.get('accesstoken')
            self.affiliation = _user.get('affiliation')
            self.orcidid = _user.get('orcidid')
            self.orcidscopes = _user.get('orcidscopes')
            self.orcidaccesstoken = _user.get('orcidaccesstoken')
            self.orcidrefreshtoken = _user.get('orcidrefreshtoken')
            self.orcidtokenrevoked = _user.get('orcidtokenrevoked')

    def __repr__(self):
        return '<User %s: %s>' % (self.id, self.name)

    @classmethod
    def get_user(self_class, id):
        user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                         application=secrets.SOLR_APP, core='hb2_users', query='id:%s' % id, facet='false')
        user_solr.request()

        return user_solr.results[0]

    @classmethod
    def get(self_class, id):
        try:
            return self_class(id)
        except UserNotFoundError:
            return None


class LoginForm(FlaskForm):
    username = StringField(lazy_gettext('Username'))
    password = PasswordField(lazy_gettext('Password'))
    wayf = HiddenField(lazy_gettext('Where Are You From?'))


@login_manager.user_loader
def load_user(id):
    return User.get(id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User(request.form.get('username'))
        # user_info = user.get_user(request.form.get('username'))
        next = get_redirect_target()
        if request.form.get('wayf') == 'bochum':
            authuser = requests.post('https://api.ub.rub.de/ldap/authenticate/',
                                     data={'nocheck': 'true',
                                           'userid': base64.b64encode(request.form.get('username').encode('ascii')),
                                           'passwd': base64.b64encode(
                                               request.form.get('password').encode('ascii'))}).json()
            # logging.info(authuser)
            if authuser.get('email'):
                accesstoken = make_secure_token(
                    base64.b64encode(request.form.get('username').encode('ascii')) + base64.b64encode(
                        request.form.get('password').encode('ascii')))

                user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                 application=secrets.SOLR_APP, core='hb2_users',
                                 query='accesstoken:%s' % accesstoken,
                                 facet='false')
                user_solr.request()
                if user_solr.count() == 0:
                    tmp = {}

                    # new user data for solr
                    tmp.setdefault('id', request.form.get('username').encode('ascii'))
                    tmp.setdefault('name', '%s, %s' % (authuser.get('last_name'), authuser.get('given_name')))
                    tmp.setdefault('email', authuser.get('email'))
                    if user.role == '' or user.role == 'user':
                        tmp.setdefault('role', 'user')
                    else:
                        tmp.setdefault('role', user.role)
                    tmp.setdefault('accesstoken', accesstoken)
                    tmp.setdefault('affiliation', 'rub')
                    tmp.setdefault('orcidid', user.orcidid)
                    tmp.setdefault('orcidscopes', user.orcidscopes)
                    tmp.setdefault('orcidaccesstoken', user.orcidaccesstoken)
                    tmp.setdefault('orcidrefreshtoken', user.orcidrefreshtoken)
                    tmp.setdefault('orcidtokenrevoked', user.orcidtokenrevoked)

                    new_user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                         application=secrets.SOLR_APP, core='hb2_users', data=[tmp], facet='false')
                    new_user_solr.update()

                    # update user data for login
                    user.name = '%s, %s' % (authuser.get('last_name'), authuser.get('given_name'))
                    user.email = authuser.get('email')
                    user.accesstoken = accesstoken
                    user.id = authuser.get('id')
                    user.affiliation = 'rub'

                login_user(user)

                return redirect(next or url_for('homepage'))
            else:
                flash(gettext("Username and Password Don't Match"), 'danger')
                return redirect('login')
        elif request.form.get('wayf') == 'dortmund':
            authuser = requests.post('https://api.ub.tu-dortmund.de/paia/auth/login',
                                     data={
                                         'username': request.form.get('username').encode('ascii'),
                                         'password': request.form.get('password').encode('ascii'),
                                         'grant_type': 'password',
                                     },
                                     headers={'Accept': 'application/json', 'Content-type': 'application/json'}).json()
            # logging.info(authuser)
            if authuser.get('access_token'):
                user_info = requests.get('https://api.ub.tu-dortmund.de/paia/core/%s' % authuser.get('patron'),
                                         headers={
                                             'Accept': 'application/json',
                                             'Authorization': '%s %s' % (
                                             authuser.get('token_type'), authuser.get('access_token'))
                                         }).json()
                # logging.info(user_info)
                user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT, 
                                 application=secrets.SOLR_APP, core='hb2_users',
                                 query='accesstoken:%s' % authuser.get('access_token'), facet='false')
                user_solr.request()
                if user_solr.count() == 0:

                    # new user data for solr
                    tmp = {}
                    tmp.setdefault('id', request.form.get('username'))
                    tmp.setdefault('name', user_info.get('name'))
                    tmp.setdefault('email', user_info.get('email'))
                    # TODO for repo: get faculty information
                    # TODO https://bitbucket.org/beno/python-sword2/wiki/Home
                    if user.role == '' or user.role == 'user':
                        tmp.setdefault('role', 'user')
                    else:
                        tmp.setdefault('role', user.role)
                    tmp.setdefault('accesstoken', authuser.get('access_token'))
                    tmp.setdefault('affiliation', 'tudo')
                    tmp.setdefault('orcidid', user.orcidid)
                    tmp.setdefault('orcidscopes', user.orcidscopes)
                    tmp.setdefault('orcidaccesstoken', user.orcidaccesstoken)
                    tmp.setdefault('orcidrefreshtoken', user.orcidrefreshtoken)
                    tmp.setdefault('orcidtokenrevoked', user.orcidtokenrevoked)

                    new_user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                         application=secrets.SOLR_APP, core='hb2_users', data=[tmp], facet='false')
                    new_user_solr.update()

                    # update user data for login
                    user.name = user_info.get('name')
                    user.email = user_info.get('email')
                    user.accesstoken = authuser.get('access_token')
                    user.id = request.form.get('username')
                    user.affiliation = 'tudo'

                login_user(user)

                return redirect(next or url_for('homepage'))
            else:
                flash(gettext("Username and Password Don't Match"), 'danger')
                return redirect('login')

    form = LoginForm()
    next = get_redirect_target()
    # return render_template('login.html', form=form, header='Sign In', next=next, orcid_sandbox_client_id=orcid_sandbox_client_id)
    return render_template('login.html', form=form, header='Sign In', next=next, site=theme(request.access_route))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('homepage')


ORCID_RE = re.compile('\d{4}-\d{4}-\d{4}-\d{4}')


# ---------- BASICS ----------

def str2bool(v):
    if str(v).lower() in ("yes", "true",  "True", "t", "1"):
        return True
    else:
        return False


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            # logging.info(type(error))
            if type(error) is list:
                message = error[0]
            else:
                message = error
            flash('Error in field "%s": %s' % (str(getattr(form, field).label.text).upper(), message), 'error')


def timestamp():
    date_string = str(datetime.datetime.now())[:-3]
    if date_string.endswith('0'):
        date_string = '%s1' % date_string[:-1]

    return date_string


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


def _diff_struct(a, b):
    diffs = ''
    for line in str(diff_dict(a, b)).split('\n'):
        if line.startswith('-'):
            line = line.lstrip('-')
            try:
                cat, val = line.split(': ')
                if val != "''," and cat != "'changed'":
                    diffs += Markup('<b>%s</b>: %s<br/>' % (cat.strip("'"), val.rstrip(',').strip("'")))
            except ValueError:
                pass
    return diffs


def is_safe_url(target):
    ref_url = parse.urlparse(request.host_url)
    test_url = parse.urlparse(parse.urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


def redirect_back(endpoint, **values):
    target = request.form['next']
    if not target or not is_safe_url(target):
        target = url_for(endpoint, **values)
    return redirect(target)


@app.route('/<agent>/<agent_id>/bibliography/<style>', methods=['GET'])
@csrf.exempt
def bibliography(agent='', agent_id='', style='harvard1'):
    """
        Getting a bibliography

        swagger_from_file: bibliography_doc/bibliography.yml
    """
    format = request.args.get('format', 'html')

    filter_by_year = request.args.get('filter_by_year', '')
    filter_by_type = request.args.get('filter_by_type', '')
    exclude_by_type = request.args.get('exclude_by_type', '')
    filter_by_pr = request.args.get('filter_by_pr', False)
    filter_by_ger = request.args.get('filter_by_ger', False)
    filter_by_eng = request.args.get('filter_by_eng', False)
    filter_by_current_members = request.args.get('filter_by_current_members', False)
    filter_by_former_members = request.args.get('filter_by_former_members', False)
    group_by_year = request.args.get('group_by_year', False)
    # logging.info('group_by_year = %s' % group_by_year)
    group_by_type = request.args.get('group_by_type', False)
    group_by_type_year = request.args.get('group_by_type_year', False)
    pubsort = request.args.get('pubsort', '')
    toc = request.args.get('toc', False)
    locale = request.args.get('locale', '')
    # TODO start-creationdate, end-creationdate >> Szenario Raumplanung

    reasoning = request.args.get('reasoning', False)
    refresh = request.args.get('refresh', False)

    formats = ['html', 'js', 'csl', 'pdf']
    agent_types = {
        'person': 'person',
        'research_group': 'organisation',
        'chair': 'organisation',
        'organisation': 'organisation',
        'working_group': 'group',
        'project': 'group',
    }
    pubsorts = ['stm', 'anh']
    STM_SORT = ['ArticleJournal', 'Chapter', 'Monograph', 'Journal', 'Series', 'Conference', 'Collection',
                'MultivolumeWork', 'SpecialIssue', 'Patent', 'Standard', 'Thesis', 'InternetDocument', 'Report', 'Lecture', 'Sonstiges',
                'ArticleNewspaper', 'PressRelease', 'RadioTVProgram', 'AudioVideoDocument',
                'ResearchData', 'Other']
    STM_LIST = {
        'ArticleJournal': '',
        'Chapter': '',
        'Monograph': '',
        'Journal': '',
        'Series': '',
        'Conference': '',
        'Collection': '',
        'MultivolumeWork': '',
        'SpecialIssue': '',
        'Patent': '',
        'Standard': '',
        'Thesis': '',
        'InternetDocument': '',
        'Report': '',
        'Lecture': '',
        'ArticleNewspaper': '',
        'PressRelease': '',
        'RadioTVProgram': '',
        'AudioVideoDocument': '',
        'ResearchData': '',
        'Other': '',
    }
    ANH_SORT = ['Monograph', 'ArticleJournal', 'ChapterInLegalCommentary', 'Chapter', 'LegalCommentary', 'Collection',
                 'MultivolumeWork', 'Conference', 'Edition', 'SpecialIssue', 'Journal', 'Series', 'Newspaper', 'Thesis',
                'ArticleNewspaper',
                'Lecture', 'Report', 'InternetDocument', 'RadioTVProgram', 'AudioVideoDocument',
                'PressRelease', 'ResearchData', 'Other']
    ANH_LIST = {
        'Monograph': '',
        'ArticleJournal': '',
        'ChapterInLegalCommentary': '',
        'Chapter': '',
        'LegalCommentary': '',
        'Collection': '',
        'MultivolumeWork': '',
        'Conference': '',
        'Edition': '',
        'SpecialIssue': '',
        'Journal': '',
        'Series': '',
        'Newspaper': '',
        'Thesis': '',
        'ArticleNewspaper': '',
        'Lecture': '',
        'Report': '',
        'InternetDocument': '',
        'RadioTVProgram': '',
        'AudioVideoDocument': '',
        'PressRelease': '',
        'ResearchData': '',
        'Other': '',
    }

    if format not in formats:
        return make_response('Bad request: format!', 400)
    elif agent not in agent_types.keys():
        return make_response('Bad request: agent!', 400)
    elif pubsort and pubsort not in pubsorts:
        return make_response('Bad request: pubsort!', 400)

    key = request.full_path.replace('&refresh=true', '').replace('?refresh=true', '?')
    # logging.debug('KEY: %s' % key)
    response = ''
    if not refresh:
        # request in cache?
        try:

            storage_publists_cache = app.extensions['redis']['REDIS_PUBLIST_CACHE']

            if storage_publists_cache.exists(key):
                response = storage_publists_cache.get(key)

        except Exception as e:
            logging.info('REDIS ERROR: %s' % e)

    if response == '':

        group = False
        group_field = ''
        group_limit = 100000
        if str2bool(group_by_year):
            group = True
            group_field = 'fdate'
        elif str2bool(group_by_type):
            group = True
            group_field = 'pubtype'

        filterquery = []
        if str2bool(filter_by_eng):
            filterquery.append('language:eng')
        elif str2bool(filter_by_ger):
            filterquery.append('language:ger')
        elif str2bool(filter_by_pr):
            filterquery.append('peer_reviewed:true')

        if filter_by_type != '':
            entries = filter_by_type.split('|')
            filter_string = ''
            for entry in entries:
                filter_string += 'pubtype:%s' % PUBTYPE_KEYS.get(entry.lower()) + '+OR+'
            filterquery.append(filter_string[:-4])

        if filter_by_year != '':
            filterquery.append('fdate:"%s"' % filter_by_year)

        if exclude_by_type:
            entries = exclude_by_type.split('|')
            for entry in entries:
                filterquery.append('-pubtype:"%s"' % PUBTYPE_KEYS.get(entry.lower()))

        query = ''
        results = []
        if agent_types.get(agent) == 'person':

            # get facet value
            actor_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, query='gnd:%s' % agent_id, export_field='wtf_json',
                              core=agent_types.get(agent))
            actor_solr.request()

            if len(actor_solr.results) == 0:
                return make_response('Not Found: Unknown Agent!', 404)
            else:
                name = actor_solr.results[0].get('name')

                query = 'pndid:%s' % agent_id
                # query = 'pnd:"%s%s%s"' % (agent_id, '%23', name)
                # logging.info('query=%s' % query)

        else:
            # get orga/group doc
            actor_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, query='id:%s' % agent_id,
                              export_field='wtf_json',
                              core=agent_types.get(agent))
            actor_solr.request()

            if actor_solr.results:

                name = actor_solr.results[0].get('pref_label')
                # logging.debug('name = %s' % name)

                if reasoning:
                    # logging.debug('reasoning: %s' % reasoning)
                    orgas = {}
                    orgas.setdefault(agent_id, name)
                    # get all children
                    if actor_solr.results[0].get('children'):
                        children = actor_solr.results[0].get('children')
                        for child_json in children:
                            child = json.loads(child_json)
                            orgas.setdefault(child.get('id'), child.get('label'))
                    query = ''
                    idx_o = 0
                    id_type = agent_types.get(agent)
                    if id_type == 'organisation':
                        id_type = 'affiliation'

                    for orga_id in orgas.keys():

                        fquery = ['gnd:[\'\' TO *]']

                        if not agent_types.get(agent) == 'person':
                            if filter_by_former_members:
                                fquery.append('personal_status:emeritus+OR+personal_status:alumnus')
                            elif filter_by_current_members:
                                fquery.append('-personal_status:emeritus')
                                fquery.append('-personal_status:alumnus')

                        member_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, query='%s_id:"%s"' % (id_type, orga_id),
                                           fquery=fquery, fields=['gnd', 'name'], rows=100000,
                                           core='person')
                        member_solr.request()

                        query_part = ''

                        if member_solr.results and len(member_solr.results) > 0:
                            idx_p = 0
                            for member in member_solr.results:
                                query_part += 'pnd:"%s%s%s"' % (member.get('gnd'), '%23', member.get('name'))
                                idx_p += 1
                                if idx_p < len(member_solr.results) and query_part != '':
                                    query_part += ' OR '

                            if query_part != '':
                                query += query_part

                        idx_o += 1
                        if idx_o < len(orgas) and query != '':
                            query += ' OR '

                    while query.endswith(' OR '):
                        query = query[:-4]

                    # logging.info('query=%s' % query)

                else:
                    logging.debug('reasoning: %s' % reasoning)
                    id_type = agent_types.get(agent)
                    if id_type == 'organisation':
                        id_type = 'affiliation'
                    query = '%s_id:%s' % (id_type, agent_id)
            else:
                return make_response('Not Found: Unknown Agent!', 404)

        biblist_id = str(uuid.uuid4())
        biblist = ''
        biblist_toc = ''
        biblist_coins = ''

        STM_TOC = {
            'ArticleJournal': '',
            'Chapter': '',
            'Monograph': '',
            'Journal': '',
            'Series': '',
            'Conference': '',
            'Collection': '',
            'MultivolumeWork': '',
            'SpecialIssue': '',
            'Patent': '',
            'Standard': '',
            'Thesis': '',
            'InternetDocument': '',
            'Report': '',
            'Lecture': '',
            'ArticleNewspaper': '',
            'PressRelease': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'ResearchData': '',
        }
        ANH_TOC = {
            'Monograph': '',
            'ArticleJournal': '',
            'ChapterInLegalCommentary': '',
            'Chapter': '',
            'LegalCommentary': '',
            'Collection': '',
            'MultivolumeWork': '',
            'Conference': '',
            'Edition': '',
            'SpecialIssue': '',
            'Journal': '',
            'Series': '',
            'Newspaper': '',
            'Thesis': '',
            'ArticleNewspaper': '',
            'Lecture': '',
            'Report': '',
            'InternetDocument': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'PressRelease': '',
            'ResearchData': '',
        }

        STM_COINS = {
            'ArticleJournal': '',
            'Chapter': '',
            'Monograph': '',
            'Journal': '',
            'Series': '',
            'Conference': '',
            'Collection': '',
            'MultivolumeWork': '',
            'SpecialIssue': '',
            'Patent': '',
            'Standard': '',
            'Thesis': '',
            'InternetDocument': '',
            'Report': '',
            'Lecture': '',
            'ArticleNewspaper': '',
            'PressRelease': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'ResearchData': '',
        }
        ANH_COINS = {
            'Monograph': '',
            'ArticleJournal': '',
            'ChapterInLegalCommentary': '',
            'Chapter': '',
            'LegalCommentary': '',
            'Collection': '',
            'MultivolumeWork': '',
            'Conference': '',
            'Edition': '',
            'SpecialIssue': '',
            'Journal': '',
            'Series': '',
            'Newspaper': '',
            'Thesis': '',
            'ArticleNewspaper': '',
            'Lecture': '',
            'Report': '',
            'InternetDocument': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'PressRelease': '',
            'ResearchData': '',
        }

        if group_by_type_year and not filter_by_year and not filter_by_type:

            facet_tree = ('pubtype', 'fdate')

            publist_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, handler='query',
                                query=query, fields=['wtf_json'], rows=0,
                                facet='true', facet_tree=facet_tree, facet_sort=False, facet_limit=-1,
                                sort='fdate asc', core='hb2')
            publist_solr.request()
            # logging.info('publist_solr.tree: %s' % json.dumps(publist_solr.tree, indent=4))

            list_cnt = 0
            for pubtype in publist_solr.tree.get('pubtype,fdate'):
                # logging.debug('pubtype = %s' % pubtype.get('value'))
                # logging.debug('pubtype = %s' % pubtype)
                year_list = ''
                year_coins = ''
                if pubtype.get('pivot'):
                    for year in pubtype.get('pivot')[::-1]:
                        # logging.debug('\t%s: %s' % (year.get('value'), year.get('count')))
                        filterquery = []
                        filterquery.append('fdate:%s' % year.get('value'))
                        filterquery.append('pubtype:%s' % pubtype.get('value'))
                        pivot_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                          application=secrets.SOLR_APP, handler='query',
                                          query=query, fields=['wtf_json'], rows=100000,
                                          fquery=filterquery, core='hb2')
                        pivot_solr.request()
                        results = pivot_solr.results
                        # logging.debug('PIVOT_PUB_LIST: %s' % results)

                        publist_docs = []
                        for result in results:
                            publist_docs.append(json.loads(result.get('wtf_json')))
                            year_coins += '<div class="coins"><span class="Z3988" title="%s"></span></div>' % openurl_processor.wtf_openurl(json.loads(result.get('wtf_json'))).replace('&', '&amp;')

                        if not group_by_type:
                            year_list += '<h5>%s</h5>' % year.get('value')
                        year_list += citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style)
                else:
                    filterquery = []
                    filterquery.append('pubtype:%s' % pubtype.get('value'))
                    pivot_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, handler='query',
                                      query=query, fields=['wtf_json'], rows=100000,
                                      fquery=filterquery, core='hb2')
                    pivot_solr.request()
                    results = pivot_solr.results
                    # logging.debug('PIVOT_PUB_LIST: %s' % results)

                    publist_docs = []
                    for result in results:
                        publist_docs.append(json.loads(result.get('wtf_json')))
                        year_coins += '<div class="coins"><span class="Z3988" title="%s"></span></div>' % openurl_processor.wtf_openurl(
                            json.loads(result.get('wtf_json'))).replace('&', '&amp;')

                    year_list += citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style)

                group_value = pubtype.get('value')
                if locale.startswith('de'):
                    group_value = display_vocabularies.PUBTYPE_GER.get(pubtype.get('value'))
                else:
                    group_value = display_vocabularies.PUBTYPE_ENG.get(pubtype.get('value'))

                list_cnt += 1
                header = '<h4 id="%s_%s">%s</h4>' % (biblist_id, list_cnt, group_value)
                footer = ''
                if toc:
                    back_string = 'Back to table of contents'
                    if locale.startswith('de'):
                        back_string = 'Zurück zum Inhaltsverzeichnis'
                    footer = '<div class="toc_return"><a href="#%s_citetoc">%s</a></div>' % (biblist_id, back_string)

                if pubsort == 'stm':
                    STM_LIST[pubtype.get('value')] = header + year_list + footer
                    STM_TOC[pubtype.get('value')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                    STM_COINS[pubtype.get('value')] = year_coins
                elif pubsort == 'anh':
                    ANH_LIST[pubtype.get('value')] = header + year_list + footer
                    ANH_TOC[pubtype.get('value')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                    ANH_COINS[pubtype.get('value')] = year_coins
                else:
                    biblist += header + year_list + footer
                    biblist_toc += '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                    biblist_coins += year_coins

            if pubsort == 'anh':
                # logging.debug(ANH_LIST)
                biblist = ''
                biblist_toc = ''
                for pubtype in ANH_SORT:
                    if ANH_LIST.get(pubtype):
                        biblist += ANH_LIST.get(pubtype)
                        biblist_toc += ANH_TOC.get(pubtype)
                        biblist_coins += ANH_COINS.get(pubtype)
            elif pubsort == 'stm':
                # logging.debug(STM_LIST)
                biblist = ''
                biblist_toc = ''
                for pubtype in STM_SORT:
                    if STM_LIST.get(pubtype):
                        biblist += STM_LIST.get(pubtype)
                        biblist_toc += STM_TOC.get(pubtype)
                        biblist_coins += STM_COINS.get(pubtype)

        else:

            publist_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, handler='query',
                                query=query, fields=['wtf_json'],
                                rows=100000, fquery=filterquery,
                                group=group, group_field=group_field, group_limit=group_limit,
                                sort='fdate desc',
                                core='hb2')
            publist_solr.request()
            results.extend(publist_solr.results)
            # print('publist_solr.results: %s' % results)

            publist_docs = []
            if group:
                biblist = ''
                list_cnt = 0
                for result in results:
                    # logging.debug('groupValue: %s' % result.get('groupValue'))
                    # logging.debug('numFound: %s' % result.get('doclist').get('numFound'))
                    # logging.debug('docs: %s' % result.get('doclist').get('docs'))

                    coins = ''
                    for doc in result.get('doclist').get('docs'):
                        publist_docs.append(json.loads(doc.get('wtf_json')))
                        coins += '<div class="coins"><span class="Z3988" title="%s"></span></div>' % openurl_processor.wtf_openurl(json.loads(doc.get('wtf_json'))).replace('&', '&amp;')

                    group_value = result.get('groupValue')
                    if str2bool(group_by_type):
                        if locale.startswith('de'):
                            group_value = display_vocabularies.PUBTYPE_GER.get(result.get('groupValue'))
                        else:
                            group_value = display_vocabularies.PUBTYPE_ENG.get(result.get('groupValue'))

                    list_cnt += 1
                    header = '<h4 id="%s_%s">%s</h4>' % (biblist_id, list_cnt, group_value)
                    footer = ''
                    if toc:
                        back_string = 'Back to table of contents'
                        if locale.startswith('de'):
                            back_string = 'Zurück zum Inhaltsverzeichnis'
                        footer = '<div class="toc_return"><a href="#%s_citetoc">%s</a></div>' % (biblist_id, back_string)

                    if str2bool(group_by_type):
                        if pubsort == 'stm':
                            STM_LIST[result.get('groupValue')] = header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                            STM_TOC[result.get('groupValue')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                            STM_COINS[result.get('groupValue')] = coins
                        elif pubsort == 'anh':
                            ANH_LIST[result.get('groupValue')] = header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                            ANH_TOC[result.get('groupValue')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                            ANH_COINS[result.get('groupValue')] = coins
                        else:
                            biblist += header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                            biblist_toc += '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                            biblist_coins += coins
                    elif str2bool(group_by_year):
                        biblist += header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                        biblist_toc += '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                        biblist_coins += coins
                    else:
                        biblist += header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer

                    if str2bool(group_by_type) and pubsort == 'anh':
                        # logging.debug(ANH_LIST)
                        biblist = ''
                        biblist_toc = ''
                        for pubtype in ANH_SORT:
                            if ANH_LIST.get(pubtype):
                                biblist += ANH_LIST.get(pubtype)
                                biblist_toc += ANH_TOC.get(pubtype)
                                biblist_coins += ANH_COINS.get(pubtype)
                    elif str2bool(group_by_type) and pubsort == 'stm':
                        # logging.debug(STM_LIST)
                        biblist = ''
                        biblist_toc = ''
                        for pubtype in STM_SORT:
                            if STM_LIST.get(pubtype):
                                biblist += STM_LIST.get(pubtype)
                                biblist_toc += STM_TOC.get(pubtype)
                                biblist_coins += STM_COINS.get(pubtype)

                    publist_docs = []

            else:
                for result in results:
                    publist_docs.append(json.loads(result.get('wtf_json')))

                biblist = citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style)

        response = ''

        if toc:
            response += '<ul id="%s_citetoc">' % biblist_id + biblist_toc + '</ul>'

        response += biblist + biblist_coins

    if response:
        try:

            storage_publists_cache = app.extensions['redis']['REDIS_PUBLIST_CACHE']

            storage_publists_cache.set(key, response)
            storage_publists_cache.hset(agent_id, key, timestamp())

        except Exception as e:
            logging.error('REDIS: %s' % e)

    return response


def citeproc_node(docs=None, format='html', locale='', style=''):

    locales_url = secrets.CITEPROC_LOCALES_FILE

    with open(locales_url) as data_file:
        locales = json.load(data_file)

    # load a CSL style (from the current directory)
    # logging.debug('LOCALE: %s' % locale)
    if locale not in locales.get('language-names').keys():
        locale = locales.get('primary-dialects').get(locale)
    # logging.debug('LOCALE: %s' % locale)

    citeproc_url = secrets.CITEPROC_SERVICE_URL % (format, style, locale)

    items = OrderedDict()
    for item in docs:
        items.setdefault(item.get('id'), item)

    response = requests.post(citeproc_url, data=json.dumps({'items': items}),
                             headers={'Content-type': 'application/json'})

    bib = response.content.decode()
    if format == 'html':
        urls = re.findall(urlmarker.URL_REGEX, bib)
        logging.info(urls)

        for url in list(set(urls)):
            bib = bib.replace(url, '<a href="%s">%s</a>' % (url.replace('http://dx.doi.org/', 'https://doi.org/'), url.replace('http://dx.doi.org/', 'https://doi.org/')))

        dois = re.findall(urlmarker.DOI_REGEX, bib)
        # logging.info('DOIs: %s' % dois)

        for doi in list(set(dois)):
            if doi.endswith('.'):
                doi = doi[:-1]
            elif doi.endswith('.</div>'):
                doi = doi[:-7]
            bib = bib.replace(doi, '<a href="https://doi.org/%s">%s</a>' % (doi.replace('doi:', ''), doi))

        dois = re.findall(urlmarker.DOI_REGEX_1, bib)
        # logging.info('DOIs: %s' % dois)

        for doi in list(set(dois)):
            if doi.endswith('.'):
                doi = doi[:-1]
            elif doi.endswith('.</div>'):
                doi = doi[:-7]
            bib = bib.replace(doi, '<a href="https://doi.org/%s">%s</a>' % (doi.replace('DOI: ', ''), doi))

    return bib


def render_bibliography(docs=None, format='html', locale='', style='', commit_link=False, commit_system=''):

    if docs is None:
        docs = []

    publist = ''
    # logging.debug('csl-docs: %s' % docs)
    if len(docs) > 0:

        locales_url = secrets.CITEPROC_LOCALES_FILE

        with open(locales_url) as data_file:
            locales = json.load(data_file)

        bib_source = CiteProcJSON(docs)
        # load a CSL style (from the current directory)
        locale = '%s/csl-locales/locales-%s' % (secrets.CSL_DATA_DIR, locales.get('primary-dialects').get(locale))
        # logging.info('locale: %s' % locale)
        bib_style = CitationStylesStyle('%s/csl/%s' % (secrets.CSL_DATA_DIR, style),
                                        locale=locale,
                                        validate=False)
        # Create the citeproc-py bibliography, passing it the:
        # * CitationStylesStyle,
        # * BibliographySource (CiteProcJSON in this case), and
        # * a formatter (plain, html, or you can write a custom formatter)
        bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.html)
        # get a list of the item ids and register them to the bibliography object

        def warn(citation_item):
            logging.warning(
                "WARNING: Reference with key '{}' not found in the bibliography.".format(citation_item.key)
            )

        for item in docs:
            citation = Citation([CitationItem(item.get('id'))])
            bibliography.register(citation)
            bibliography.cite(citation, warn)

        # And finally, the bibliography can be rendered.
        if format == 'html':
            publist += '<div class="csl-bib-body">'

        idx = 0
        for item in bibliography.bibliography():
            # TODO Formatierung
            # logging.info('CSL item: %s' % item)
            # logging.info('CSL item ID: %s' % docs[idx].get('id'))
            if format == 'html':
                publist += '<div class="csl-entry">'
                if commit_link:
                    publist += '<span class="glyphicon glyphicon-minus" aria-hidden="true"></span> '

            if format == 'html':
                urls = re.findall(urlmarker.URL_REGEX, str(item))
                # logging.info(urls)

                for url in urls:
                    item = item.replace(url, '<a href="%s">%s</a>' % (url, url))

            publist += str(item)

            if commit_link and commit_system:
                if commit_system == 'crossref':
                    publist += ' <span class="glyphicon glyphicon-transfer" aria-hidden="true"></span> <a href="%s?doi=%s">%s</a>' % (url_for("new_by_identifiers"), docs[idx].get('id'), lazy_gettext('Use this Record'))
                else:
                    publist += ' <span class="glyphicon glyphicon-transfer" aria-hidden="true"></span> <a href="%s?source=%s&id=%s">%s</a>' % (url_for("new_by_identifiers"), commit_system, docs[idx].get('id'), lazy_gettext('Use this Record'))

            if format == 'html':
                publist += '</div>'

            idx += 1

        if format == 'html':
            publist += '</div>'

    return publist


# TODO
def is_token_valid(token = ''):

    if token == 'Bearer %s' % secrets.API_KEY_SANDBOX:
        return True
    else:
        return False


@socketio.on('lock', namespace='/hb2')
def lock_message(message):
    print('Locked ' + message.get('data'))
    emit('locked', {'data': message['data']}, broadcast=True)


@socketio.on('unlock', namespace='/hb2')
def unlock_message(message):
    print(message)
    # resp = requests.get('http://127.0.0.1:8983/solr/hb2/query?q=id:%s&fl=editorial_status&omitHeader=true' % message.get('data')).json()
    # status = resp.get('response').get('docs')[0].get('editorial_status')
    # print(status)
    print('Unlocked ' + message.get('data'))
    # emit('unlocked', {'data': {'id': message.get('data'), 'status': status}}, broadcast=True)
    emit('unlocked', {'data': message.get('data')}, broadcast=True)


@socketio.on('connect', namespace='/hb2')
def connect():
    emit('my response', {'data': 'connected'})


@app.route('/contact')
def contact():
    site = theme(request.access_route)
    if site == 'bochum':
        return redirect('mailto:bibliographie-ub@rub.de')
    elif site == 'dortmund':
        return redirect('http://www.ub.tu-dortmund.de/mail-hsb.html')
    else:
        return redirect('mailto:bibliographie-ub@rub.de')


# if __name__ == '__main__':
#     app.run()

if __name__ == '__main__':
    socketio.run(app, port=secrets.APP_PORT)
