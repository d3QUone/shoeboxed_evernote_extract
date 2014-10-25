# -*- coding: utf-8 -*-
import requests
import urllib
import json
import sys
from os import path

import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.type.ttypes as Types
from evernote.api.client import EvernoteClient

import time
import hashlib
import binascii

#shoeboxed info
authorize_url = 'https://id.shoeboxed.com/oauth/authorize'    
token_url = 'https://id.shoeboxed.com/oauth/token'
#evernote info
auth_token = "S=s519:U=5174815:E=1509b265235:C=149437524d8:P=1cd:A=en-devtoken:V=2:H=f4b59d04da0aa9e051190aa615d08e6f"

def main():
    global StartPath, authData, authorize_url, token_url, auth_token
    # 1
    StartPath = getCurrentPath()
    if not path.isfile(StartPath + 'authorize.txt'):
        persInfo = {}
        #model template (for new user) with interactive instructions
        persInfo['shoeboxed'] = {"ID":'your_ID', "Account_ID":'auto_Account_ID', "Secret":'your_Secret', "redirect_uri":'your_redirect_uri',
                                 "state":'random_CSRFkey', "access_token":'auto_access_token', 
                                 "refresh_token":'auto_refresh_token', "code":'code_from_url_here'}
        persInfo['evernote'] = {"auth_token":'your_auth_token'}
        #SHOEBOXED interactive instructions
        print ("Open the link below and create a new appp:\n\nhttps://app.shoeboxed.com/member/v2/user-settings#api"+
               "\n\nPaste 'ID' below and press Enter:")
        inp = raw_input()
        persInfo['shoeboxed']['ID'] = inp
        print ("Paste 'Secret' below and press Enter:")
        inp = raw_input()
        persInfo['shoeboxed']['Secret'] = inp
        print ("Paste 'redirect_uri' below and press Enter:")
        inp = raw_input()
        persInfo['shoeboxed']['redirect_uri'] = inp
        print ("Then open next link\n\n" + str(returnAuthURL(persInfo)) + "\n\nAuthorize to shoeboxed and allow access."+
               "You'll be redirected to 'redirect_uri'. Click on address line - there will be something like this: http://rezoh.ru/?code="+
               "933bed8f-cdc8-4628-8ce2-b51c976ed223&state=random_CSRF_key\n\nand paste 'code' value below and press enter:")
        inp = raw_input()
        persInfo['shoeboxed']['code'] = inp

        #EVERNOTE interactive
        print("Please fill in your developer token\nTo get a developer token,"\
              "visit https://www.evernote.com/api/DeveloperToken.action"\
              "\n\nPaste it below and press Enter:")
        inp = raw_input()
        persInfo['evernote']['auth_token'] = inp
        
        '''
        #model with my current account datas (for simplify testing)
        persInfo['shoeboxed'] = {"ID":'4ad9df8b07bc444482d2f568981439bc', "Secret":'Ma91KV1M1gwIK.NzDYfuheKG64sywYouYzU882aez8d2zMs7toh.2',
                                 "redirect_uri":'http://rezoh.ru', "state":'random_CSRF_key', "access_token":'auto_access_token', 
                                 "refresh_token":'auto_refresh_token', "code":'code_from_url_here'}

        print ("Open the link below and create a new appp\n\nhttps://app.shoeboxed.com/member/v2/user-settings#api\n\nThen open next\n\n"+
               str(returnAuthURL(persInfo)) + "\n\nAuthorize to shoeboxed and allow access. You'll be redirected. "+
               "Click on address line - there will be something like this: http://rezoh.ru/?code="+
               "933bed8f-cdc8-4628-8ce2-b51c976ed223&state=random_CSRF_key\n\nPaste 'code' value below and press enter:")
        inp = raw_input() #code
        persInfo['shoeboxed']['code'] = inp.replace('\n', '')
        #the same with evernote (or may be easier)
        persInfo['evernote'] = {"Key":'volkvid', "Secret":'bf8294717d32907e', "token":'auto_token'}
        '''
        authorize = open(StartPath + 'authorize.txt', 'w+')
        authorize.write(json.dumps(persInfo))
        authorize.close()
    authData = readAuthDataFromFile()

    if not path.isfile(StartPath + 'indexFile.txt'): 
        indexFile = open(StartPath + 'indexFile.txt', 'w+')
        indexFile.write(json.dumps({'IDs':[]}))
        indexFile.close()
        print "--Empty indexFile (JSON with IDs of Receipts) was created"
    ids = readIDsFromFile()

    if not path.isfile(StartPath + 'Num.txt'):
        print "--Error. No Num file was found. Enter Num (integer only, -1 meals all Recieps) below to create Num file:"
        inp = raw_input()
        NumFile = open(StartPath + 'Num.txt', 'w+')
        try:
            inp = int(inp)
            NumFile.write('Num='+str(inp)+';')
        except BaseException as ex:
            print 'Error 1:', ex, '\nNum file created with Num=-1, you can change it manually'
            NumFile.write('Num=-1;')
        NumFile.close()
    Num = readNumFromFile()

    # 2
    print '--Auth to SHOEBOXED'        
    if authData['shoeboxed']['access_token'] == 'auto_access_token':
        #means no token 
        print 'Creating access_token'        
        r = obtainAccessToken()
        try:
            authData['shoeboxed']['access_token'] = r['access_token']
            authData['shoeboxed']['refresh_token'] = r['refresh_token']
        except BaseException as ex:
            print 'Error 2:', str(ex), ', trying to renew token.\n'
            r = refreshAccessToken()
            try:
                authData['shoeboxed']['access_token'] = r['access_token']
            except BaseException as exc:
                print 'Error 3:', str(exc), ', new r =', r, '\n'

    sUserInfo = callSAPI2()
    print '\nsUserInfo =', sUserInfo, '\n'
    if sUserInfo.status_code in [401, 404]:
        print 'refreshing token'
        r = refreshAccessToken()
        try:
            authData['shoeboxed']['access_token'] = r['access_token']
            sUserInfo = json.loads(callSAPI2().text)
            authData['shoeboxed']['Account_ID'] = sUserInfo['accounts']['id']
        except BaseException as exc:
            print 'Error 4:', str(exc), ', new r =', r, '\n'
    #else:
    #    sUserInfo = json.loads(callSAPI2().text)
        #authData['shoeboxed']['Account_ID'] = sUserInfo['accounts']['id']

    # auth to evernote
    print "--Auth to EVERNOTE"
    client = EvernoteClient(token=auth_token, sandbox=False) #persInfo['evernote']['auth_token']
    user_store = client.get_user_store()
    version_ok = user_store.checkVersion(
        "Evernote EDAMTest (Python)",
        UserStoreConstants.EDAM_VERSION_MAJOR,
        UserStoreConstants.EDAM_VERSION_MINOR
    )
    
    # check notebook and create if none
    notebookTargetName = "Shoeboxed"
    targetNotebook = Types.Notebook()

    note_store = client.get_note_store()
    notebooks = []
    for notebook in note_store.listNotebooks():
        notebooks.append(notebook.name) 
        if notebook.name == notebookTargetName:
            targetNotebook = notebook
    
    if notebookTargetName not in notebooks:
        targetNotebook.name = notebookTargetName
        targetNotebook = note_store.createNotebook(targetNotebook)
        print "Notebook named " + notebookTargetName + " was created"

    notebookGUID = targetNotebook.guid
    print 'notebookGUID =', notebookGUID

    S = ['1 - OTHER IN QB', '1 - RECEIPT IN QB', '1 - STATEMENT RECONCILED IN QB',
         'Manoj - Ask Richard', 'Manoj - Duplicate', 'Manoj - Entered', 'Richard', 'Richard Responded']
    s = []
    for t in S:
        s.append(t.lower().replace(' ', ''))

    i = 1
    uncreatedNotes = []
    data = callSAPI()
    print 'data.status_code =', data.status_code, '\n'
    json_data = json.loads(data.text)

    if Num == -1:
        Num = json_data['totalCountFiltered']
    print '\n--Num to sync =', Num, '\n'
    
    for oneReceipt in json_data['documents']:
        if oneReceipt['id'] not in ids['IDs']:
            print 'Receipt #', i,'\n', oneReceipt

            # creating Note object 
            note = Types.Note()
            note.notebookGuid = notebookGUID 
            note.title = (oneReceipt['issued'][:oneReceipt['issued'].find('T')]+' - '+
                          oneReceipt['vendor'])

            # add times 
            t = oneReceipt['uploaded'][:oneReceipt['uploaded'].find('T')]
            t = time.mktime(time.strptime(t, "%Y-%m-%d"))*1000
            note.created = t

            t = oneReceipt['modified'][:oneReceipt['modified'].find('T')]
            t = time.mktime(time.strptime(t, "%Y-%m-%d"))*1000
            note.updated = t
            
            # downloading pdf by link and formating

            imageURL = oneReceipt['attachment']['url']
            image = urllib.urlopen(imageURL, proxies={}).read() #open('enlogo.png', 'rb').read()
            md5 = hashlib.md5()
            md5.update(image)
            hash = md5.digest()

            data = Types.Data()
            data.size = len(image)
            data.bodyHash = hash
            data.body = image

            resource = Types.Resource()
            resource.mime = 'application/pdf'
            resource.data = data

            note.resources = [resource]

            hash_hex = binascii.hexlify(hash)

            # creating Tag object from Categories
            #need fix to tech task
            tags = ['Shoeboxed', 'Shoeboxed ' + oneReceipt['source']['type']]
            if oneReceipt['source']['type'] == 'mail':
                tags.append('G:'+oneReceipt['source']['envelope'])

            #isS = 'no'
            for tag in oneReceipt['categories']:
                if tag.replace('&', 'amp;').encode('utf-8').lower().replace(' ', '') in s:
                    tags.append('S:'+tag.replace('&', 'amp;').encode('utf-8'))
                    #isS = 'yes'
                else:
                    tags.append('T:'+tag.replace('&', 'amp;').encode('utf-8'))
                    
            '''
            for tag in oneReceipt['categories']:
                if tag.lower().replace(' ', '') not in s and isS == 'no':
                    tags.append('T:'+tag.replace('&', 'amp;').encode('utf-8'))'''
                
            note.tagNames = tags

            # composing all data into Note
            note.content = '<?xml version="1.0" encoding="UTF-8"?>'
            note.content += '<!DOCTYPE en-note SYSTEM ' \
                '"http://xml.evernote.com/pub/enml2.dtd">'
            note.content += '<en-note>Document.id: '+oneReceipt['id']+'<br/>'
            try:
                note.content += 'Document.invoiceNumber: '+oneReceipt['']+'<br/>'
            except:
                note.content += 'Document.invoiceNumber: None<br/>'                
            note.content += 'Document.notes: '+oneReceipt['notes'].replace('&', '&amp;')+'<br/>'
            #note.content += 'Document.paymentType: '+oneReceipt['paymentType']+'<br/>'
            note.content += 'DocumentSource.name: '+oneReceipt['source']['name']+'<br/>'
            note.content += 'Document.total: '+str(oneReceipt['total'])+'<br/>'
            note.content += 'Document.tax: '+str(oneReceipt['tax'])+'<br/>'
            note.content += 'Document.totalInPreferredCurrency: '+str(oneReceipt['totalInPreferredCurrency'])+'<br/>'
            note.content += 'Document.taxInPreferredCurrency: '+str(oneReceipt['taxInPreferredCurrency'])+'<br/>'
            note.content += 'Document.currency: '+str(oneReceipt['currency'])+'<br/>'
            note.content += 'Document.trashed: '+str(oneReceipt['trashed'])+'<br/>'
            note.content += 'DocumentSourse.type: '+oneReceipt['source']['type']+'<br/>'
            note.content += 'PaymentType.type: '+oneReceipt['paymentType']['type']+'<br/>'
            try:
                note.content += 'PaymentType.lastFourDigits: '+oneReceipt['paymentType']['lastFourDigits']+'<br/>'
            except:
                note.content += 'PaymentType.lastFourDigits: None<br/>'
            note.content += '<en-media type="application/pdf" hash="' + hash_hex + '"/>'
            note.content += '</en-note>'

            try:
                created_note = note_store.createNote(note)
                ids['IDs'].append(oneReceipt['id'])
            except BaseException as ex:
                print "\nError creating note =", ex, "\nreceipt id =", oneReceipt['id'], "\n"
                uncreatedNotes.append(oneReceipt['id'])
                # uncreated notes will be repeated after 

            i += 1
            print ""
            
        if i > Num:
            break
            # out of Num Receipt limit 

    print '\nAll added notes ids :', ids, '\n\nError occured in notes with ids :', uncreatedNotes
        
    #SAVE AUTHDATA 
    authorize = open(StartPath + 'authorize.txt', 'w+')
    authorize.write(json.dumps(authData))
    authorize.close()

    #SAVE document IDs
    indexFile = open(StartPath + 'indexFile.txt', 'w+')
    indexFile.write(json.dumps(ids))
    indexFile.close()
    

def callSAPI():
    print '\n--Call SHOEBOXED API (documents)'
    sapi_url = 'https://api.shoeboxed.com/v2/'    
    headers = {"Authorization": "Bearer " + authData['shoeboxed']['access_token'],
               "Content-Type":"application/json"}
    params = {}
    params['type'] = 'receipt'
    r = requests.get(sapi_url+'accounts/'+authData['shoeboxed']['Account_ID']+'/documents/?',
                     headers=headers, params=params)
    print "'documents'status code:", r.status_code
    return r
    '''try:
        return json.loads(r.text)
    except BaseException as ex:
        print 'callSAPI error occur:', str(ex) 
        return 'error'''


def callSAPI2():
    print '\n--Call SHOEBOXED API (user)'
    sapi_url = 'https://api.shoeboxed.com/v2/'    
    headers = {"Authorization": "Bearer " + authData['shoeboxed']['access_token'],
               "Content-Type":"application/json"}
    r = requests.get(sapi_url+'user/?', headers=headers)
    print "'user'status code:", r.status_code
    return r
    

#shoeboxed auth (one time)
def obtainAccessToken():
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {}
    params['code'] = authData['shoeboxed']['code']
    params['grant_type'] = 'authorization_code'
    params['redirect_uri'] = authData['shoeboxed']['redirect_uri']

    r = requests.post(token_url, headers=headers, params=params,
                      auth=(authData['shoeboxed']['ID'], authData['shoeboxed']['Secret']))
    r = json.loads(r.text)
    return r


#shoeboxed auth (all other times)
def refreshAccessToken():
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {}
    params['refresh_token'] = authData['shoeboxed']['refresh_token'] 
    params['grant_type'] = 'refresh_token'
    params['redirect_uri'] = authData['shoeboxed']['redirect_uri']

    r = requests.post(token_url, headers=headers, params=params,
                      auth=(authData['shoeboxed']['ID'], authData['shoeboxed']['Secret']))
    r = json.loads(r.text)
    return r
    

def readAuthDataFromFile():
    authFile = open(StartPath + 'authorize.txt')
    content = authFile.read()
    authFile.close()
    return json.loads(content)


def readIDsFromFile():
    indexFile = open(StartPath + 'indexFile.txt')
    data = indexFile.read()
    indexFile.close()
    return json.loads(data)


def readNumFromFile():
    numFile = open(StartPath + 'Num.txt')
    num = numFile.read()
    num = num[num.find('=')+1:num.find(';')]
    return int(num)
        
        
def returnAuthURL(data):
    authData = data
    params = {}
    params['client_id'] = authData['shoeboxed']['ID']
    params['response_type'] = 'code'
    params['scope'] = 'all'
    params['redirect_uri'] = authData['shoeboxed']['redirect_uri']
    params['state'] = authData['shoeboxed']['state']
    #authorize_url = 'https://id.shoeboxed.com/oauth/authorize' 
    return 'https://id.shoeboxed.com/oauth/authorize?'+urllib.urlencode(params)


# gets the current location of script-file
def getCurrentPath():
    spath = ''
    if len(path.dirname(sys.argv[0])) != 0:
        spath += path.dirname(sys.argv[0]) + path.sep
    return spath


main()
