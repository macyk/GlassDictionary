
import json
import requests
import urllib

args = {
	        'client_id': 'miaomiaogames',#your client id here
	        'client_secret': 'lSBAhsgrsQI7rnAb1VURVqrtQrYU53giv/4HdIIlf7A=',#your azure secret here
	        'scope': 'http://api.microsofttranslator.com',
	        'grant_type': 'client_credentials'
	    }

def translate_txt():
	oauth_url = 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13'
	oauth_junk = json.loads(requests.post(oauth_url,data=urllib.urlencode(args)).content)
	translation_args = {
	        'text': "hello",
	        'to': 'ru',
	        'from': 'en'
	        }
	headers={'Authorization': 'Bearer '+oauth_junk['access_token']}
	translation_url = 'http://api.microsofttranslator.com/V2/Ajax.svc/Translate?'
	translation_result = requests.get(translation_url+urllib.urlencode(translation_args),headers=headers)
	print translation_result.content

def read_word():
	oauth_url = 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13'
	oauth_junk = json.loads(requests.post(oauth_url,data=urllib.urlencode(args)).content)
	translation_args = {
	        'text': "hello",
	        'language': 'en'
	        }
	headers={'Authorization': 'Bearer '+oauth_junk['access_token']}
	translation_url = 'http://api.microsofttranslator.com/V2/Http.svc/Speak?'
	translation_result = requests.get(('http://api.microsofttranslator.com/v2/Http.svc/Speak?text=welcome&language=en&format=audio/mp3'),headers=headers)
	print type(translation_result.content)

read_word()