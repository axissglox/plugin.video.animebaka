#v1 API http://animebaka.tv/api/v1/
#GET /shows
#GET /shows/{id} // Numeric ID of show
#GET /shows/{id}/episode/{float} // Numeric ID of show & episode number (7|22|16.5)
#GET /genres 
#GET /genres/{string} // String name of genre (spaces converted to underscores) (action|shounen_ai|sci-fi)
#GET /type/movies	
#GET /status/{string} // String name of status (ongoing|completed|upcoming)
# TODO: Fix special characters like star display
import sys
import xbmc
import xbmcgui
import xbmcplugin

import json
import re
import HTMLParser
import urllib
import urllib2
import urlparse
from string import ascii_lowercase

import time
from datetime import datetime

addon_handle = int( sys.argv[1] )
    
xbmcplugin.setContent(addon_handle, 'movies')

args = urlparse.parse_qs(sys.argv[2][1:])
mode = args.get('mode', None)
base_url = "http://animebaka.tv"
api_base = "http://animebaka.tv/api/v1/"
bakavideo_base = 'https://bakavideo.tv/view/'

defaultOpts = (
    { 'label': 'Latest Releases', 'href': 'latest', 'mode': 'latest' },
    { 'label': 'All Shows', 'href': 'shows' },
    #{ 'label': 'Currently Airing', 'href': 'status/ongoing' }, #endpoint currently 404
    { 'label': 'Filter by Alphabet', 'href': 'filter' },
    { 'label': 'Genres', 'href': 'genres' },
    #{ 'label': 'Video by Type', 'href': 'types' }, #currently missing endpoint
    { 'label': 'Movies', 'href': 'type/movies' }    
)
	
def addDirectoryItem( urlParams, title, img, isFolder, streamInfo={}, setInfo={} ):
    url = build_url( urlParams )
    try:
        li = xbmcgui.ListItem( fixEncoding( title ), iconImage=img, thumbnailImage=img )
    except: #mirrors will cause an exceptions.UnicodeDecodeError
        li = xbmcgui.ListItem( title, iconImage=img, thumbnailImage=img )

    for key, value in streamInfo.items():
        li.addStreamInfo( key, value )

    for key, value in setInfo.items():
        li.setInfo( key, value )
        
    xbmcplugin.addDirectoryItem( addon_handle, url, li, isFolder )

    return li

def getImgURL( showID ):
    return 'http://images.animebaka.tv/a_lth/' + showID + '_lth.jpg' #large thumb
    
def build_url( query ):
    if 'href' in query:
        query['href'] = fixEncoding( query['href'] )
        
    return sys.argv[0] + '?' + urllib.urlencode( query )
    
def fixEncoding( str ): #YQL turns ' into &#039;, that needs to be undone 
    return HTMLParser.HTMLParser().unescape( str.encode('utf-8') ) 

def getYQLAlias( alias, query={} ):
    req = urllib2.Request( 'http://query.yahooapis.com/v1/public/yql/animebaka_show/animebaka_' + alias + '?format=json&' + urllib.urlencode( query ) )
    reqContent = urllib2.urlopen( req )
    results = json.load( reqContent, 'utf-8' )
    
    links      = []
    if results[ 'query' ][ 'results' ] != None:
        links = results[ 'query' ][ 'results' ][ 'a' ]
        if isinstance( links, list ) is False: #YQL doesn't return an array if only 1 result, make list for list item building
            links = [ links ]
    
    return links
  	
def getAPI( endpoint ):
    req = urllib2.Request( api_base + endpoint )
    reqContent = urllib2.urlopen( req )
    reqJSON = json.load( reqContent, 'utf-8' )
    
    return reqJSON['result']

def play( href ):
    videoLink = getYQLAlias( 'download_video', {'videoHREF': href } )
    xbmc.Player().play( videoLink[0]['href'] ) #scrape the file link on file host and play

def extractStreamInfo( mirror ):
    streamInfo = {}

    if mirror['quality'] == 'HD':
        streamInfo['video'] = { 'width': '1280', 'height': '720' }
    else:
        streamInfo['video'] = { 'width': '640', 'height': '480' }

    subDub = mirror['type']
    if subDub == 'english-subbed':
        streamInfo['subtitle'] = { 'language': 'en' }

    return streamInfo

def listMirrorsAPI( href, title ):
    episode = getAPI( href )
    
    for mirror in episode['mirrors']:
        if mirror['service'] == 'BakaVideo':
            streamInfo = extractStreamInfo( mirror )
            subDub = '[Subbed]'
            
            if streamInfo['subtitle']['language'] != 'en':
                subDub = ''
                
            li = addDirectoryItem( {'mode': 'play', 'href': bakavideo_base + mirror['video_code'] }, title + ' ' + fixEncoding( subDub ), 'DefaultVideo.png', False, streamInfo )
    
    return { 'mirrors': episode['mirrors'], 'li': li }

def getShowInfo( show ):
    video = {}
    
    try:
        fixedSummary = fixEncoding( show['summary'] )
        
    except:
        fixedSummary = '<Summary Unavailable>'
    
    video['plot'] = fixedSummary
    video['plotoutline'] = fixedSummary
    video['title'] = fixEncoding( show['title'] )
        
    dateFormat = "%Y-%m-%d %H:%M:%S"
    
    try:
        video['year'] = datetime(*(time.strptime( show['start_date'], dateFormat)[0:6]) ).year
    except:
        video['year'] = '0000' #error in date time data
    
    if 'parental_rating' in show and show['parental_rating'] != None:
        video['mpaa'] = show['parental_rating']
        
    showInfo = { 'video': video }
    return showInfo

#Start Mode support
if mode is None: #Default View, uses defaultOpts to build menu
    for opt in defaultOpts:
        if 'mode' in opt:
            modeStr = opt['mode']
        else:
            modeStr = 'browse'
        
        if 'api' in opt:
            api = opt['api']
        else:
            api = 'true'
            
        addDirectoryItem( {'mode': modeStr, 'href': opt['href'] }, opt['label'], 'DefaultFolder.png', True )
		
elif mode[0] == 'browse': #Browse links, based on the animebaka.tv menu
    if args['href'][0] == 'genres': #Menu of Genres
        for genre in getAPI( 'genres' ):
            addDirectoryItem( {'mode': 'browse', 'href': 'genre/' + genre['name'] }, genre['name'], 'DefaultFolder.png', True )

    elif args['href'][0] == 'types': #Menu of Video types, from the Type filter
        for type in getYQLAlias( 'types' ):
            if 'content' in type:
                addDirectoryItem( {'mode': 'browse', 'href': type['href'] }, type['content'], 'DefaultFolder.png', True )
	
    elif args['href'][0] == 'filter': #Menu of Alpha filters, does not include the # filter yet
        addDirectoryItem( {'mode':'browse', 'href': 'shows', 'filterAlpha': '[^a-zA-Z].*'}, '#', 'DefaultFolder.png', True ) #add a filter for shows starting without alpha
        for c in ascii_lowercase:
            addDirectoryItem( {'mode': 'browse', 'href': 'shows', 'filterAlpha': '(?i)^' + c }, c.upper(), 'DefaultFolder.png', True )
		
    else:
        if 'filterAlpha' in args: #filter full show results if alpha filter in args
            filterAlpha = args['filterAlpha'][0]
        else:
            filterAlpha = ''
            
        for show in sorted( getAPI( args['href'][0] ), key=lambda k: k['title'].lower() ):
            if re.match( filterAlpha, show['title'] ):
                addDirectoryItem( {'mode': 'list', 'href': 'shows/' + show['id'] }, show['title'], getImgURL( show['id'] ), True, {}, getShowInfo( show ) )
           
	
elif mode[0] == 'latest': #pages of latest results from animebaka.tv front page
    if 'page' in args:
        page = int( args[ 'page' ][0] )
    else:
        page = 1
    
    for episode in getYQLAlias( 'latest', { 'pageHREF': base_url + '/?page=' + str( page ) } ):
        showID = re.findall(r'\d+', episode['img']['src'] )
        episodeID = re.findall( r'\d+', episode['img']['alt'] )
        href = 'shows/' + showID[0] + '/episode/' + episodeID[ len( episodeID ) - 1 ]
        addDirectoryItem( {'mode': 'watch', 'href': href, 'title': fixEncoding( episode['img']['alt'] ) }, episode['img']['alt'], "http:" + episode['img']['src'].replace( 'lcap', 'lth' ), True )
        
    addDirectoryItem( { 'mode': 'latest', 'page': str( page + 1 ) }, 'More', 'DefaultFolder.png', True ) #Add a More link to get more results
     
elif mode[0] == 'list': #List videos linked at the series/movie endpoint
    show = getAPI( args['href'][0] ) 
    
    if len( show['episodes'] ) == 1: #Only one, advance to mirrors
        listMirrorsAPI( 'shows/' + show['id'] + '/episode/1', show['title'] )
        
    else:
        episodes = show['episodes']
        
        for key in sorted( episodes, key=int ):
            if episodes[key] is None:
                title = key + ' - ' + show['title']
                
            else:
                title = key + ' - ' + episodes[key] + ': ' + show['title']

            addDirectoryItem( { 'mode': 'watch', 'href': 'shows/' + show['id'] + '/episode/' + key, 'title': fixEncoding( title ) }, title, 'DefaultFolder.png', True )

elif mode[0] == 'watch': #get available videos from video page
    mirrorsInfo = listMirrorsAPI( args['href'][0], args['title'][0] )
    
    if len( mirrorsInfo['mirrors'] ) == 1: #if only 1, play it
        xbmcplugin.setResolvedUrl( addon_handle, False, mirrorsInfo['li'] )
        play( bakavideo_base + mirrorsInfo['mirrors'][0]['video_code'] )
    #elif len( mirrorsInfo['mirrors'] ) == 0:
        #TODO: no playable mirrors
        
    
elif mode[0] == 'play': #Watch the selected show from list view
    play( args['href'][0] )
	
xbmcplugin.endOfDirectory( addon_handle )
