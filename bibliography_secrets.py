# The MIT License
#
#  Copyright 2016 UB Dortmund <api.ub@tu-dortmund.de>.
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

# ---- APP CONFIG ---- #
DIFFERENT_PROXY_PATH = True

DEBUG = True
DEBUG_KEY = '1cf7e937-c98b-4e80-ac65-ecf0bb2e5e86'

LOGFILE = 'log/publist.log'

APP_PORT = 5006

# ---- DOCS ---- #
SWAGGER_SCHEMES = ['http', 'https']
SWAGGER_HOST = 'localhost:5006'
SWAGGER_BASEPATH = '/'
SWAGGER_API_VERSION = ''
SWAGGER_TITLE = ''
SWAGGER_DESCRIPTION = ''

# ---- PERSISTENCE ---- #
SOLR_HOST = 'localhost'
SOLR_PORT = '5200'
SOLR_APP = 'solr'

REDIS_PUBLIST_CACHE_URL = 'redis://localhost:6379/1'
REDIS_PUBLIST_CACHE_HOST = 'localhost'
REDIS_PUBLIST_CACHE_PORT = 6379
REDIS_PUBLIST_CACHE_DB = 1

# ---- CITEPROC ---- #
CITEPROC_LOCALES_FILE = '/path/to/csl-locales/locales.json'
CITEPROC_SERVICE_URL = 'http://127.0.0.1:8085?responseformat=%s&style=%s&locale=%s'

