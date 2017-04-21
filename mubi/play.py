#
# MUBI script to manage authentication and playback
# from the MUBI video service on Boxee Box.
#
# by Shawn Rieger / Boxee
#

import mc
import re
import simplejson as json
from xml.dom.minidom import parse, parseString

token_key = ''
token_secret = ''
debug = True

message_credit = 'To watch %s your account will be charged %s.  Would you like to proceed?'
message_geo = 'Unfortunately, %s is not available to watch in your country.  Please choose another film to watch.'
message_addcredit = 'It looks like you need to add credit to your account. You currently have %s, and need %s more to watch this film. Please visit http://mubi.com/account to add more credit.'

def log(s):
   if debug:
      print '@mubi: %s' % str(s)

def getJson(url):
   response = mc.Http().Get(url)
   log(response)
   try:
      data = re.sub('//.*?\n|/\*.*?\*/', '', response, re.S)
      data = json.loads(data)
      return data
   except Exception, e:
      return response

def authenticate():
   global token_key, token_secret
   try:
      log('checking: http://app.boxee.tv/api/get_application_data?id=mubi')
      user_keys = mc.Http().Get('http://app.boxee.tv/api/get_application_data?id=mubi')
      if not user_keys:
         mc.ShowDialogOk('MUBI', 'Server not responding or returned no result. Unable to check for account. Please contact support@boxee.tv.')
      log(user_keys)
      dom = parseString(user_keys)
      token_key = str(dom.getElementsByTagName('auth_token')[0].firstChild.data)
      token_secret = str(dom.getElementsByTagName('auth_token_secret')[0].firstChild.data)
      if token_key and token_secret:
          return True
   except:
      return False

def request(req):
   data = (req, mubi_id, token_secret, token_key)
   log('http://dir.boxee.tv/apps/mubi/call/%s/%s/%s/%s' % data)
   result = getJson('http://dir.boxee.tv/apps/mubi/call/%s/%s/%s/%s' % data)
   return result

def watch_viewing(resume=False):
   try:
      item = mc.GetApp().GetLaunchedListItem()
      watchmode = 'resume' if resume == True else 'watch'
      data = (watchmode, mubi_id, token_secret, token_key)
      data = mc.Http().Get('http://dir.boxee.tv/apps/mubi/call/%s/%s/%s/%s' % data)
      item.SetPath(data)
      #item.SetContentType('application/x-shockwave-flash')
      mc.HideDialogWait()
      mc.GetPlayer().Play(item)
      return True
   except:
      return False

def play():
   global mubi_id, mubi_price, mubi_title
   mc.ShowDialogWait()

   res = request('viewing')
   log(res['result'])
   if ( str(res['result']) == 'true'):
      if (int(res['last_time_code']) <= 0 ):
         log('viewing exists, no last time code. playing from the begining.')
         return watch_viewing()
      else:
         seconds = int(res['last_time_code'])
         log('last_time_code: '+str(seconds))
         minutes = str(int(seconds/60))
         log('time code converted: '+minutes)
         msg = "You've recently watched %s minutes of %s." % (minutes, mubi_title)
         if mc.ShowDialogConfirm('MUBI', msg, 'Start Over', 'Resume'):
            log('viewing exists, user chose to resume from last time code')
            return watch_viewing(True)
         else:
            log('viewing exists, user choose to play from the beginning.')
            return watch_viewing()
   elif str(res['result']) == '422':
      log('mubi returned status code 422, film no longer available your location.')
      mc.ShowDialogOk('MUBI', str(res['message']))
      return False
   else:
      mubi_price           = res['film_price'].encode('utf-8')
      available_credits    = res['available_credits'].encode('utf-8')
      credits_needed       = res['credits_needed'].encode('utf-8')
      has_enough_credits   = bool(res['has_enough_credits'])
      is_subscriber        = bool(res['subscriber'])
      log('_')
      log('film_price: '+mubi_price)
      log('available_credits: '+available_credits)
      log('credits_needed: '+credits_needed)
      log('has_enough_credits: '+str(has_enough_credits))
      log('is_subscriber: '+str(is_subscriber))
      log('_')
      log('no viewing exists for this film')

   if not mubi_price:
      req = str(request('freeview')['result'])
      if req == 'true': return watch_viewing()
      elif req == '422':
         mc.ShowDialogOk('MUBI', message_geo % mubi_title)
         mc.ShowDialogOk('MUBI', 'Your account was not charged for this transaction.')
         return False
      return False

   if mubi_price:
      if is_subscriber:
         log('user is a subscriber')
         req = str(request('subview')['result'])
         if req == 'true': return watch_viewing()
         elif req == '422':
            mc.ShowDialogOk('MUBI', message_geo % mubi_title)
            mc.ShowDialogOk('MUBI', 'Your account was not charged for this trasaction.')
            return False
         return False

      else:
         log('user is not a subscriber, checking available credits')
         if has_enough_credits:
            if mc.ShowDialogConfirm('MUBI', message_credit % (mubi_title, mubi_price), 'No', 'Yes'):
               req = str(request('payperview')['result'])
               if req == 'true':
                  return watch_viewing()
               elif req == '422':
                  mc.ShowDialogOk('MUBI', message_geo % mubi_title)
                  mc.ShowDialogOk('MUBI', 'Your account was not charged for this trasaction.')
                  return False
               else:
                  return False
         else:
            log('user does not have enough credits available to play film')
            mc.ShowDialogOk('MUBI', message_addcredit % (available_credits, credits_needed))
            return True
   mc.HideDialogWait()
   return False

mubi_ok = False

#mc.ShowDialogOk('test', u'\xa33')

try:
   params = mc.GetApp().GetLaunchedScriptParameters()
   item = mc.GetApp().GetLaunchedListItem()
   if debug: item.Dump()
   mubi_price = ''
   mubi_id = str(params['id'])
   mubi_title = item.GetLabel()
   mubi_ok = True
   log('id: '+mubi_id)
   log('title: '+mubi_title)
except:
   log('unable to parse launch parameters')
   mc.ActivateWindow(14000)

if not authenticate():
   mc.ActivateWindow(14000)
   mc.GetWindow(14000).GetControl(121).SetVisible(True)
else:
   mc.GetWindow(14000).GetControl(121).SetVisible(False)
   if mubi_ok:
      play()
      #try: play()
      #except: mc.ShowDialogOk('MUBI', 'There was a problem playing %s.  Please try again.  If the problem persists, please contact us at support@boxee.tv.' % mubi_title)
      mc.HideDialogWait()
