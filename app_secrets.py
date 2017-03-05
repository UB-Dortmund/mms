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

key = ''

contact_mail = ''

BOOTSTRAP_SERVE_LOCAL = False

APP_DEBUG = True
APP_BASE_URL = ''
APP_PORT = 5005
# This parameter allows to start the application without CSRF security (set to False).
# THIS IS NOT RECOMMENDED! (but sometime necessary)
APP_SECURITY = True

# To make the app run on a different path than root, set this to True and change your web server configuration accordingly.
# For nginx see e.g. https://gist.github.com/ubbochum/7b50facf1923fff61bc4
DIFFERENT_PROXY_PATH = False

SWAGGER_SCHEMES = ['https']
SWAGGER_HOST = 'localhost:5005'
SWAGGER_BASEPATH = '/'
SWAGGER_DESCRIPTION = ''

API_KEY_SANDBOX = ''

orcid_app_data = {
    'tudo': {
        'sandbox': True,
        'sandbox_client_id': '',
        'sandbox_client_secret': '',
        'client_id': '',
        'client_secret': '',
        'organization': {
            'name': '',
            'address': {
                'city': '',
                'region': '',
                'country': ''
            }
        },
        'orcid_contact_mail': ''
    }
}

orcid_scopes = [
    '/read-limited',
    '/person/update',
    '/activities/update',
]

CSL_DATA_DIR = '/home/hb2/csl'
CSL_LOCALES_REG = '/home/hb2/csl/locales/locales.json'

SOLR_HOST = '127.0.0.1'
SOLR_PORT = '8983'

SOLR_APP = 'solr'
SOLR_CORE = 'hb2'

SOLR_EXPORT_FIELD = 'wtf_json'
SOLR_ROWS = '20'
SOLR_SEARCH_FACETS = {
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
    'pubtype':
        {
            'type': 'terms',
            'field': 'pubtype'
        },
    'language':
        {
            'type': 'terms',
            'field': 'language'
        },
    'fperson':
        {
            'type': 'terms',
            'field': 'fperson'
        },
    'ftudo_orga':
        {
            'type': 'terms',
            'field': 'ftudo_orga'
        },
    'frubi_orga':
        {
            'type': 'terms',
            'field': 'frubi_orga'
        },
    'ftudo_pers':
        {
            'type': 'terms',
            'field': 'ftudo_pers'
        },
    'frubi_pers':
        {
            'type': 'terms',
            'field': 'frubi_pers'
        },
    'fdate':
        {
            'type': 'terms',
            'field': 'fdate',
            'sort': 'index desc'
        },
}
SOLR_PERSON_FACETS = {
    'faffiliation':
        {
            'type': 'terms',
            'field': 'faffiliation',
            'limit': 10
        },
    'fgroup':
        {
            'type': 'terms',
            'field': 'fgroup',
            'limit': 10
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
    'personal_status':
        {
            'type': 'terms',
            'field': 'personal_status',
            'limit': 15
        },
}
SOLR_ORGA_FACETS = {
    'destatis_id':
        {
            'type': 'terms',
            'field': 'destatis_id',
            'limit': 20
        },
    'fparent':
        {
            'type': 'terms',
            'field': 'fparent',
            'limit': 20
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
}
SOLR_GROUP_FACETS = {
    'destatis_id':
        {
            'type': 'terms',
            'field': 'destatis_id',
            'limit': 20
        },
    'fparent':
        {
            'type': 'terms',
            'field': 'fparent',
            'limit': 20
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
}

DASHBOARD_FACETS = {
    'pubtype':
        {
            'type': 'terms',
            'field': 'pubtype',
            'limit': 20
        },
    'subtype':
        {
            'type': 'terms',
            'field': 'subtype',
            'limit': 30
        },
    'fperson':
        {
            'type': 'terms',
            'field': 'fperson'
        },
    'fakultaet':
        {
            'type': 'terms',
            'field': 'fakultaet'
        },
    'publication_status':
        {
            'type': 'terms',
            'field': 'publication_status'
        },
    'editorial_status':
        {
            'type': 'terms',
            'field': 'editorial_status'
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
    'owner':
        {
            'type': 'terms',
            'field': 'owner'
        },
    'deskman':
        {
            'type': 'terms',
            'field': 'deskman'
        },
}
DASHBOARD_PERS_FACETS = {
    'faffiliation':
        {
            'type': 'terms',
            'field': 'faffiliation',
            'limit': 10
        },
    'fgroup':
        {
            'type': 'terms',
            'field': 'fgroup',
            'limit': 10
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
    'editorial_status':
        {
            'type': 'terms',
            'field': 'editorial_status',
            'limit': 20
        },
    'personal_status':
        {
            'type': 'terms',
            'field': 'personal_status',
            'limit': 20
        },
    'dwid':
        {
            'type': 'terms',
            'field': 'dwid',
            'limit': 10
        },
    'owner':
        {
            'type': 'terms',
            'field': 'owner'
        },
    'deskman':
        {
            'type': 'terms',
            'field': 'deskman'
        },
}
DASHBOARD_ORGA_FACETS = {
    'destatis_id':
        {
            'type': 'terms',
            'field': 'destatis_id',
            'limit': 20
        },
    'fparent':
        {
            'type': 'terms',
            'field': 'fparent',
            'limit': 20
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
    'editorial_status':
        {
            'type': 'terms',
            'field': 'editorial_status',
            'limit': 20
        },
    'owner':
        {
            'type': 'terms',
            'field': 'owner'
        },
    'deskman':
        {
            'type': 'terms',
            'field': 'deskman'
        },
}
DASHBOARD_GROUP_FACETS = {
    'destatis_id':
        {
            'type': 'terms',
            'field': 'destatis_id',
            'limit': 20
        },
    'fparent':
        {
            'type': 'terms',
            'field': 'fparent',
            'limit': 20
        },
    'catalog':
        {
            'type': 'terms',
            'field': 'catalog'
        },
    'editorial_status':
        {
            'type': 'terms',
            'field': 'editorial_status',
            'limit': 20
        },
    'owner':
        {
            'type': 'terms',
            'field': 'owner'
        },
    'deskman':
        {
            'type': 'terms',
            'field': 'deskman'
        },
}

REDIS_CONSOLIDATE_PERSONS_URL = 'redis://localhost:6379/0'
REDIS_CONSOLIDATE_PERSONS_HOST = 'localhost'
REDIS_CONSOLIDATE_PERSONS_PORT = 6379
REDIS_CONSOLIDATE_PERSONS_DB = 0

REDIS_PUBLIST_CACHE_URL = 'redis://localhost:6379/1'
REDIS_PUBLIST_CACHE_HOST = 'localhost'
REDIS_PUBLIST_CACHE_PORT = 6379
REDIS_PUBLIST_CACHE_DB = 1

TRAC_URL = ''
TRAC_USER = ''
TRAC_PW = ''

REDMINE_URL = ''
REDMINE_USER = ''
REDMINE_KEY = ''
REDMINE_PROJECT = ''

CITEPROC_LOCALES_FILE = ''
CITEPROC_SERVICE_URL = ''
