# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /notify endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import json
import logging
import webapp2
import requests
import urllib
import client
from apiclient.http import MediaIoBaseUpload
from oauth2client.appengine import StorageByKeyName

from microsofttranslator import Translator, TranslateApiException
from model import Credentials
import util
import main_handler

client_id = 'miaomiaogames'
client_secret = 'lSBAhsgrsQI7rnAb1VURVqrtQrYU53giv/4HdIIlf7A='

args = {
          'client_id': client_id,#your client id here
          'client_secret': client_secret,#your azure secret here
          'scope': 'http://api.microsofttranslator.com',
          'grant_type': 'client_credentials'
      }

class NotifyHandler(webapp2.RequestHandler):
  """Request Handler for notification pings."""

  def post(self):
    """Handles notification pings."""
    logging.info('Got a notification with payload %s', self.request.body)
    data = json.loads(self.request.body)
    userid = data['userToken']
    # TODO: Check that the userToken is a valid userToken.
    self.mirror_service = util.create_service(
        'mirror', 'v1',
        StorageByKeyName(Credentials, userid, 'credentials').get())
    if data.get('collection') == 'locations':
      self._handle_locations_notification(data)
    elif data.get('collection') == 'timeline':
      self._handle_timeline_notification(data)

  def _handle_locations_notification(self, data):
    """Handle locations notification."""
    location = self.mirror_service.locations().get(id=data['itemId']).execute()
    text = 'New location is %s, %s' % (location.get('latitude'),
                                       location.get('longitude'))
    body = {
        'text': text,
        'location': location,
        'menuItems': [{'action': 'NAVIGATE'}],
        'notification': {'level': 'DEFAULT'}
    }
    self.mirror_service.timeline().insert(body=body).execute()
    
  def _handle_timeline_notification(self, data):
    """Handle timeline notification."""
    for user_action in data.get('userActions', []):
      if user_action.get('type') == 'SHARE':
        # Fetch the timeline item.
        item = self.mirror_service.timeline().get(id=data['itemId']).execute()
        attachments = item.get('attachments', [])
        media = None
        if attachments:
          # Get the first attachment on that timeline item and do stuff with it.
          attachment = self.mirror_service.timeline().attachments().get(
              itemId=data['itemId'],
              attachmentId=attachments[0]['id']).execute()
          resp, content = self.mirror_service._http.request(
              attachment['contentUrl'])
          if resp.status == 200:
            media = MediaIoBaseUpload(
                io.BytesIO(content), attachment['contentType'],
                resumable=True)
          else:
            logging.info('Unable to retrieve attachment: %s', resp.status)
        body = {
            'text': 'Echoing your shared item: %s' % item.get('text', ''),
            'notification': {'level': 'DEFAULT'}
        }
        self.mirror_service.timeline().insert(
            body=body, media_body=media).execute()
        # Only handle the first successful action.
        break
      if user_action.get('type') == 'REPLY':
        reply_id = data['itemId']
        result = self.mirror_service.timeline().get(id=reply_id).execute()
        origional_txt = result.get('text');
        translator = Translator(client_id, client_secret)
        translate_txt = translator.translate(origional_txt, "zh-CHS")
        logging.info('here!!!!!!!!!!!!!!!!')
        oauth_url = 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13'
        oauth_junk = json.loads(requests.post(oauth_url,data=urllib.urlencode(args)).content)
        headers={'Authorization': 'Bearer '+oauth_junk['access_token']}
        translation_url = "http://api.microsofttranslator.com/V2/Http.svc/Speak?"
        request_string = '%stext=%s&language=zh-CHS&format=audio/mp3' % (translation_url,translate_txt)
        translation_result = requests.get(request_string,headers=headers)
        reply_id = data['itemId']
        ###logging.info('translation_result is %s' ,translation_result.content)
        audio = translation_result.content
        audio_media = MediaIoBaseUpload(io.BytesIO(audio), mimetype='video/mp4', resumable=True)
        logging.info('%s is translated to %s' %  (origional_txt, translate_txt))
        ###clent.query_example()
        body = {
            'bundleId': 'words_with_glass',
            'menuItems': [{'action': 'DELETE'}],
            'text': translate_txt,
            'notification': {'level': 'DEFAULT'}
        }
        new_item = self.mirror_service.timeline().insert(body=body, media_body = audio_media).execute()
        logging.info("new_item %s", new_item)
        attachment_link = None
        attachment_link = self.get_attachment_link(new_item)
        ###attachment_link = 'URL: %s %s ' %(data['itemId'], attachments[0]['id'])
        logging.info(attachment_link)
        self.save_entry(origional_txt, translate_txt, str(attachment_link))

        new_template = { 'original': origional_txt,
                          'translated': translate_txt,
                          'audio': attachment_link 
        }
        self._insert_item(new_template)
        

        logging.info('attachments url is: %s', attachment_link)
      else:
        logging.info(
            "I don't know what to do with this notification: %s", user_action)

  @util.auth_required
  def _insert_item(self, translation=None):
        """Insert a timeline item."""

        template_values = { 'original': translation.original,
                            'translated': translation.translated,
                            'audio': translation.audio }
        template = jinja_environment.get_template('templates/translation-card.html')
        html = template.render(template_values)
        logging.info(html)
        body = {
            'html': html,
            'bundleId': 'words_with_glass',
            'menuItems': [{'action': 'DELETE'}],
            'notification': {'level': 'DEFAULT'}
        }
        
        # Send to glass timeline
        self.mirror_service.timeline().insert(body=body).execute()

  ### save transation result ###
  def save_entry(self, original, translated, audio):
    payload = {
      'original': original,
      'translated': translated,
      'audio': audio
    }
    requests.post("https://glassdictionary.appspot.com/save", data=payload)
  
  def get_attachment_link(self, the_item):
    attachments = the_item.get('attachments', [])
    url = '/attachmentproxy?attachment=%s&timelineItem=%s' % (attachments[0]['id'],the_item['id'])
    return url

NOTIFY_ROUTES = [
    ('/notify', NotifyHandler)
]
