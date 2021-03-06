# -*- coding: utf-8 -*-

__author__ = 'vladimir'
__skype__ = 'volkvid'
__email__ = 'volkvid@yandex.ru'

import sys
from os import path
import time
import hashlib
import binascii

import json
import urllib
import requests

import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.type.ttypes as Types
from evernote.api.client import EvernoteClient

#shoeboxed endpoints
authorize_url = "https://id.shoeboxed.com/oauth/authorize"
token_url = "https://id.shoeboxed.com/oauth/token"

def main():
    global StartPath, authData, authorize_url, token_url, auth_token
    # 1
    StartPath = getCurrentPath()
    if not path.isfile(StartPath + 'authorize.txt'):
        #model template (for new user) with interactive instructions
        persInfo = {}
        persInfo["shoeboxed"] = {
            "ID": "your_ID",
            "Account_ID": "auto_Account_ID", 
            "Secret": "your_Secret", 
            "redirect_uri": "your_redirect_uri",
            "state": "random_CSRFkey", 
            "access_token": "auto_access_token",
            "refresh_token": "auto_refresh_token", 
            "code": "code_from_url_here"
        }
        persInfo["evernote"] = {
            "auth_token": "your_auth_token"
        }

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
        print ("\nOpen next link\n\n" + str(returnAuthURL(persInfo)) + "\n\nAuthorize to shoeboxed and allow access."+
               "You'll be redirected to 'redirect_uri'. Click on address line - there will be something like this: http://rezoh.ru/?code="+
               "933bed8f-cdc8-4628-8ce2-b51c976ed223&state=random_CSRF_key\n\nand paste 'code' value below and press enter:")
        inp = raw_input()
        persInfo['shoeboxed']['code'] = inp

        #EVERNOTE interactive
        print("\nNow Evernote. Visit and create token \nhttps://www.evernote.com/api/DeveloperToken.action"\
              "\n\nPaste it below and press Enter:")
        inp = raw_input()
        persInfo['evernote']['auth_token'] = inp

        #save auth data
        authorize = open(StartPath + 'authorize.txt', 'w+')
        authorize.write(json.dumps(persInfo))
        authorize.close()
    authData = readAuthDataFromFile()

    if not path.isfile(StartPath + 'indexFile.txt'): 
        indexFile = open(StartPath + 'indexFile.txt', 'w+')
        indexFile.write(json.dumps({'IDs':[], 'offset':0}))
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

    #SAVE AUTHDATA 
    authorize = open(StartPath + 'authorize.txt', 'w+')
    authorize.write(json.dumps(authData))
    authorize.close()

    sUserInfo = callSAPI2()
    if sUserInfo.status_code in [401, 404]:
        print '\nrefreshing token'
        r = refreshAccessToken()
        try:
            authData['shoeboxed']['access_token'] = r['access_token']
            sUserInfo = json.loads(callSAPI2().text)
            authData['shoeboxed']['Account_ID'] = sUserInfo['accounts'][0]['id']
        except BaseException as exc:
            print 'Error 4:', str(exc), ', new r =', r,
            print '\n\nIncorrect data. Delete authorize.txt and restart script!'
            sys.exit(2)
    else:
        sUserInfo = json.loads(sUserInfo.text)
        print '\nsUserInfo =', sUserInfo, '\n'
        authData['shoeboxed']['Account_ID'] = sUserInfo['accounts'][0]['id']

    # 3
    print "\n--Auth to EVERNOTE"
    try:
        client = EvernoteClient(token=authData['evernote']['auth_token'], sandbox=False)
    except BaseException as ex:
        print "\nError message :", ex
        print "\nIf token expired, visit \nhttps://www.evernote.com/api/DeveloperToken.action"\
              "\n\nPaste it below and press Enter:"
        inp = raw_input()
        authData['evernote']['auth_token'] = inp
        client = EvernoteClient(token=authData['evernote']['auth_token'], sandbox=False)        
        
    user_store = client.get_user_store()
    version_ok = user_store.checkVersion(
        "Evernote EDAMTest (Python)",
        UserStoreConstants.EDAM_VERSION_MAJOR,
        UserStoreConstants.EDAM_VERSION_MINOR
    )
    
    # find notebook 
    notebookTargetName = "Shoeboxed"
    targetNotebook = Types.Notebook()

    note_store = client.get_note_store()
    notebooks = []
    for notebook in note_store.listNotebooks():
        notebooks.append(notebook.name) 
        if notebook.name == notebookTargetName:
            targetNotebook = notebook
    # or create if no
    if notebookTargetName not in notebooks:
        targetNotebook.name = notebookTargetName
        targetNotebook = note_store.createNotebook(targetNotebook)
        print "Notebook named " + notebookTargetName + " was created"

    notebookGUID = targetNotebook.guid
    print 'notebookGUID =', notebookGUID

    # ? 
    S = ['1 - OTHER IN QB', '1 - RECEIPT IN QB', '1 - STATEMENT RECONCILED IN QB',
         'Manoj - Ask Richard', 'Manoj - Duplicate', 'Manoj - Entered', 'Richard', 'Richard Responded']
    s = []
    for t in S:
        s.append(t.lower().replace(' ', ''))

    # process starts here
    
    uncreatedNotes = []
    data = callSAPI(offset = 0, limit = 1) 
    try:
        json_data = json.loads(data.text)
    except BaseException as ex:
        r = refreshAccessToken()
        try:
            authData['shoeboxed']['access_token'] = r['access_token']
            data = callSAPI(offset = 0, limit = 1)
            json_data = json.loads(data.text)
        except BaseException as exc:
            print 'Error 3:', str(exc), '\n\nRESTART ONLY'

    totalCount = json_data['totalCountFiltered']
    print '\n--total count of Receipts in Shoeboxed acc', totalCount

    i = 1
    offset = ids['offset']
    if Num == -1:
        Num = totalCount - offset  
        print '\n--Left to sync =', Num # absolute number to complete
    else:
        print '\n--Num to sync =', Num  # required number
    
    print '\n--offset now =', offset, '\n'
    for step in range(totalCount-offset): 
        data = callSAPI(offset = step+offset, limit = 1) 
        try:
            json_data = json.loads(data.text)
            if data.status_code in [401, 404]:
                r = refreshAccessToken()
                try:
                    authData['shoeboxed']['access_token'] = r['access_token']
                    data = callSAPI(offset = step+offset, limit = 1)
                    json_data = json.loads(data.text)
                except BaseException as exc:
                    print 'Error 7:', str(exc), '\n\nRESTART ONLY'
            oneReceipt = json_data['documents'][0] 
        except BaseException as ex:
            print 'Error 6:', str(ex), '\n\nRESTART ONLY'
                
        if oneReceipt['id'] not in ids['IDs']:
            print '-Receipt #', i,'\n', oneReceipt
            # creating basic Note object 
            note = Types.Note()
            note.notebookGuid = notebookGUID
            
            # deletes all spaces at the end of the word if word exists 
            try:
                st = oneReceipt['vendor']
                c = len(oneReceipt['vendor'])-1
                while c > 0:
                    if st[c] == " ":
                        st = st[:c]
                        c -= 1
                    else:
                        break
                oneReceipt['vendor'] = st
                del(st, c)
            except:
                pass

            # add title
            try:
                note.title = oneReceipt['issued'][:oneReceipt['issued'].find('T')]+' - '+oneReceipt['vendor']
            except:
                try:
                    note.title = 'none - '+oneReceipt['vendor']
                except:
                    try:
                        note.title = oneReceipt['issued'][:oneReceipt['issued'].find('T')]+' - none'
                    except:
                        note.title = 'none - none'

            # add times
            try:
                t = oneReceipt['uploaded'][:oneReceipt['uploaded'].find('T')]
                t = time.mktime(time.strptime(t, "%Y-%m-%d"))*1000
                note.created = t
            except:
                print 'No uploaded time'

            try:
                t = oneReceipt['modified'][:oneReceipt['modified'].find('T')]
                t = time.mktime(time.strptime(t, "%Y-%m-%d"))*1000
                note.updated = t
            except:
                print 'No modified time'

            attachment = ""
            try:
                # downloading pdf by link and formating
                imageURL = oneReceipt['attachment']['url']
                image = urllib.urlopen(imageURL, proxies={}).read()
                md5 = hashlib.md5()
                md5.update(image)
                hash = md5.digest()

                # uploading to evernote
                data = Types.Data()
                data.size = len(image)
                data.bodyHash = hash
                data.body = image
                
                resource = Types.Resource()
                resource.mime = 'application/pdf'
                resource.data = data
                note.resources = [resource]

                hash_hex = binascii.hexlify(hash)
                attachment = "yes"
            except:
                print "Warning: No attachment"
                attachment = "no"
            
            # creating Tag object from Categories
            try:
                tags = ['Shoeboxed', 'Shoeboxed ' + oneReceipt['source']['type']]
            except:
                tags = ['Shoeboxed']                

            try:
                if oneReceipt['source']['type'] == 'mail':
                    tags.append('G:'+oneReceipt['source']['envelope'])
            except:
                pass
                #will be no G-tags

            try:
                for tag in oneReceipt['categories']:
                    if tag.replace('&', '&amp;').encode('utf-8').lower().replace(' ', '') in s:
                        tags.append('S:'+tag.replace('&', '&amp;').encode('utf-8'))
                    else:
                        tags.append('T:'+tag.replace('&', '&amp;').encode('utf-8'))
            except:
                pass
                #will be no tags at all 

            note.tagNames = tags

            # representing Data
            note.content = '<?xml version="1.0" encoding="UTF-8"?>'
            note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'\
                            '<en-note>'

            try:
                note.content += '<h2>'+oneReceipt['issued'][:oneReceipt['issued'].find('T')]+' - '+\
                                oneReceipt['vendor'].replace('&', '&amp;')+'</h2><table bgcolor="#F0F0F0" border="0" width="60%">'
            except:
                try:
                    note.content += '<h2>none - '+oneReceipt['vendor'].replace('&', '&amp;')+'</h2><table bgcolor="#F0F0F0" border="0" width="60%">'
                except:
                    try:
                        note.content += '<h2>'+oneReceipt['issued'][:oneReceipt['issued'].find('T')]+' - none</h2><table bgcolor="#F0F0F0" border="0" width="60%">'
                    except:
                        note.content += '<h2>none - none</h2><table bgcolor="#F0F0F0" border="0" width="60%">'
                        print 'No ussued and no vendor name'

            try:
                note.content += makeTableRow('Receipt Date', oneReceipt['issued'][:oneReceipt['issued'].find('T')])
            except:
                note.content += makeTableRow('Receipt Date', 'none')

            try:
                note.content += makeTableRow('Receipt Total', str(oneReceipt['total']))
            except:
                note.content += makeTableRow('Receipt Total', 'none')

            try:
                note.content += makeTableRow('Receipt Tax', str(oneReceipt['tax']))
            except:
                note.content += makeTableRow('Receipt Tax', 'none')
                
            try:
                note.content += makeTableRow('Receipt Currency', oneReceipt['currency'])
            except:
                note.content += makeTableRow('Receipt Currency', 'none')
                
            try:
                dig = int(oneReceipt['paymentType']['lastFourDigits'])
                note.content += makeTableDoubleRow(['Payment', 'Type'], [oneReceipt['paymentType']['type'],
                                                    '**** **** **** ' + str(dig)])
            except:
                try:
                    note.content += makeTableDoubleRow(['Payment', 'Type'], [oneReceipt['paymentType']['type'], '**** **** **** none'])
                except:
                    note.content += makeTableRow('Payment Type', 'none')

            try:
                note.content += makeTableRow('Notes', oneReceipt['notes'].replace('&', '&amp;'))
            except:
                note.content += makeTableRow('Notes', 'none')
                
            note.content += makeTableRow('&nbsp;', '&nbsp;')

            try:
                note.content += makeTableRow('Document ID', oneReceipt['id'])
            except:
                note.content += makeTableRow('Document ID', 'error document ID, none')

            try:
                note.content += makeTableRow('Envelope ID', oneReceipt['source']['envelope'])
            except:
                pass
                
            try:
                note.content += makeTableRow('Date Uploaded', oneReceipt['uploaded'][:oneReceipt['uploaded'].find('T')])
            except:
                note.content += makeTableRow('Date Uploaded', 'none')
                
            try:
                note.content += makeTableRow('Date Modified', oneReceipt['modified'][:oneReceipt['modified'].find('T')])
            except:
                note.content += makeTableRow('Date Modified', 'none')
                
            try:
                note.content += makeTableRow('Invoice Number', oneReceipt['invoiceNumber'])
            except:
                note.content += makeTableRow('Invoice Number', 'none')

            try:
                note.content += makeTableRow('Total in Preferred Currency', str(oneReceipt['totalInPreferredCurrency']))
            except:
                note.content += makeTableRow('Total in Preferred Currency', 'none')
                
            try:
                note.content += makeTableRow('Tax in Preferred Currency', str(oneReceipt['taxInPreferredCurrency']))
            except:
                note.content += makeTableRow('Tax in Preferred Currency', 'none')

            try:
                note.content += makeTableRow('Trashed?', str(oneReceipt['trashed']))
            except:
                note.content += makeTableRow('Trashed?', 'none')

            try:
                note.content += makeTableRow('Document source', oneReceipt['source']['type'])
            except:
                note.content += makeTableRow('Document source', 'none')

            if attachment == "yes":
                note.content += '</table><br/><br/><en-media type="application/pdf" hash="' + hash_hex + '"/>'
            else:
                note.content += '</table><br/><br/>' #if no attachment 
            note.content += '</en-note>'

            try:
                created_note = note_store.createNote(note)
                #SAVE document ID every step - its safer
                ids['IDs'].append(oneReceipt['id'])
                ids['offset'] = i + offset
                i += 1
                indexFile = open(StartPath + 'indexFile.txt', 'w+')
                indexFile.write(json.dumps(ids))
                indexFile.close()
            except BaseException as ex:
                print "\nError creating note =", str(ex), "\nreceipt id =", oneReceipt['id'], "\n"
                uncreatedNotes.append(oneReceipt['id'])
            print ""

        #don't move this statement below!
        if i > Num: 
            break

    print '\nAll added notes ids:\n', ids['IDs']
    if len(uncreatedNotes) > 0:
        print '\nError occured in notes ids:\n', uncreatedNotes
    #SAVE AUTHDATA 
    authorize = open(StartPath + 'authorize.txt', 'w+')
    authorize.write(json.dumps(authData))
    authorize.close()
    

#representation of result
def makeTableRow(name, val):
    if val == "":
        val = "none"
    return "<tr><td>{0}</td><td>{1}</td></tr>".format(name, val)

    
def makeTableDoubleRow(name, val):
    no = ""
    for n in name:
        no += n + "<br/>"
    vo = ""
    for v in val:
        vo += v + "<br/>"
    return "<tr><td>{0}</td><td>{1}</td></tr>".format(no, vo)
    

#shoeboxed auth (one time)
def obtainAccessToken():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {
        "code": authData["shoeboxed"]["code"],
        "redirect_uri": authData["shoeboxed"]["redirect_uri"],
        "grant_type": "authorization_code"
    }
    r = requests.post(token_url, headers=headers, params=params, auth=(authData["shoeboxed"]["ID"], authData["shoeboxed"]["Secret"]))
    r = json.loads(r.text)
    print "\nobtainAccessToken returns", r, "\n"
    return r


#shoeboxed auth (all other times)
def refreshAccessToken():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {
        "refresh_token": authData["shoeboxed"]["refresh_token"],
        "redirect_uri": authData["shoeboxed"]["redirect_uri"],
        "grant_type": "refresh_token"
    }
    r = requests.post(token_url, headers=headers, params=params, auth=(authData["shoeboxed"]["ID"], authData["shoeboxed"]["Secret"]))
    return json.loads(r.text)
    

def callSAPI(offset, limit=100):
    print "\n--Call SHOEBOXED API (documents)"
    headers = {
        "Authorization": "Bearer " + authData['shoeboxed']['access_token'],
        "Content-Type": "application/json"
    }
    params = {
        "type": "receipt",
        "offset": offset,
        "limit": limit
    }
    r = requests.get("https://api.shoeboxed.com/v2/accounts/"+authData['shoeboxed']['Account_ID']+'/documents/?', headers=headers, params=params)
    print "    'documents' status code:", r.status_code
    return r


def callSAPI2():
    print "\n--Call SHOEBOXED API (user)"
    headers = {
        "Authorization": "Bearer " + authData['shoeboxed']['access_token'],
        "Content-Type": "application/json"
    }
    r = requests.get("https://api.shoeboxed.com/v2/user/?", headers=headers)
    print "'user' status code:", r.status_code
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
    params = {
        "client_id": data["shoeboxed"]["ID"],
        "redirect_uri": data["shoeboxed"]["redirect_uri"],
        "state": data["shoeboxed"]["state"],
        "response_type": "code",
        "scope": "all"
    }
    return "https://id.shoeboxed.com/oauth/authorize?" + urllib.urlencode(params)


# gets the current location of script-file
def getCurrentPath():
    spath = ''
    if len(path.dirname(sys.argv[0])) != 0:
        spath += path.dirname(sys.argv[0]) + path.sep
    return spath


if __name__ == "__main__":
    main()
