# Metadata Management System

The Metadata Management System is based on the Research Bibliography Platform, which is a joint project between
the University Library Bochum and the University Library Dortmund.
It is comprised of a web application for submitting, editing and searching bibliographic metadata about
publications and a linked data platform for structured querying of the data.

This is the succeeding project of [hb2flask](https://github.com/ubbochum/hb2_flask) and
its [fork](https://github.com/UB-Dortmund/hb2_flask).

## Structure

The platform is parted into several web services:

* the APP: a web application for submitting, editing and searching bibliographic metadata
* the API: a restful web service submitting, editing and searching bibliographic metadata
* the citations list service: a service to export individually specified citations lists or bibliographies
* the OAI-PMH data provider
* the export and statistics service

Furthermore there exists some batch processes for bulk imports from our previous system, for backups and
syncing data to third party platforms (e.g. ORCID or the Linked Data Platform of our institutions).

## Host Your Own Version

To host your own instance of the platform, you should first clone this repository.

Make a new virtual environment in a Python 3 installation (if you need to maintain several Python versions next to each
other, we recommend installing [pyenv](https://github.com/yyuu/pyenv)).

Install the dependencies into this environment with ```pip install -r requirements.txt```.

Edit the contents of ```*_secrets.py``` and save it as ```local_*_secrets.py```.

Further you have to setup an Apache Solr instance using the configurations in the `ìnit` folder of this project.

You can then run the web app with ```python app.py```, the api with ```python api.py``` and the
bibliography service with ```python bibliography.py```

## License

The MIT License

Copyright 2015-2017 University Library Bochum <bibliogaphie-ub@rub.de> and UB Dortmund <api.ub@tu-dortmund.de>.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
