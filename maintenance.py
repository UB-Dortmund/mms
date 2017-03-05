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
from urllib import parse

import simplejson as json
import wtforms_json
from datadiff import diff_dict
from flask import Flask, render_template, redirect, request, jsonify, flash, url_for, send_file
from flask_babel import Babel, lazy_gettext, gettext
from flask_bootstrap import Bootstrap
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_humanize import Humanize
from flask_wtf.csrf import CSRFProtect

from forms.forms import *

from utils import display_vocabularies

try:
    import local_app_secrets as secrets
except ImportError:
    import app_secrets as secrets

# logging.basicConfig(level=logging.INFO,
#                    format='%(asctime)s %(levelname)-4s %(message)s',
#                    datefmt='%a, %d %b %Y %H:%M:%S')


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


@app.route('/')
@app.route('/index')
@app.route('/homepage')
def homepage():
    return render_template('maintenance.html', header=lazy_gettext('Home'), site=theme(request.access_route), maintenance=True)


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
