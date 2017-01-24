# The MIT License
#
#  Copyright 2015 UB Bochum <bibliographie-ub@rub.de>.
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

import datetime
import uuid
from re import IGNORECASE

import pyisbn
from flask import Markup
from flask.ext.babel import lazy_gettext
from flask.ext.wtf import Form, RecaptchaField
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, SelectMultipleField, FileField, HiddenField, FieldList, FormField, PasswordField
from wtforms.validators import DataRequired, UUID, URL, Email, Optional, Length, Regexp, ValidationError
from wtforms.widgets import TextInput

from forms import forms_vocabularies


def Isbn(form, field):
    theisbn = pyisbn.Isbn(field.data.strip())
    if theisbn.validate() == False:
        raise ValidationError(lazy_gettext('Not a valid ISBN!'))


def timestamp():
    date_string = str(datetime.datetime.now())[:-3]
    if date_string.endswith('0'):
        date_string = '%s1' % date_string[:-1]

    return date_string


class CustomTextInput(TextInput):
    '''Enable both placeholder and help text descriptions.'''
    def __init__(self, **kwargs):
        self.params = kwargs
        super(CustomTextInput, self).__init__()

    def __call__(self, field, **kwargs):
        for param, value in self.params.items():
            kwargs.setdefault(param, value)
        return super(CustomTextInput, self).__call__(field, **kwargs)


class URIForm(Form):
    address = StringField(lazy_gettext('URI'), validators=[URL(), Optional()])
    label = StringField(lazy_gettext('Label'), validators=[Optional()])


class TableOfContentsForm(Form):
    uri = StringField('URI to Table of Contents', validators=[URL(), Optional()], widget=CustomTextInput(placeholder=lazy_gettext('e.g. http://d-nb.info/1035670232/04')))
    toc = TextAreaField(lazy_gettext('Table of Contents in textform'), validators=[Optional()])


class AbstractForm(Form):
    content = TextAreaField(lazy_gettext('Abstract'), validators=[Optional()])
    address = StringField(lazy_gettext('URL'), validators=[URL(), Optional()])
    language = SelectField(lazy_gettext('Language'), validators=[Optional()], choices=forms_vocabularies.LANGUAGES)
    shareable = BooleanField(lazy_gettext('Shareable'), validators=[Optional()], description=lazy_gettext('I hereby declare that I own the rights to publish this abstract.'))


class PersonForm(Form):
    name = StringField(lazy_gettext('Name'), validators=[Optional()],
                       widget=CustomTextInput(placeholder=lazy_gettext('Name, Given name')))
    # gnd = StringField(lazy_gettext('GND'),
    #                  validators=[Optional(), Regexp('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]')],
    #                  description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    gnd = StringField(lazy_gettext('GND'),
                      validators=[Optional()],
                      description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    orcid = StringField(lazy_gettext('ORCID'), validators=[Optional()],
                        description=Markup(lazy_gettext('<a href="https://orcid.org/orcid-search/search" target="_blank">Find in ORCID</a>')))
    role = SelectMultipleField(lazy_gettext('Role'))
    corresponding_author = BooleanField(lazy_gettext('Corresponding Author'), validators=[Optional()],
                                        description=lazy_gettext('The person handling the publication process'))
    rubi = BooleanField(lazy_gettext('RUB member'), validators=[Optional()])
    tudo = BooleanField(lazy_gettext('TUDO member'), validators=[Optional()])

    admin_only = ['gnd', 'rubi', 'tudo']


class PersonUserForm(Form):
    name = StringField(lazy_gettext('Name'), validators=[Optional()],
                       widget=CustomTextInput(placeholder=lazy_gettext('Name, Given name')))
    gnd = HiddenField(validators=[Optional()])
    orcid = HiddenField(validators=[Optional()])
    # author = BooleanField(lazy_gettext('Author'), validators=[Optional()])
    # editor = BooleanField(lazy_gettext('Editor'), validators=[Optional()])
    corresponding_author = BooleanField(lazy_gettext('Corresponding Author'), validators=[Optional()],
                                        description=lazy_gettext('The person handling the publication process'))
    rubi = BooleanField(lazy_gettext('RUB member'), validators=[Optional()])
    tudo = BooleanField(lazy_gettext('TUDO member'), validators=[Optional()])


class PatentPersonForm(PersonForm):
    role = SelectMultipleField(lazy_gettext('Role'), choices=forms_vocabularies.PATENT_PERS_ROLES)


class PersonAsEditorForm(PersonForm):
    role = SelectMultipleField(lazy_gettext('Role'))
    start_year = StringField(lazy_gettext('First Year'), validators=[Optional()])
    start_volume = StringField(lazy_gettext('First Volume'), validators=[Optional()])
    start_issue = StringField(lazy_gettext('First Issue'), validators=[Optional()])
    end_year = StringField(lazy_gettext('Last Year'), validators=[Optional()])
    end_volume = StringField(lazy_gettext('Last Volume'), validators=[Optional()])
    end_issue = StringField(lazy_gettext('Last Issue'), validators=[Optional()])
    corresponding_author = BooleanField(lazy_gettext('Corresponding Author'), validators=[Optional()], description=lazy_gettext('The person handling the publication process'))
    rubi = BooleanField(lazy_gettext('RUB member'), validators=[Optional()])
    tudo = BooleanField(lazy_gettext('TUDO member'), validators=[Optional()])


class OpenAccessForm(Form):
    project_identifier = StringField(lazy_gettext('Project Identifier'), validators=[URL(), Optional()], widget=CustomTextInput(placeholder=lazy_gettext('e.g. http://purl.org/info:eu-repo/grantAgreement/EC/FP7/12345P')))
    project_type = SelectField(lazy_gettext('Project Type'), choices=forms_vocabularies.PROJECT_TYPES, validators=[Optional()])
    publication_version = SelectField(lazy_gettext('Publication Version'), choices=[
        ('', lazy_gettext('Select a Publication Version')),
        ('accepted', lazy_gettext('Accepted')),
        ('draft', lazy_gettext('Draft')),
        ('forthcoming', lazy_gettext('Forthcoming')),
        ('legal', lazy_gettext('Legal')),
        ('non_peer_reviewed', lazy_gettext('Non Peer Reviewed')),
        ('peer-reviewed', lazy_gettext('Peer Reviewed')),
        ('published', lazy_gettext('Published')),
        ('rejected', lazy_gettext('Rejected')),
        ('unpublished', lazy_gettext('Unpublished')),
    ], validators=[Optional()])
    fee = BooleanField(lazy_gettext('Author Pays'))
    access_level = SelectField(lazy_gettext('Access Level'), choices=[
        ('', lazy_gettext('Select an Access Level')),
        ('closed', lazy_gettext('Closed Access')),
        ('embargoed', lazy_gettext('Embargoed Access')),
        ('restricted', lazy_gettext('Restricted Access')),
        ('open', lazy_gettext('Open Access')),
    ], validators=[Optional()])
    embargo_end_date = StringField(lazy_gettext('Embargo End Date'), validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')], widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')), description=lazy_gettext("If you don't know the month and/or day please use 01"))
    mime_type = SelectField(lazy_gettext('MIME-type'), choices=[
        ('pdf', lazy_gettext('application/pdf')),
        ('msword', lazy_gettext('application/msword')),
        ('x-latex', lazy_gettext('application/x-latex')),
        ('plain', lazy_gettext('text/plain')),
    ], validators=[Optional()])


class SEDForm(Form):
    start = StringField(lazy_gettext('Start Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')], widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    end = StringField(lazy_gettext('End Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                        widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    label = StringField(lazy_gettext('Label'), validators=[Optional()])
# TODO: Brauchen wir eine ID, und wenn ja, wohin?


class IDLForm(Form):
    id = StringField(lazy_gettext('ID'), validators=[Optional()])
    label = StringField(lazy_gettext('Label'), validators=[Optional()])


class FundsForm(Form):
    organisation = StringField(lazy_gettext('Funds Administration'))
    organisation_id = StringField(lazy_gettext('Funds Administration ID'),
                                 description=lazy_gettext('e.g. GND ID of the Funds Administration'))
    project_id = StringField(lazy_gettext('Funds Administration Project ID'),
                             description=lazy_gettext('Project ID given by the Funds Administration'))


class IssueForm(SEDForm):
    pass


class AwardForm(SEDForm):
    pass


class CVForm(SEDForm):
    pass


class MembershipForm(SEDForm):
    pass


class ProjectForm(SEDForm):
    project_id = StringField(lazy_gettext('Project ID'), validators=[Optional()])
    project_type = SelectField('Project Type', choices=forms_vocabularies.PROJECT_TYPES, validators=[Optional()])


class AffiliationForm(Form):
    organisation_id = StringField(lazy_gettext('ID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    start = StringField(lazy_gettext('Start Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                        widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    end = StringField(lazy_gettext('End Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                      widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    pref_label = StringField(lazy_gettext('Label'), validators=[Optional()])


class GroupForm(Form):
    group_id = StringField(lazy_gettext('ID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    start = StringField(lazy_gettext('Start Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                        widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    end = StringField(lazy_gettext('End Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                      widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    pref_label = StringField(lazy_gettext('Label'), validators=[Optional()])


class ThesisProfileForm(Form):
    title = StringField(lazy_gettext('Title'), validators=[Optional()])
    year = StringField(lazy_gettext('Year'), validators=[Optional()])
    thesis_type = SelectField(lazy_gettext('Type'), choices=[
        ('', lazy_gettext('Select a Thesis Type')),
        ('m', lazy_gettext('M.A. Thesis')),
        ('d', lazy_gettext('M.Sc. Thesis')),
        ('p', lazy_gettext('Doctoral Thesis')),
        ('h', lazy_gettext('Professorial Dissertation')),
    ])


class URLProfileForm(Form):
    # url = FieldList(StringField(lazy_gettext('URL'), validators=[URL(), Optional()]), min_entries=1)
    url = StringField(lazy_gettext('URL'), validators=[URL(), Optional()])
    label = SelectField(lazy_gettext('Label'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Label for the URL')),
        ('hp', lazy_gettext('Homepage')),
        ('rg', lazy_gettext('ResearchGate')),
        ('ri', lazy_gettext('ResearcherID')),
        ('an', lazy_gettext('AcademiaNet')),
        ('ae', lazy_gettext('Academia.edu')),
        ('wp', lazy_gettext('Wikipedia')),
        ('xi', lazy_gettext('Xing')),
        ('li', lazy_gettext('LinkedIn')),
        ('bl', lazy_gettext('Blog')),
        ('fb', lazy_gettext('Facebook')),
        ('tw', lazy_gettext('Twitter')),
        ('ic', lazy_gettext('identi.ca')),
        ('zt', lazy_gettext('Zotero')),
        ('md', lazy_gettext('Mendeley')),
        ('lg', lazy_gettext('Logo')),
        ('mi', lazy_gettext('Other')),
    ])


class PersonFromGndForm(Form):
    # gnd = StringField(lazy_gettext('GND'), validators=[DataRequired(), Regexp('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]')], description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    gnd = StringField(lazy_gettext('GND'), validators=[DataRequired()], description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))


class PersonAdminForm(Form):
    salutation = SelectField(lazy_gettext('Salutation'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Salutation')),
        ('m', lazy_gettext('Mr.')),
        ('f', lazy_gettext('Mrs./Ms.')),
    ])
    name = StringField(lazy_gettext('Name'), widget=CustomTextInput(placeholder=lazy_gettext('Family Name, Given Name')))
    also_known_as = FieldList(StringField(lazy_gettext('Also known as'), validators=[Optional()]), min_entries=1)
    email = StringField(lazy_gettext('E-Mail (IDM)'), validators=[Optional()],
                        widget=CustomTextInput(placeholder=lazy_gettext('Your institutional e-mail address')))
    contact = StringField(lazy_gettext('E-Mail (Contact)'), validators=[Optional()],
                          widget=CustomTextInput(placeholder=lazy_gettext('Your contact e-mail address')))
    account = FieldList(StringField(lazy_gettext('Account'), validators=[Optional(), Length(min=7, max=7)], widget=CustomTextInput(placeholder=lazy_gettext('Your 7-digit account number'))))
    dwid = StringField(lazy_gettext('Verwaltungs-ID'), validators=[Optional()])
    affiliation = FieldList(FormField(AffiliationForm), min_entries=1)
    group = FieldList(FormField(GroupForm), min_entries=1)
    url = FieldList(FormField(URLProfileForm), min_entries=1)

    # gnd = StringField(lazy_gettext('GND'),
    #                  validators=[Optional(),
    #                              Regexp('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]', message=lazy_gettext('Invalid value!'))],
    #                  description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    gnd = StringField(lazy_gettext('GND'),
                      validators=[Optional()],
                      description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    orcid = StringField(lazy_gettext('ORCID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="https://orcid.org/orcid-search/search" target="_blank">Find in ORCID</a>')))
    viaf = StringField(lazy_gettext('VIAF'), validators=[Optional()], description=Markup(lazy_gettext('<a href="http://www.viaf.org" target="_blank">Find in VIAF</a>')))
    isni = StringField(lazy_gettext('ISNI'), validators=[Optional()], description=Markup(lazy_gettext('<a href="http://www.isni.org" target="_blank">Find in ISNI</a>')))
    researcher_id = StringField(lazy_gettext('Researcher ID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="http://www.researcherid.com/ViewProfileSearch.action" target="_blank">Find in Researcher ID</a>')))
    # scopus_id = StringField(lazy_gettext('Scopus Author ID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="https://www.scopus.com/search/form/authorFreeLookup.uri" target="_blank">Find in Scopus Author ID</a>')))
    scopus_id = FieldList(StringField(lazy_gettext('Scopus Author ID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="https://www.scopus.com/search/form/authorFreeLookup.uri" target="_blank">Find in Scopus Author ID</a>'))), min_entries=1)
    arxiv_id = StringField(lazy_gettext('ArXiv Author ID'), validators=[Optional()], description=Markup(lazy_gettext('<a href="http://arxiv.org/find" target="_blank">Find in ArXiv Author ID</a>')))
    research_interest = FieldList(StringField(lazy_gettext('Research Interest')), validators=[Optional()], min_entries=1)

    status = SelectMultipleField(lazy_gettext('Status'), choices=forms_vocabularies.PERS_STATUS_MAP, description=lazy_gettext('Choose one or more Status'))

    note = TextAreaField(lazy_gettext('Note'), validators=[Optional()],
                             description=lazy_gettext('Commentary on the person'))
    data_supplied = StringField(lazy_gettext('Data Supplied'), validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')],
                              description=lazy_gettext('The date of the latest data delivery'),
                                widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))

    editorial_status = SelectField(lazy_gettext('Editorial Status'), validators=[DataRequired()], choices=[
        ('', lazy_gettext('Select an Editorial Status')),
        ('new', lazy_gettext('New')),
        ('in_process', lazy_gettext('In Process')),
        ('processed', lazy_gettext('Processed')),
        ('final_editing', lazy_gettext('Final Editing')),
        ('finalized', lazy_gettext('Finalized')),
        ('imported', lazy_gettext('Imported')),
        ('deleted', lazy_gettext('Deleted')),
    ], default='new')
    # catalog = FieldList(StringField(lazy_gettext('Data Catalog'), validators=[DataRequired()]), min_entries=1)
    catalog = SelectMultipleField(lazy_gettext('Data Catalog'), validators=[DataRequired()], choices=[
        ('Ruhr-Universität Bochum', lazy_gettext('Ruhr-Universität Bochum')),
        ('Technische Universität Dortmund', lazy_gettext('Technische Universität Dortmund')),
        ('Temporäre Daten', lazy_gettext('Temporäre Daten')),
    ], description=lazy_gettext('Choose one or more DataCatalog'))
    created = StringField(lazy_gettext('Record Creation Date'), widget=CustomTextInput(readonly='readonly'))
    changed = StringField(lazy_gettext('Record Change Date'), widget=CustomTextInput(readonly='readonly'))
    id = StringField(lazy_gettext('ID'), widget=CustomTextInput(readonly='readonly'))
    owner = FieldList(StringField(lazy_gettext('Owner'), validators=[DataRequired()]), min_entries=1)
    deskman = StringField(lazy_gettext('Deskman'), validators=[Optional()], widget=CustomTextInput(admin_only='admin_only'))

    rubi = BooleanField(lazy_gettext('RUB member'), validators=[Optional()])
    tudo = BooleanField(lazy_gettext('TUDO member'), validators=[Optional()])

    same_as = FieldList(StringField(lazy_gettext('Same As'), validators=[Optional()]), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.salutation, self.name, self.also_known_as, self.account, self.email, self.contact,
                       self.status,
                       self.research_interest, self.url], 'label': lazy_gettext('Basic')},
            {'group': [self.gnd, self.orcid, self.dwid, self.viaf, self.isni, self.researcher_id, self.scopus_id,
                       self.arxiv_id], 'label': lazy_gettext('IDs')},
            {'group': [self.affiliation, self.group], 'label': lazy_gettext('Affiliation')},
            {'group': [self.note, self.data_supplied], 'label': lazy_gettext('Notes')},
            {'group': [self.id, self.created, self.changed, self.editorial_status, self.catalog, self.owner,
                       self.deskman, self.same_as], 'label': lazy_gettext('Administrative')},
        ]


class DestatisForm(IDLForm):
    pass


class AccountForm(IDLForm):
    pass


class ChildForm(Form):
    child_id = StringField(lazy_gettext('ID'), validators=[Optional()])
    child_label = StringField(lazy_gettext('Label'), validators=[Optional()])


class ParentForm(Form):
    parent_id = StringField(lazy_gettext('ID'))
    parent_label = StringField(lazy_gettext('Label'))


class ProjectMemberForm(Form):
    project_id = StringField(lazy_gettext('ID'))
    project_label = StringField(lazy_gettext('Label'))


class PartnerForm(Form):
    partner_id = StringField(lazy_gettext('ID'))
    partner_label = StringField(lazy_gettext('Label'))


class OrgaAdminForm(Form):
    pref_label = StringField(lazy_gettext('Label'))
    id = StringField(lazy_gettext('ID'), validators=[Optional()], widget=CustomTextInput(readonly='readonly'))
    dwid = FieldList(StringField(lazy_gettext('Verwaltungs-ID')), min_entries=1)
    gnd = StringField(lazy_gettext('GND'),
                      validators=[Optional(), Regexp('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]', message=lazy_gettext('Invalid value!'))],
                      description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    start_date = StringField(lazy_gettext('Start Date'),
                             validators=[Optional(), Regexp('[12]\d{3}|[12]\d{3}-[01]\d|[12]\d{3}-[01]\d-[0123]\d')],
                             widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    end_date = StringField(lazy_gettext('End Date'),
                           validators=[Optional(), Regexp('[12]\d{3}|[12]\d{3}-[01]\d|[12]\d{3}-[01]\d-[0123]\d')],
                           widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    correction_request = StringField(lazy_gettext('Correction Request'))
    owner = FieldList(StringField(lazy_gettext('Owner')), min_entries=1)
    editorial_status = SelectField(lazy_gettext('Editorial Status'), validators=[DataRequired()],
                                   choices=forms_vocabularies.EDITORIAL_STATUS, default='new')
    catalog = SelectMultipleField(lazy_gettext('Data Catalog'), validators=[DataRequired()], choices=forms_vocabularies.CATALOGS,
                                  description=lazy_gettext('Choose one or more DataCatalog'))
    created = StringField(lazy_gettext('Record Creation Date'), widget=CustomTextInput(readonly='readonly'))
    changed = StringField(lazy_gettext('Record Change Date'), widget=CustomTextInput(readonly='readonly'))
    deskman = StringField(lazy_gettext('Deskman'), validators=[Optional()], widget=CustomTextInput(admin_only='admin_only'))
    destatis = FieldList(FormField(DestatisForm), min_entries=1)
    url = FieldList(FormField(URLProfileForm), min_entries=1)
    note = TextAreaField(lazy_gettext('Notes'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('Please put any information that does not fit other fields here.')))

    parent = FieldList(FormField(ParentForm), min_entries=1, max_entries=1)
    children = FieldList(FormField(ChildForm), min_entries=1)
    projects = FieldList(FormField(ProjectMemberForm), min_entries=1)
    same_as = FieldList(StringField(lazy_gettext('Same As'), validators=[Optional()]), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pref_label, self.dwid, self.gnd, self.correction_request, self.start_date,
                       self.end_date, self.url, self.note],
             'label': lazy_gettext('Basic')},
            {'group': [self.parent, self.children, self.projects],
             'label': lazy_gettext('Relations')},
            {'group': [self.destatis],
             'label': lazy_gettext('Destatis')},
            {'group': [self.id, self.created, self.changed, self.editorial_status, self.catalog, self.owner, self.deskman,
                       self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class GroupAdminForm(Form):
    pref_label = StringField(lazy_gettext('Label'))
    id = StringField(lazy_gettext('ID'), validators=[Optional()], widget=CustomTextInput(readonly='readonly'))
    description = TextAreaField(lazy_gettext('Description'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('Please put any information that does not fit other fields here.')))
    gnd = StringField(lazy_gettext('GND'),
                      validators=[Optional(), Regexp('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]', message=lazy_gettext('Invalid value!'))],
                      description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    funds = FieldList(FormField(FundsForm), min_entries=1)
    url = FieldList(FormField(URLProfileForm), min_entries=1)
    start_date = StringField(lazy_gettext('Start Date'),
                             validators=[Optional(), Regexp('[12]\d{3}|[12]\d{3}-[01]\d|[12]\d{3}-[01]\d-[0123]\d')],
                             widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    end_date = StringField(lazy_gettext('End Date'),
                           validators=[Optional(), Regexp('[12]\d{3}|[12]\d{3}-[01]\d|[12]\d{3}-[01]\d-[0123]\d')],
                           widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    correction_request = StringField(lazy_gettext('Correction Request'))
    owner = FieldList(StringField(lazy_gettext('Owner')), min_entries=1)
    editorial_status = SelectField(lazy_gettext('Editorial Status'), validators=[DataRequired()],
                                   choices=forms_vocabularies.EDITORIAL_STATUS, default='new')
    catalog = SelectMultipleField(lazy_gettext('Data Catalog'), validators=[DataRequired()], choices=forms_vocabularies.CATALOGS,
                                  description=lazy_gettext('Choose one or more DataCatalog'))
    created = StringField(lazy_gettext('Record Creation Date'), widget=CustomTextInput(readonly='readonly'))
    changed = StringField(lazy_gettext('Record Change Date'), widget=CustomTextInput(readonly='readonly'))
    deskman = StringField(lazy_gettext('Deskman'), validators=[Optional()], widget=CustomTextInput(admin_only='admin_only'))
    destatis = FieldList(FormField(DestatisForm), min_entries=1)
    note = TextAreaField(lazy_gettext('Notes'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('Please put any information that does not fit other fields here.')))

    # parent_id = StringField(lazy_gettext('Parent ID'))
    # parent_label = StringField(lazy_gettext('Parent Label'))
    parent = FieldList(FormField(ParentForm), min_entries=1, max_entries=1)
    children = FieldList(FormField(ChildForm), min_entries=1)
    partners = FieldList(FormField(PartnerForm), min_entries=1)

    same_as = FieldList(StringField(lazy_gettext('Same As'), validators=[Optional()]), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pref_label, self.gnd, self.description, self.start_date, self.end_date, self.url, self.note],
             'label': lazy_gettext('Basic')},
            {'group': [self.funds],
             'label': lazy_gettext('Funds')},
            {'group': [self.parent, self.children, self.partners],
             'label': lazy_gettext('Relations')},
            {'group': [self.destatis],
             'label': lazy_gettext('Destatis')},
            {'group': [self.id, self.created, self.changed, self.editorial_status, self.catalog, self.owner, self.deskman,
                       self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class GroupAdminUserForm(GroupAdminForm):
    id = HiddenField(validators=[UUID(), Optional()], default=str(uuid.uuid4))
    created = HiddenField(default=timestamp())
    changed = HiddenField(default=timestamp())
    catalog = SelectMultipleField(lazy_gettext('Data Catalog'), choices=forms_vocabularies.CATALOGS,
                                  description=lazy_gettext('Choose one or more DataCatalog'))

    def simple_groups(self):
        yield [
            {'group': [self.pref_label, self.description, self.start_date, self.end_date, self.url,
                       self.note, self.id, self.created, self.changed],
             'label': lazy_gettext('Working group details')},
            {'group': [self.funds],
             'label': lazy_gettext('Funds')},
        ]


class PersonProfileForm(PersonForm):
    image = FileField(lazy_gettext('Image'))
    url = FieldList(StringField('URL', validators=[URL(), Optional()]), min_entries=1)


class CorporationForm(Form):
    name = StringField(lazy_gettext('Name'))
    role = SelectMultipleField(lazy_gettext('Role'), choices=forms_vocabularies.CORP_ROLES)

    gnd = StringField(lazy_gettext('GND'), validators=[Optional(), Regexp('(1|10)\d{7}[0-9X]|[47]\d{6}-\d|[1-9]\d{0,7}-[0-9X]|3\d{7}[0-9X]')], description=Markup(lazy_gettext('<a href="https://portal.d-nb.de/opac.htm?method=showOptions#top" target="_blank">Find in GND</a>')))
    viaf = StringField(lazy_gettext('VIAF'), validators=[Optional()])
    isni = StringField(lazy_gettext('ISNI'), validators=[Optional()])

    rubi = BooleanField(lazy_gettext('RUB member'), validators=[Optional()])
    tudo = BooleanField(lazy_gettext('TUDO member'), validators=[Optional()])


class CorporationUserForm(Form):
    name = StringField(lazy_gettext('Name'))
    gnd = HiddenField(validators=[Optional()])

    rubi = BooleanField(lazy_gettext('RUB member'), validators=[Optional()])
    tudo = BooleanField(lazy_gettext('TUDO member'), validators=[Optional()])


class PatentCorporationForm(CorporationForm):
    role = SelectMultipleField(lazy_gettext('Role'), choices=forms_vocabularies.PATENT_CORP_ROLES)


class CorporationAsEditorForm(CorporationForm):
    role = SelectMultipleField(lazy_gettext('Role'), choices=forms_vocabularies.CORP_ROLES)
    start_year = StringField(lazy_gettext('First Year'), validators=[Optional()])
    start_volume = StringField(lazy_gettext('First Volume'), validators=[Optional()])
    start_issue = StringField(lazy_gettext('First Issue'), validators=[Optional()])
    end_year = StringField(lazy_gettext('Last Year'), validators=[Optional()])
    end_volume = StringField(lazy_gettext('Last Volume'), validators=[Optional()])
    end_issue = StringField(lazy_gettext('Last Issue'), validators=[Optional()])


class EventForm(Form):
    event_name = StringField(lazy_gettext('Name of the Event'), validators=[Optional()])
    event_startdate = StringField(lazy_gettext('First day of the Event'),
                                  validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')],
                                  widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')),
                                  description=lazy_gettext("If you don't know the month and/or day please use 01"))
    event_enddate = StringField(lazy_gettext('Last day of the Event'),
                                validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')],
                                widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')),
                                description=lazy_gettext("If you don't know the month and/or day please use 01"))
    event_place = StringField(lazy_gettext('Location of the Event'), validators=[Optional()])
    event_numbering = StringField(lazy_gettext('Numbering of the Event'), validators=[Optional()])


class HasPartForm(Form):
    has_part = StringField(lazy_gettext('Has Part'))


class IsPartOfForm(Form):
    is_part_of = StringField(lazy_gettext('Is Part of'))
    volume = StringField(lazy_gettext('Volume'))


class SpecialIssueRelationForm(IsPartOfForm):
    is_part_of = StringField(lazy_gettext('Is Part of'))
    volume = StringField(lazy_gettext('Volume'))
    issue = StringField(lazy_gettext('Issue'))


class OtherVersionForm(Form):
    other_version = StringField(lazy_gettext('Other Version'))


class OtherRelationForm(IsPartOfForm):
    page_first = StringField(lazy_gettext('First Page'))
    page_last = StringField(lazy_gettext('Last Page'))


class ChapterRelationForm(IsPartOfForm):
    page_first = StringField(lazy_gettext('First Page'))
    page_last = StringField(lazy_gettext('Last Page'))


class ArticleRelationForm(IsPartOfForm):
    # For reasons of ordering we don't inherit from ChapterRelationForm here...
    volume = StringField(lazy_gettext('Volume / Year'))
    issue = StringField(lazy_gettext('Issue'))
    page_first = StringField(lazy_gettext('First Page'))
    page_last = StringField(lazy_gettext('Last Page'))


class NewspaperRelationForm(IsPartOfForm):
    # For reasons of ordering we don't inherit from ChapterRelationForm here...
    volume = StringField(lazy_gettext('Volume'))
    issue = StringField(lazy_gettext('Edition'), widget=CustomTextInput(
        placeholder=lazy_gettext('Name or number of the edition that the article was published in')))
    page_first = StringField(lazy_gettext('First Page'))
    page_last = StringField(lazy_gettext('Last Page'))


class ContainerRelationForm(IsPartOfForm):
    volume = StringField(lazy_gettext('Volume'), validators=[Optional()])


class MonographRelationForm(ContainerRelationForm):
    pass


class OtherTitleForm(Form):
    other_title = StringField(lazy_gettext('Other Title'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('translated title, parallel title or EST of the work')))
    language = SelectField(lazy_gettext('Language'), validators=[Optional()], choices=forms_vocabularies.LANGUAGES)


class OrcidSyncForm(Form):

    orcid_put_code = StringField(lazy_gettext('ORCiD PutCode'), widget=CustomTextInput(readonly='readonly', placeholder=(lazy_gettext('ID of a work in ORCID record - automatically managed'))))
    orcid_id = StringField(lazy_gettext('for ORCiD ID'), widget=CustomTextInput(readonly='readonly', placeholder=(lazy_gettext('related ORCiD ID - automatically managed'))))


class WorkForm(Form):
    pubtype = SelectField(lazy_gettext('Type'), validators=[Optional()])
    DOI = FieldList(StringField(lazy_gettext('DOI'),
                                validators=[Optional(), Regexp('^\s*10\.[0-9]{4,}(?:\.[0-9]+)*\/[a-z0-9\-\._\(\)]+', IGNORECASE, message=lazy_gettext('Invalid value! Schema: 10.<NNNN>/<SOME-ID>'))]),
                    min_entries=1)
    title = StringField(lazy_gettext('Title'), validators=[DataRequired()], widget=CustomTextInput(
        placeholder=lazy_gettext('The title of the work')))
    subtitle = StringField(lazy_gettext('Subtitle'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('The subtitle of the work')))
    language = FieldList(SelectField(lazy_gettext('Language'), validators=[Optional()], choices=forms_vocabularies.LANGUAGES),
                         min_entries=1)

    title_supplement = StringField(lazy_gettext('Title Supplement'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('Additions to the title of the work')))
    other_title = FieldList(FormField(OtherTitleForm), min_entries=1)
    publication_status = SelectField(lazy_gettext('Publication Status'), validators=[DataRequired()],
                                     choices=forms_vocabularies.PUB_STATUS, default='published')
    version = SelectField(lazy_gettext('Version'), choices=[
        ('', lazy_gettext('Select a Version')),
        ('preprint', lazy_gettext('Preprint')),
        ('postprint', lazy_gettext('Postprint')),
        ('publischers_version', lazy_gettext("Publisher's Version")),
    ], default='publischers_version')
    issued = StringField(lazy_gettext('Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                         widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))

    person = FieldList(FormField(PersonForm), min_entries=1)
    corporation = FieldList(FormField(CorporationForm), min_entries=1)

    uri = FieldList(StringField(lazy_gettext('Link to full text'),
                                validators=[URL(message=lazy_gettext('Invalid value! The URI has to start with http:// or https:// or another schema?')), Optional()]), min_entries=1,
                    widget=CustomTextInput(placeholder=lazy_gettext('A URI, URL, or URN')))
    PMID = StringField(lazy_gettext('PubMed ID'), widget=CustomTextInput(placeholder=(lazy_gettext('e.g. 15894097'))))

    #orcid_put_code = StringField(lazy_gettext('ORCID PutCode'), widget=CustomTextInput(readonly='readonly', placeholder=(lazy_gettext('Automatically managed ID of a work in ORCID record.'))))
    orcid_sync = FieldList(FormField(OrcidSyncForm), min_entries=1)

    WOSID = StringField(lazy_gettext('Web of Science ID'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. 000229082300022'))))
    accessed = StringField(lazy_gettext('Last Seen'),
                           validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                           widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))
    additions = StringField(lazy_gettext('Additions'), validators=[Optional()])
    keyword = FieldList(StringField(lazy_gettext('Keyword'), validators=[Optional()]), min_entries=1)
    keyword_temporal = FieldList(StringField(lazy_gettext('Temporal'), validators=[Optional()]), min_entries=1)
    keyword_geographic = FieldList(StringField(lazy_gettext('Geographic'), validators=[Optional()]), min_entries=1)
    swd_subject = FieldList(FormField(IDLForm), min_entries=1)
    ddc_subject = FieldList(FormField(IDLForm), min_entries=1)
    mesh_subject = FieldList(FormField(IDLForm), min_entries=1)
    stw_subject = FieldList(FormField(IDLForm), min_entries=1)
    lcsh_subject = FieldList(FormField(IDLForm), min_entries=1)
    thesoz_subject = FieldList(FormField(IDLForm), min_entries=1)

    abstract = FieldList(FormField(AbstractForm), min_entries=1)
    number_of_pages = StringField(lazy_gettext('Extent'), validators=[Optional()])
    medium = SelectField(lazy_gettext('Medium'), validators=[Optional()], choices=forms_vocabularies.CARRIER)
    note = TextAreaField(lazy_gettext('Notes'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('Please put any information that does not fit other fields here.')))
    license = SelectField(lazy_gettext('License'), validators=[Optional()], choices=forms_vocabularies.LICENSE_MAP)
    license_text = StringField(lazy_gettext('Copyright'),
                               description=lazy_gettext("If you have granted the exclusive use of rights to a commercial service, please enter relevant information."))
    is_part_of = FieldList(FormField(IsPartOfForm), min_entries=1)

    affiliation_context = FieldList(StringField(lazy_gettext('Affiliation Context'), validators=[Optional()],
                                                widget=CustomTextInput(placeholder=lazy_gettext('The organisational unit this publication belongs to'))), min_entries=1)
    group_context = FieldList(StringField(lazy_gettext('Working Group Context'), validators=[Optional()],
                                          widget=CustomTextInput(placeholder=lazy_gettext('The working group this publication belongs to'))), min_entries=1)
    id = StringField(lazy_gettext('ID'), validators=[UUID(), Optional()], widget=CustomTextInput(readonly='readonly'))
    created = StringField(lazy_gettext('Record Creation Date'), widget=CustomTextInput(readonly='readonly'))
    changed = StringField(lazy_gettext('Record Change Date'), widget=CustomTextInput(readonly='readonly'))
    editorial_status = SelectField(lazy_gettext('Editorial Status'), validators=[DataRequired()],
                                   choices=forms_vocabularies.EDITORIAL_STATUS, default='new')
    owner = FieldList(StringField(lazy_gettext('Owner')), min_entries=1)
    catalog = SelectMultipleField(lazy_gettext('Data Catalog'), choices=forms_vocabularies.CATALOGS,
                                  description=lazy_gettext('Choose one or more data catalog by clicking and pressing "strg"'))
    deskman = StringField(lazy_gettext('Deskman'), validators=[Optional()])
    apparent_dup = BooleanField(lazy_gettext('Apparent Duplicate'))

    same_as = FieldList(StringField(lazy_gettext('Same As'), validators=[Optional()]), min_entries=1)


class PrintedWorkForm(WorkForm):
    publisher = StringField(lazy_gettext('Publisher'), validators=[Optional()])
    publisher_place = StringField(lazy_gettext('Place of Publication'), validators=[Optional()])
    edition = StringField(lazy_gettext('Edition'), validators=[Optional()])
    table_of_contents = FieldList(FormField(TableOfContentsForm), min_entries=1)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    hbz_id = FieldList(StringField(lazy_gettext('HBZ-ID'), validators=[Optional()]), min_entries=1)


class SerialForm(PrintedWorkForm):
    subseries = StringField(lazy_gettext('Subseries'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('The title of a subseries')))
    ISSN = FieldList(StringField(lazy_gettext('ISSN'), widget=CustomTextInput(
        placeholder=lazy_gettext('e.g. 1932-6203'))), min_entries=1)
    ZDBID = FieldList(StringField(lazy_gettext('ZDB-ID'),
                                  widget=CustomTextInput(placeholder=lazy_gettext('e.g. 2267670-3'))),
                      min_entries=1)
    frequency = SelectField(lazy_gettext('Frequency'), validators=[Optional()],
                            choices=forms_vocabularies.FREQUENCY)
    external = BooleanField(lazy_gettext('External'))

    person = FieldList(FormField(PersonAsEditorForm), min_entries=1)
    corporation = FieldList(FormField(CorporationAsEditorForm), min_entries=1)

    user_only = ['parent_title', 'parent_subtitle']
    admin_only = ['external']


class SeriesForm(SerialForm):
    number_of_volumes = StringField(lazy_gettext('Number of Volumes'), validators=[Optional()])

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle, self.subseries, self.language,
                       self.title_supplement, self.other_title, self.number_of_volumes, self.publisher,
                       self.publisher_place, self.frequency, self.medium,
                       self.note, self.license, self.license_text
                       ],
             'label': lazy_gettext('Basic')},
            {'group': [self.ISSN, self.ZDBID, self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code], 'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class JournalForm(SerialForm):
    journal_abbreviation = FieldList(StringField(lazy_gettext('Journal Abbreviation'), widget=CustomTextInput(
        placeholder=lazy_gettext('The Abbreviated Title of the Journal'))), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle, self.subseries,
                       self.journal_abbreviation,
                       self.language, self.title_supplement, self.other_title, self.publisher,
                       self.publisher_place, self.frequency, self.medium,
                       self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.ISSN, self.ZDBID, self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class NewspaperForm(JournalForm):
    journal_abbreviation = FieldList(StringField(lazy_gettext('Newspaper Abbreviation'), widget=CustomTextInput(
        placeholder=lazy_gettext('The Abbreviated Title of the Newspaper'))), min_entries=1)


class ArticleForm(WorkForm):
    pass


class ArticleJournalForm(ArticleForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('abstract', lazy_gettext('Abstract')),
        ('festschrift', lazy_gettext('Festschrift')),
        ('interview', lazy_gettext('Interview')),
        ('lexicon_article', lazy_gettext('Article in Lexicon')),
        ('meeting_abstract', lazy_gettext('Meeting Abstract')),
        ('poster', lazy_gettext('Poster')),
        ('poster_abstract', lazy_gettext('Poster Abstract')),
        ('sermon', lazy_gettext('Sermon')),
        ('review', lazy_gettext('Review')),
        ('introduction', lazy_gettext('Foreword')),
    ])
    publication_status = SelectField(lazy_gettext('Publication Status'), validators=[DataRequired()], choices=[
        ('', lazy_gettext('Select a Publication Status')),
        ('submitted', lazy_gettext('Submitted')),
        ('accepted', lazy_gettext('Accepted')),
        ('published', lazy_gettext('Published')),
        ('unpublished', lazy_gettext('Unpublished'))
    ], default='published')
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))
    is_part_of = FieldList(FormField(ArticleRelationForm), min_entries=1)
    DFG = BooleanField(lazy_gettext('DFG Funded'),
                       description=Markup(lazy_gettext('APCs funded by the DFG and the institutional OA Fund.')))
    open_access = FormField(OpenAccessForm)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    event = FieldList(FormField(EventForm), min_entries=1)

    admin_only = ['gnd', 'viaf', 'isni']

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle,
                       self.language,
                       self.title_supplement, self.other_title, self.issued, self.number_of_pages, self.medium,
                       self.accessed, self.additions, self.note, self.license, self.license_text, self.peer_reviewed],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.event],
             'label': lazy_gettext('Event')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Journal')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.open_access, self.DFG],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman,
                       self.same_as, self.orcid_sync],
             'label': lazy_gettext('Administrative')},
        ]


class ArticleRelationUserForm(Form):
    is_part_of = StringField(lazy_gettext('Journal'))
    volume = StringField(lazy_gettext('Volume / Year'))
    issue = StringField(lazy_gettext('Issue'))
    page_first = StringField(lazy_gettext('First Page'))
    page_last = StringField(lazy_gettext('Last Page'))


class ArticleJournalUserForm(ArticleJournalForm):
    id = HiddenField(validators=[UUID(), Optional()], default=str(uuid.uuid4))
    created = HiddenField(default=timestamp())
    changed = HiddenField(default=timestamp())
    person = FieldList(FormField(PersonUserForm), min_entries=1)
    corporation = FieldList(FormField(CorporationUserForm), min_entries=1)
    is_part_of = FieldList(FormField(ArticleRelationUserForm), min_entries=1)

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle,
                       self.language, self.issued, self.uri, self.DOI, self.peer_reviewed,
                       self.note, self.id, self.created, self.changed],
             'label': lazy_gettext('Publication Details')},
            {'group': [self.person, self.corporation],
             'label': lazy_gettext('Contributors')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Journal')},
            {'group': [self.keyword],
             'label': lazy_gettext('Keywords')},
            {'group': [self.abstract],
             'label': lazy_gettext('Abstract')},
            {'group': [self.affiliation_context, self.group_context],
             'label': lazy_gettext('Work belongs to')},
        ]


class ArticleNewspaperForm(ArticleForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('review', lazy_gettext('Review')),
        ('interview', lazy_gettext('Interview')),
    ])
    is_part_of = FieldList(FormField(NewspaperRelationForm), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle,
                       self.language,
                       self.title_supplement, self.other_title, self.issued, self.number_of_pages, self.medium,
                       self.accessed, self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Newspaper')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject
                       ],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class SpecialIssueForm(JournalForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('festschrift', lazy_gettext('Festschrift')),
    ])
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)
    ISMN = FieldList(StringField(lazy_gettext('ISMN'), validators=[Optional()]), min_entries=1)
    is_part_of = FieldList(FormField(SpecialIssueRelationForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle,
                       self.language,
                       self.title_supplement, self.other_title, self.issued, self.publisher,
                       self.publisher_place, self.frequency, self.number_of_pages, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.ISSN, self.ISBN, self.ISMN, self.ZDBID, self.uri, self.DOI, self.PMID, self.WOSID,
                       self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ContainerForm(PrintedWorkForm):
    number_of_volumes = StringField(lazy_gettext('Number of Volumes'), validators=[Optional()])
    open_access = FormField(OpenAccessForm)
    external = BooleanField(lazy_gettext('External'))
    is_part_of = FieldList(FormField(ContainerRelationForm), min_entries=1)
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)
    ISMN = FieldList(StringField(lazy_gettext('ISMN'), validators=[Optional()]), min_entries=1)

    admin_only = ['external']


class CollectionForm(ContainerForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('festschrift', lazy_gettext('Festschrift')),
    ])
    publication_status = SelectField(lazy_gettext('Publication Status'), validators=[DataRequired()], choices=[
        ('', lazy_gettext('Select a Publication Status')),
        ('forthcoming', lazy_gettext('Forthcoming')),
        ('published', lazy_gettext('Published')),
        ('unpublished', lazy_gettext('Unpublished'))
    ], default='published')
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))
    author_editor = FieldList(FormField(PersonUserForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle,
                       self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.number_of_volumes,
                       self.publisher, self.publisher_place, self.number_of_pages, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text, self.peer_reviewed],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.hbz_id, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class CollectionUserForm(CollectionForm):
    id = HiddenField(validators=[UUID(), Optional()], default=str(uuid.uuid4))
    created = HiddenField(default=timestamp())
    changed = HiddenField(default=timestamp())
    person = FieldList(FormField(PersonUserForm), min_entries=1)
    corporation = FieldList(FormField(CorporationUserForm), min_entries=1)

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle, self.language,
                       self.issued, self.edition, self.number_of_volumes,
                       self.publisher, self.publisher_place,
                       self.uri, self.DOI, self.ISBN, self.peer_reviewed, self.note,
                       self.id, self.created, self.changed],
             'label': lazy_gettext('Publication Details')},
            {'group': [self.person, self.corporation],
             'label': lazy_gettext('Contributors')},
            {'group': [self.keyword],
             'label': lazy_gettext('Keywords')},
            {'group': [self.abstract],
             'label':lazy_gettext('Abstract')},
            {'group': [self.affiliation_context, self.group_context],
             'label': lazy_gettext('Work belongs to')},
        ]


class ConferenceForm(CollectionForm):
    event = FieldList(FormField(EventForm), min_entries=1)
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.number_of_volumes,
                       self.publisher, self.publisher_place, self.number_of_pages, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text, self.peer_reviewed],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.hbz_id, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.event],
             'label': lazy_gettext('Event')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup,
                       self.editorial_status, self.created, self.changed, self.catalog, self.owner, self.deskman,
                       self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class EditionForm(CollectionForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('festschrift', lazy_gettext('Festschrift')),
        ('notated_music', lazy_gettext('Notated Music')),
    ])

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.number_of_volumes,
                       self.publisher, self.publisher_place, self.number_of_pages, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.hbz_id, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class LegalCommentaryForm(CollectionForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('festschrift', lazy_gettext('Festschrift')),
        ('lexicon_article', lazy_gettext('Article in Lexicon')),
    ])
    standard_abbreviation = FieldList(StringField(lazy_gettext('Standard Abbreviation'),
                                                  validators=[Optional()], widget=CustomTextInput(
            placeholder=lazy_gettext('The standard abbreviation of the legal commentary'))), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.standard_abbreviation, self.issued, self.edition,
                       self.number_of_volumes, self.publisher, self.publisher_place, self.number_of_pages, self.medium,
                       self.accessed, self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.hbz_id, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ChapterForm(WorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('abstract', lazy_gettext('Abstract')),
        ('afterword', lazy_gettext('Afterword')),
        ('festschrift', lazy_gettext('Festschrift')),
        ('sermon', lazy_gettext('Sermon')),
        ('interview', lazy_gettext('Interview')),
        ('introduction', lazy_gettext('Foreword')),
        ('lexicon_article', lazy_gettext('Article in Lexicon')),
        ('meeting_abstract', lazy_gettext('Meeting Abstract')),
        ('poster', lazy_gettext('Poster')),
        ('poster_abstract', lazy_gettext('Poster Abstract')),
        ('review', lazy_gettext('Review')),
    ])
    parent_title = StringField(lazy_gettext('Parent Title'), validators=[Optional()],
                               widget=CustomTextInput(placeholder=lazy_gettext('The Title of the Parent Reference')))
    parent_subtitle = StringField(lazy_gettext('Parent Subtitle'), validators=[Optional()], widget=CustomTextInput(
        placeholder=lazy_gettext('The Subtitle of the Parent Reference')))
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))
    open_access = FormField(OpenAccessForm)
    DFG = BooleanField(lazy_gettext('DFG Funded'), description=Markup(lazy_gettext(
        'APCs funded by the DFG and the RUB OA Fund (<a href="https://github.com/OpenAPC/openapc-de/tree/master/data/rub">OpenAPC</a>)')))
    is_part_of = FieldList(FormField(ChapterRelationForm), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    event = FieldList(FormField(EventForm), min_entries=1)

    user_only = ['parent_title', 'parent_subtitle', 'ISBN']

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.number_of_pages, self.medium,
                       self.accessed, self.additions, self.note, self.license, self.license_text, self.peer_reviewed],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.event],
             'label': lazy_gettext('Event')},
            {'group': [self.is_part_of, self.parent_title, self.parent_subtitle],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.open_access, self.DFG],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup,
                       self.editorial_status, self.created, self.changed, self.catalog, self.owner, self.deskman,
                       self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ChapterUserForm(ChapterForm):
    id = HiddenField(validators=[UUID(), Optional()], default=str(uuid.uuid4))
    created = HiddenField(default=timestamp())
    changed = HiddenField(default=timestamp())
    person = FieldList(FormField(PersonUserForm), min_entries=1)
    corporation = FieldList(FormField(CorporationUserForm), min_entries=1)

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle, self.language,
                       self.issued, self.uri, self.DOI, self.peer_reviewed, self.note,
                       self.id, self.created, self.changed],
             'label': lazy_gettext('Publication Details')},
            {'group': [self.person, self.corporation],
             'label': lazy_gettext('Contributors')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is published in')},
            {'group': [self.keyword],
             'label': lazy_gettext('Keywords')},
            {'group': [self.abstract],
             'label':lazy_gettext('Abstract')},
            {'group': [self.affiliation_context, self.group_context],
             'label': lazy_gettext('Work belongs to')},
        ]


class ChapterInLegalCommentaryForm(ChapterForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('lexicon_article', lazy_gettext('Article in Lexicon')),
    ])
    supplement = StringField('Supplement', validators=[Optional()])
    date_updated = StringField(lazy_gettext('Date updated'),
                               validators=[Optional(), Regexp('[12]\d{3}|[12]\d{3}-[01]\d|[12]\d{3}-[01]\d-[0123]\d')],
                               widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')),
                               description=lazy_gettext("The last update of the legal text. If you don't know the month and/or day please use 01"))

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.supplement, self.issued, self.date_updated,
                       self.number_of_pages, self.medium, self.accessed, self.additions, self.note, self.license,
                       self.license_text, self.peer_reviewed],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of, self.parent_title, self.parent_subtitle],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.open_access, self.DFG],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup,
                       self.editorial_status, self.created, self.changed, self.catalog, self.owner, self.deskman,
                       self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class AudioVideoDocumentForm(PrintedWorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('image_database', lazy_gettext('Image Database')),
        ('dramatic_work', lazy_gettext('Dramatic Work')),
        ('interview', lazy_gettext('Interview')),
        ('sermon', lazy_gettext('Sermon')),
        ('audio_book', lazy_gettext('Audio Book')),
    ])
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)
    ISMN = FieldList(StringField(lazy_gettext('ISMN'), validators=[Optional()]), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.publisher,
                       self.publisher_place, self.number_of_pages, self.medium, self.accessed, self.additions,
                       self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class InternetDocumentForm(WorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('abstract', lazy_gettext('Abstract')),
        ('sermon', lazy_gettext('Sermon')),
        ('interview', lazy_gettext('Interview')),
        ('lexicon_article', lazy_gettext('Article in Lexicon')),
        ('meeting_abstract', lazy_gettext('Meeting Abstract')),
        ('poster', lazy_gettext('Poster')),
        ('poster_abstract', lazy_gettext('Poster Abstract')),
        ('review', lazy_gettext('Review')),
    ])
    uri = FieldList(StringField(lazy_gettext('URL'), validators=[URL(), Optional()]), min_entries=1)
    last_update = StringField(lazy_gettext('Last update'),
                              validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')],
                              widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD'),
                                                     description=lazy_gettext("If you don't know the month and/or day please use 01")))
    place = StringField(lazy_gettext('Place'), validators=[Optional()])
    number = FieldList(StringField('Number', validators=[Optional()]), min_entries=1)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    table_of_contents = FieldList(FormField(TableOfContentsForm), min_entries=1)
    event = FieldList(FormField(EventForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.place, self.number_of_pages,
                       self.number, self.medium, self.accessed, self.last_update, self.additions, self.note,
                       self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.event],
             'label': lazy_gettext('Event')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class LectureForm(WorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('abstract', lazy_gettext('Abstract')),
        ('meeting_abstract', lazy_gettext('Meeting Abstract')),
    ])
    lecture_title = StringField(lazy_gettext('Lecture Series'),
                                validators=[Optional()],
                                widget=CustomTextInput(placeholder=lazy_gettext('The Title of the Lecture Series')))
    event = FieldList(FormField(EventForm), min_entries=1)
    open_access = FormField(OpenAccessForm)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    table_of_contents = FieldList(FormField(TableOfContentsForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.lecture_title, self.issued, self.number_of_pages,
                       self.medium, self.accessed, self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.event],
             'label': lazy_gettext('Event')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label':lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class MonographForm(PrintedWorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('dissertation', lazy_gettext('Dissertation')),
        ('habilitation', lazy_gettext('Habilitation')),
        ('festschrift', lazy_gettext('Festschrift')),
        ('notated_music', lazy_gettext('Notated Music')),
    ])
    publication_status = SelectField(lazy_gettext('Publication Status'), validators=[DataRequired()], choices=[
        ('', lazy_gettext('Select a Publication Status')),
        ('forthcoming', lazy_gettext('Forthcoming')),
        ('published', lazy_gettext('Published')),
        ('unpublished', lazy_gettext('Unpublished'))
    ], default='published')
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)
    ISMN = FieldList(StringField(lazy_gettext('ISMN'), validators=[Optional()]), min_entries=1)
    hbz_id = FieldList(StringField(lazy_gettext('HBZ-ID'), validators=[Optional()]), min_entries=1)
    number_of_volumes = StringField('Number of Volumes', validators=[Optional()])
    open_access = FormField(OpenAccessForm)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    is_part_of = FieldList(FormField(MonographRelationForm), min_entries=1)
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))
    author_editor = FieldList(FormField(PersonUserForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.number_of_volumes,
                       self.publisher, self.publisher_place, self.number_of_pages, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text, self.peer_reviewed],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.hbz_id],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman,
                       self.same_as, self.orcid_sync],
             'label': lazy_gettext('Administrative')},
        ]


class MonographUserForm(MonographForm):
    id = HiddenField(validators=[UUID(), Optional()], default=str(uuid.uuid4))
    created = HiddenField(default=timestamp())
    changed = HiddenField(default=timestamp())
    person = FieldList(FormField(PersonUserForm), min_entries=1)
    corporation = FieldList(FormField(CorporationUserForm), min_entries=1)

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle, self.language,
                       self.issued, self.edition,
                       self.publisher, self.publisher_place,
                       self.uri, self.DOI, self.ISBN, self.peer_reviewed, self.note,
                       self.id, self.created, self.changed],
             'label': lazy_gettext('Publication Details')},
            {'group': [self.person, self.corporation],
             'label': lazy_gettext('Contributors')},
            {'group': [self.keyword],
             'label': lazy_gettext('Keywords')},
            {'group': [self.abstract],
             'label':lazy_gettext('Abstract')},
            {'group': [self.affiliation_context, self.group_context],
             'label': lazy_gettext('Work belongs to')},
        ]


class MultivolumeWorkForm(PrintedWorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('Monograph', lazy_gettext('Monograph')),
        ('Collection', lazy_gettext('Collection')),
        ('Conference', lazy_gettext('Conference')),
        ('SpecialIssue', lazy_gettext('Special Issue')),
    ])
    publication_status = SelectField(lazy_gettext('Publication Status'), validators=[DataRequired()], choices=[
        ('', lazy_gettext('Select a Publication Status')),
        ('forthcoming', lazy_gettext('Forthcoming')),
        ('published', lazy_gettext('Published')),
        ('unpublished', lazy_gettext('Unpublished'))
    ], default='published')
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)
    ISMN = FieldList(StringField(lazy_gettext('ISMN'), validators=[Optional()]), min_entries=1)
    hbz_id = FieldList(StringField(lazy_gettext('HBZ-ID'), validators=[Optional()]), min_entries=1)
    number_of_volumes = StringField('Number of Volumes', validators=[Optional()])
    open_access = FormField(OpenAccessForm)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    is_part_of = FieldList(FormField(MonographRelationForm), min_entries=1)
    issued = StringField(lazy_gettext('Date'), validators=[Optional(), Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                         widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')))

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.number_of_volumes,
                       self.publisher, self.publisher_place, self.number_of_pages, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.ISMN, self.hbz_id, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Volume')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman,
                       self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ReportForm(WorkForm):
    parent_title = StringField(lazy_gettext('Parent Title'), validators=[Optional()],
                               widget=CustomTextInput(placeholder=lazy_gettext('The Title of the Parent Reference')))
    parent_subtitle = StringField(lazy_gettext('Parent Subtitle'), validators=[Optional()],
                                  widget=CustomTextInput(placeholder=lazy_gettext('The Subtitle of the Parent Reference')))
    place = StringField(lazy_gettext('Place'), validators=[Optional()])
    edition = StringField(lazy_gettext('Edition'), validators=[Optional()])
    number = FieldList(StringField(lazy_gettext('Number'), validators=[Optional()]), min_entries=1)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    is_part_of = FieldList(FormField(OtherRelationForm), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    table_of_contents = FieldList(FormField(TableOfContentsForm), min_entries=1)
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)
    author_editor = FieldList(FormField(PersonUserForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.place,
                       self.number_of_pages, self.number, self.medium, self.accessed, self.additions, self.note,
                       self.license, self.license_text, self.peer_reviewed
                       ],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.ISBN, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of, self.parent_title, self.parent_subtitle],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ReportUserForm(ReportForm):
    id = HiddenField()
    created = HiddenField()
    changed = HiddenField()
    person = FieldList(FormField(PersonUserForm), min_entries=1)
    corporation = FieldList(FormField(CorporationUserForm), min_entries=1)

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.subtitle, self.language,
                       self.issued, self.edition, self.place, self.number,
                       self.uri, self.DOI, self.ISBN, self.peer_reviewed, self.note,
                       self.id, self.created, self.changed],
             'label': lazy_gettext('Publication Details')},
            {'group': [self.person, self.corporation],
             'label': lazy_gettext('Contributors')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is published in')},
            {'group': [self.keyword],
             'label': lazy_gettext('Keywords')},
            {'group': [self.abstract],
             'label':lazy_gettext('Abstract')},
            {'group': [self.affiliation_context, self.group_context],
             'label': lazy_gettext('Work belongs to')},
        ]


class RelatedIdentifiersForm(Form):
    related_identifier = StringField(lazy_gettext('Related Identifier'), validators=[Optional()])
    relation_type = SelectField(lazy_gettext('Resource Type'), validators=[Optional()],
                                choices=forms_vocabularies.RELATION_TYPES,
                                description=lazy_gettext('Specify identifiers of related publications and datasets.'))


class ResearchDataForm(WorkForm):
    place = StringField(lazy_gettext('Publisher Place'), validators=[Optional()])
    version = StringField(lazy_gettext('Version'), validators=[Optional()])
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    is_part_of = FieldList(FormField(IsPartOfForm), min_entries=1)
    related_identifiers = FieldList(FormField(RelatedIdentifiersForm), min_entries=1)
    repository = StringField(lazy_gettext('Repository / Publisher'), validators=[Optional()])
    resource_type = SelectField(lazy_gettext('Resource Type'), validators=[Optional()],
                                choices=forms_vocabularies.RESOURCE_TYPES)
    size = StringField(lazy_gettext('Size'), validators=[Optional()])
    format = StringField(lazy_gettext('Format'), validators=[Optional()])
    peer_reviewed = BooleanField(lazy_gettext('Peer Reviewed'))

    def groups(self):
        yield [
            {'group': [self.pubtype, self.resource_type, self.publication_status, self.title, self.subtitle,
                       self.title_supplement,
                       self.issued, self.version, self.repository, self.place,
                       self.medium, self.size, self.format, self.accessed, self.note, self.peer_reviewed
                       ],
             'label': lazy_gettext('Basic')},
            {'group': [self.license, self.license_text],
             'label': lazy_gettext('License')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.related_identifiers],
             'label': lazy_gettext('Relations')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ResearchDataUserForm(ResearchDataForm):
    id = HiddenField(validators=[UUID(), Optional()], default=str(uuid.uuid4))
    created = HiddenField(default=timestamp())
    changed = HiddenField(default=timestamp())
    person = FieldList(FormField(PersonUserForm), min_entries=1)
    corporation = FieldList(FormField(CorporationUserForm), min_entries=1)

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.resource_type, self.publication_status, self.title, self.subtitle,
                       self.language,
                       self.issued, self.version, self.repository, self.medium, self.size, self.format,
                       self.uri, self.DOI, self.peer_reviewed, self.note,
                       self.id, self.created, self.changed],
             'label': lazy_gettext('Publication Details')},
            {'group': [self.person, self.corporation],
             'label': lazy_gettext('Contributors')},
            {'group': [self.license, self.license_text],
             'label': lazy_gettext('License')},
            {'group': [self.related_identifiers],
             'label': lazy_gettext('Relations')},
            {'group': [self.keyword],
             'label': lazy_gettext('Keywords')},
            {'group': [self.abstract],
             'label':lazy_gettext('Abstract')},
            {'group': [self.affiliation_context, self.group_context],
             'label': lazy_gettext('Work belongs to')},
        ]


class OtherForm(WorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('article_lexicon', lazy_gettext('Article in Lexicon')),
        ('festschrift', lazy_gettext('Festschrift')),
        ('sermon', lazy_gettext('Sermon')),
        ('lecture_notes', lazy_gettext('Lecture Notes')),
        ('poster', lazy_gettext('Poster')),
        ('poster_abstract', lazy_gettext('Poster Abstract')),
        ('expert_opinion', lazy_gettext('Expert Opinion')),
    ])
    place = StringField(lazy_gettext('Place'), validators=[Optional()])
    edition = StringField('Edition', validators=[Optional()])
    number = FieldList(StringField('Number', validators=[Optional()]), min_entries=1)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    is_part_of = FieldList(FormField(OtherRelationForm), min_entries=1)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    event = FieldList(FormField(EventForm), min_entries=1)
    table_of_contents = FieldList(FormField(TableOfContentsForm), min_entries=1)
    ISBN = FieldList(StringField(lazy_gettext('ISBN'), validators=[Optional(), Isbn]), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.place,
                       self.number_of_pages, self.number, self.medium, self.accessed, self.additions, self.note,
                       self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.ISBN, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.event],
             'label': lazy_gettext('Event')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class PatentFormOld(WorkForm):
    patent_number = StringField(lazy_gettext('Patent Number'), widget=CustomTextInput(
        placeholder=(lazy_gettext('The publication number for a patent, e.g. DE102004031250 A1'))))
    claims = StringField(lazy_gettext('Claims'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. Eur. Pat. Appl.'))))
    applicant = FieldList(StringField(lazy_gettext('Applicant'), widget=CustomTextInput(
        placeholder=(lazy_gettext('The name of the person applying for the patent')))), min_entries=1)
    date_application = StringField(lazy_gettext('Application Date'), widget=CustomTextInput(
        placeholder=(lazy_gettext('YYYY-MM-DD'))), validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')])
    place_of_application = StringField(lazy_gettext('Application Country'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. Germany'))))
    application_number = StringField(lazy_gettext('Application Number'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. PCT/US2007/066814'))))
    place = StringField(lazy_gettext('Issue Country'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. Germany'))))
    bibliographic_ipc = StringField(lazy_gettext('Bibliographic IPC'), widget=CustomTextInput(
        placeholder=(lazy_gettext('Number according to the International Patent Classification, e. g. A63G 29/00'))))
    priority_date = FieldList(StringField(lazy_gettext('Priority Date'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. 60/744,997, 17.04.2006, US')))), min_entries=1)
    open_access = FormField(OpenAccessForm)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.number_of_pages, self.medium,
                       self.accessed, self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.claims, self.applicant, self.date_application, self.place_of_application,
                       self.application_number, self.place, self.bibliographic_ipc, self.priority_date],
             'label': lazy_gettext('Specific')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
]


class PatentForm(WorkForm):
    publication_number = StringField(lazy_gettext('Publication Number'), widget=CustomTextInput(
        placeholder=(lazy_gettext('The publication number for a patent, e.g. DE102004031250A1'))))
    application_number = StringField(lazy_gettext('Application Number'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. 2012071376'))), validators=[DataRequired()])
    application_country = StringField(lazy_gettext('Application Country'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. DE'))), validators=[DataRequired(), Regexp('[A-Z]{2}')])
    application_date = StringField(lazy_gettext('Application Date'), widget=CustomTextInput(
        placeholder=(lazy_gettext('YYYY-MM-DD'))), validators=[DataRequired(), Regexp('[12]\d{3}-[01]\d-[0123]\d')])
    priority_number = StringField(lazy_gettext('Priority Number'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. 2012071376'))))
    priority_country = StringField(lazy_gettext('Priority Country'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. DE'))), validators=[Optional(), Regexp('[A-Z]{2}')])
    priority_date = StringField(lazy_gettext('Priority Date'), widget=CustomTextInput(
        placeholder=(lazy_gettext('e.g. 60/744,997, 17.04.2006, US'))))

    ipc_keyword = FieldList(FormField(IDLForm), min_entries=1)

    publication_status = SelectField(lazy_gettext('Publication Status'), validators=[DataRequired()],
                                     choices=forms_vocabularies.PATENT_PUB_STATUS,
                                     default='granted')
    person = FieldList(FormField(PatentPersonForm), min_entries=1)
    corporation = FieldList(FormField(PatentCorporationForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.title, self.language,
                       self.other_title, self.number_of_pages, self.accessed, self.note],
             'label': lazy_gettext('Basic')},
            {'group': [self.publication_number,
                       self.application_number, self.application_country, self.application_date,
                       self.priority_number, self.priority_country, self.priority_date],
             'label': lazy_gettext('Specific')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.ipc_keyword, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.uri],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class PressReleaseForm(WorkForm):
    place = StringField(lazy_gettext('Place'), validators=[Optional()])
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.place, self.number_of_pages,
                       self.medium, self.accessed, self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class RadioTVProgramForm(WorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('interview', lazy_gettext('Interview')),
    ])
    issued = StringField(lazy_gettext('Broadcast Date'),
                         validators=[DataRequired(), Regexp('[12]\d{3}-[01]\d-[0123]\d')],
                         widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')),
                         description=lazy_gettext("If you don't know the month and/or day please use 01"))
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued,self.number_of_pages, self.medium,
                       self.accessed, self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract],
             'label':lazy_gettext('Content')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class SoftwareForm(PrintedWorkForm):
    title = StringField(lazy_gettext('Program Name'),
                        validators=[DataRequired()], widget=CustomTextInput(
            placeholder=lazy_gettext('The Name of the Software')))
    edition = StringField('Version', validators=[Optional()])
    operating_system = FieldList(StringField('Operating System', validators=[Optional()]), min_entries=1)
    open_access = FormField(OpenAccessForm)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.publisher,
                       self.publisher_place, self.number_of_pages, self.operating_system, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]

    def simple_groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.publisher,
                       self.publisher_place, self.number_of_pages, self.operating_system, self.medium, self.accessed,
                       self.additions, self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class StandardForm(PrintedWorkForm):
    number = FieldList(StringField('Number', validators=[Optional()]), min_entries=1)
    number_revision = StringField('Revision Number', validators=[Optional()])
    type_of_standard = StringField('Type of Standard', validators=[Optional()])
    ICS_notation = FieldList(StringField('ICS Notation', validators=[Optional()]), min_entries=1)
    open_access = FormField(OpenAccessForm)
    other_version = FieldList(FormField(OtherVersionForm), min_entries=1)
    ISBN = FieldList(StringField(lazy_gettext('ISBN of the Collection'), validators=[Optional(), Isbn]), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.publication_status, self.version, self.title, self.subtitle, self.language,
                       self.title_supplement, self.other_title, self.issued, self.edition, self.publisher,
                       self.publisher_place, self.number_of_pages, self.medium, self.accessed, self.additions,
                       self.note, self.license, self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.number_revision, self.type_of_standard, self.ICS_notation],
             'label': lazy_gettext('Specific')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.ISBN, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.other_version],
             'label': lazy_gettext('Other Version')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label': lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


class ThesisForm(WorkForm):
    subtype = SelectField(lazy_gettext('Subtype'), validators=[Optional()], choices=[
        ('', lazy_gettext('Select a Subtype')),
        ('bachelor_thesis', lazy_gettext('Bachelor Thesis')),
        ('diploma_thesis', lazy_gettext('Diploma Thesis')),
        ('dissertation', lazy_gettext('Dissertation')),        
        ('habilitation', lazy_gettext('Habilitation')),
        ('magisterarbeit', lazy_gettext('Magisterarbeit')),
        ('masters_thesis', lazy_gettext('Master`s Thesis')),
        ('first_state_examination', lazy_gettext('1st State Examination')),
        ('second_state_examination', lazy_gettext('2nd State Examination')),
    ])
    hbz_id = FieldList(StringField(lazy_gettext('HBZ-ID'), validators=[Optional()]), min_entries=1)
    issued = StringField(lazy_gettext('Date issued'), validators=[Regexp('[12]\d{3}(?:-[01]\d)?(?:-[0123]\d)?')],
                         widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')),
                         description=lazy_gettext("If you don't know the month and/or day please use 01"))
    day_of_oral_exam = StringField(lazy_gettext('Day of the Oral Exam'),
                                   validators=[Optional(), Regexp('[12]\d{3}-[01]\d-[0123]\d')],
                                   widget=CustomTextInput(placeholder=lazy_gettext('YYYY-MM-DD')),
                                   description=lazy_gettext("If you don't know the month and/or day please use 01"))
    place = StringField(lazy_gettext('Location of Academic Institution'), validators=[Optional()],
                        widget=CustomTextInput(placeholder=lazy_gettext('Where the thesis was submitted')))
    open_access = FormField(OpenAccessForm)
    has_part = FieldList(FormField(HasPartForm), min_entries=1)
    table_of_contents = FieldList(FormField(TableOfContentsForm), min_entries=1)

    def groups(self):
        yield [
            {'group': [self.pubtype, self.subtype, self.publication_status, self.version, self.title, self.subtitle,
                       self.language,
                       self.title_supplement, self.other_title, self.issued, self.day_of_oral_exam, self.place,
                       self.number_of_pages, self.medium, self.accessed, self.additions, self.note, self.license,
                       self.license_text],
             'label': lazy_gettext('Basic')},
            {'group': [self.uri, self.DOI, self.PMID, self.WOSID, self.hbz_id, self.orcid_put_code],
             'label': lazy_gettext('IDs')},
            {'group': [self.person],
             'label': lazy_gettext('Person')},
            {'group': [self.corporation],
             'label': lazy_gettext('Corporation')},
            {'group': [self.is_part_of],
             'label': lazy_gettext('Is Part of')},
            {'group': [self.has_part],
             'label': lazy_gettext('Has Part')},
            {'group': [self.keyword, self.keyword_temporal, self.keyword_geographic, self.swd_subject, self.ddc_subject,
                       self.mesh_subject, self.stw_subject, self.lcsh_subject, self.thesoz_subject],
             'label': lazy_gettext('Keyword')},
            {'group': [self.abstract, self.table_of_contents],
             'label':lazy_gettext('Content')},
            {'group': [self.open_access],
             'label': lazy_gettext('Open Access')},
            {'group': [self.id, self.affiliation_context, self.group_context, self.apparent_dup, self.editorial_status,
                       self.created, self.changed, self.catalog, self.owner, self.deskman, self.same_as],
             'label': lazy_gettext('Administrative')},
        ]


########################################################################


class UserForm(Form):
    loginid = StringField(Markup(lazy_gettext('<i class="fa fa-user"></i> LoginID')), validators=[DataRequired()])
    password = PasswordField(lazy_gettext('Password'))
    name = StringField(lazy_gettext('Name'), description=lazy_gettext('First Name Last Name'))
    email = StringField(lazy_gettext('Email'), validators=[Email()])
    role = SelectField(lazy_gettext('Role'), choices=[
        ('', lazy_gettext('Select a Role')),
        ('user', lazy_gettext('User')),
        ('admin', lazy_gettext('Admin'))], default='user')
    recaptcha = RecaptchaField()
    submit = SubmitField(Markup(lazy_gettext('<i class="fa fa-user-plus"></i> Register')))


class IDListForm(Form):
    ids = TextAreaField(lazy_gettext('List of IDs'),
                        lazy_gettext('A List of one or more Identifiers such as ISBNs, DOIs, or PubMED IDs.'))
    submit = SubmitField(lazy_gettext('Search'))


class FileUploadForm(Form):
    type = SelectField(lazy_gettext('Entity Type'), choices=[
        ('', lazy_gettext('Select a Type')),
        ('publication', lazy_gettext('Publication')),
        ('person', lazy_gettext('Person')),
        ('organisation', lazy_gettext('Organisation')),
        ('group', lazy_gettext('Working Group'))
    ])
    file = FileField(lazy_gettext('Data'))
    submit = SubmitField()


class SimpleSearchForm(Form):
    query = StringField(lazy_gettext('Publication Search'))
    submit = SubmitField(lazy_gettext('Search'))
