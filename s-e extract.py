# -*- coding: utf-8 -*-
import requests
import urllib
import json
import sys
from os import path
import evernote

authorize_url = 'https://id.shoeboxed.com/oauth/authorize'    
token_url = 'https://id.shoeboxed.com/oauth/token'

def main():
    global StartPath, authData, authorize_url, token_url
    StartPath = getCurrentPath()

    if not path.isfile(StartPath + 'authorize.txt'):
        persInfo = {}
        
        #model template (for new user) w UI
        persInfo['shoeboxed'] = {"ID":'your_ID', "Secret":'your_Secret', "redirect_uri":'your_redirect_uri',
                                 "state":'random_CSRFkey', "access_token":'auto_access_token', 
                                 "refresh_token":'auto_refresh_token', "code":'code_from_url_here'}
        persInfo['evernote'] = {'Key':'your_Key', 'Secret':'your_Secret', 'token':'auto_token'}
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

        #EVERNOTE is not tested yet, have to use its SDK
        print("\nAuth to evernote and create 'Key' and 'Sedret'\nPaste 'Key' below and press Enter:")
        inp = raw_input()
        persInfo['evernote']['Key'] = inp
        print("Paste 'Secret' below and press Enter:")
        inp = raw_input()
        persInfo['evernote']['Secret'] = inp
        
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
        #file with key "IDs" and list of all ids

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
        
    #1 check if token exists
    #1 yes, go to requesting (2)
    #1 no, authorize, go to requesting (2)
    #2 try to make API request
    #2 ok, save data, go to next req
    #2 error, refresh access_token, repeat req
    #3 the same for Evernote will be below

    #new!
    print '--Authorizing to SHOEBOXED below'
    #incorect, check what is without 'limit', make a request and then parse json in while 
        
    if authData['shoeboxed']['access_token'] == 'auto_access_token':
        print 'creating access_token'        
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
                

    #need to check token validation 
    data = callSAPI()
    if data == 'error':
        r = refreshAccessToken()
        try:
            authData['shoeboxed']['access_token'] = r['access_token']
            data = callSAPI()
        except BaseException as exc:
            print 'Error 4:', str(exc), ', new r =', r, '\n'

    print 'data:', data
    #now convert and export to evernote using SDK
    if Num == -1:
        pass
        # Num = data['totalCountFiltered'] #int, from https://api.shoeboxed.com/v2/explorer/index.html#!/v2/getDocuments
        # all docs by filter Receipt 
        
    i = 1
    while i < Num: 
        #here work with evernote SDK
        
        i += 1 #itterate if no errors exporting/importing 



    #SAVE AUTHDATA for the future
    authorize = open(StartPath + 'authorize.txt', 'w+')
    authorize.write(json.dumps(authData))
    authorize.close()
    

def callSAPI():
    print '\n--Call SHOEBOXED API for test'
    sapi_url = 'https://api.shoeboxed.com/v2/'    
    headers = {"Authorization": "Bearer " + authData['shoeboxed']['access_token'], "Content-Type":"application/json"}
    r = requests.get(sapi_url+'/accounts/'+authData['shoeboxed']['ID']+'/documents/?', headers=headers)
    #r = json.loads(r.text)
    
    print 'get r:', r

    try:
        'callSAPI error occur: ' + r['error'] + ' : ' + r['error_description']
        return 'error'
    except:
        return r
    '''try:
        #r = r.json()
        try:
            'callSAPI error occur: ' + r['error'] + ' : ' + r['error_description']
            return 'error'
        except:
            return r
    except:
        return 'error'
        '''
    

#shoeboxed auth (one time)
def obtainAccessToken():
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {}
    params['code'] = authData['shoeboxed']['code']
    params['grant_type'] = 'authorization_code'
    params['redirect_uri'] = authData['shoeboxed']['redirect_uri']

    r = requests.post(token_url, headers=headers, params=params, auth=(authData['shoeboxed']['ID'], authData['shoeboxed']['Secret']))
    r = json.loads(r.text)
    return r
    #return r.json()


#shoeboxed auth (all other times)
def refreshAccessToken():
    #print '\nauthData:\n', json.dumps(authData), '\n'
    headers = {'Content-Type':'application/x-www-form-urlencoded'}
    params = {}
    params['refresh_token'] = authData['shoeboxed']['refresh_token'] 
    params['grant_type'] = 'refresh_token'
    params['redirect_uri'] = authData['shoeboxed']['redirect_uri']

    r = requests.post(token_url, headers=headers, params=params, auth=(authData['shoeboxed']['ID'], authData['shoeboxed']['Secret']))
    r = json.loads(r.text)
    return r
    #return r.json()
    

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
    return authorize_url+'?'+urllib.urlencode(params)


# gets the current location of script-file
def getCurrentPath():
    spath = ''
    if len(path.dirname(sys.argv[0])) != 0:
        spath += path.dirname(sys.argv[0]) + path.sep
    return spath


main()
