# -*- coding: utf-8 -*-

import os
import flask
import requests
import io
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
from cal_analyze import get_data,plot_cal_bars, get_calendar_list
from markupsafe import Markup
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "client_secret_268205187149-tke3jbrhcgk8abdminqpf27p1nu06ssc.apps.googleusercontent.com.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/drive.metadata.readonly']
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'

app = flask.Flask(__name__)
# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See http://flask.pocoo.org/docs/0.12/quickstart/#sessions.
app.secret_key = 'REPLACE ME - this value is here as a placeholder.'


@app.route('/')
def index():
  if 'credentials' not in flask.session:
    return ('<a href="/test">Sign in to view your calendar data!</a><br><a href="/clear">Sign out')
  else:
    return ('<a href="/test">Signed in! Click here to view your calendar data!</a><br><a href="/clear">Sign out')


@app.route('/test')
def test_api_request():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')
  # Load credentials from the session.
  credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])
  service = googleapiclient.discovery.build(
      API_SERVICE_NAME, API_VERSION, credentials=credentials)  
  # service = get_gcal_service()
  cal_data = get_calendar_list(service)

  flask.g.cal_list = list(cal_data[0].keys())
  return flask.render_template('list_calendars.html',cal_list = flask.g.cal_list)
  # flask.g.data = get_data(service)
  # return ('Data Loaded! <a href="/bar_plot">Click here to view!</a></td>')
@app.route('/handle_data', methods=['POST'])
def handle_data():
  cals_to_analyze=flask.request.values.getlist('acs')
  flask.g.cals_to_analyze = cals_to_analyze
  service = get_gcal_service()
  data = get_data(service, flask.g.cals_to_analyze)
  plot = plot_cal_bars(data)
  return flask.render_template('demo_template.html',d3_code=plot)
  # return flask.redirect(flask.url_for('bar_plot'))


# @app.route('/bar_plot')
# def bar_plot():
#   data = getattr(flask.g, 'data', None)

  
#   #output.close()
#   r

 # return 'Code executed... I guess it worked!'
def get_gcal_service():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')
  # Load credentials from the session.
  credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])
  service = googleapiclient.discovery.build(
      API_SERVICE_NAME, API_VERSION, credentials=credentials)
  return service

@app.route('/authorize')
def authorize():
  # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  authorization_url, state = flow.authorization_url(
      # Enable offline access so that you can refresh an access token without
      # re-prompting the user for permission. Recommended for web server apps.
      access_type='offline',
      # Enable incremental authorization. Recommended as a best practice.
      include_granted_scopes='true')

  # Store the state so the callback can verify the auth server response.
  flask.session['state'] = state

  return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
  # Specify the state when creating the flow in the callback so that it can
  # verified in the authorization server response.
  state = flask.session['state']

  flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
  flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

  # Use the authorization server's response to fetch the OAuth 2.0 tokens.
  authorization_response = flask.request.url
  flow.fetch_token(authorization_response=authorization_response)

  # Store credentials in the session.
  # ACTION ITEM: In a production app, you likely want to save these
  #              credentials in a persistent database instead.
  credentials = flow.credentials
  flask.session['credentials'] = credentials_to_dict(credentials)

  return flask.redirect(flask.url_for('test_api_request'))


@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])

  revoke = requests.post('https://accounts.google.com/o/oauth2/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.' + print_index_table())
  else:
    return('An error occurred.' + print_index_table())


@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return flask.redirect('/')

def get_gcal_service():
  if 'credentials' not in flask.session:
    return flask.redirect('authorize')
  # Load credentials from the session.
  credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])
  service = googleapiclient.discovery.build(
      API_SERVICE_NAME, API_VERSION, credentials=credentials)
  return service



def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}
  
if __name__ == '__main__':
  # When running locally, disable OAuthlib's HTTPs verification.
  # ACTION ITEM for developers:
  #     When running in production *do not* leave this option enabled.
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

  # Specify a hostname and port that are set as a valid redirect URI
  # for your API project in the Google API Console.
  app.run('127.0.0.1', 8080, debug=True,ssl_context='adhoc')