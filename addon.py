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

addon_handle = int( sys.argv[1] )
    
xbmcplugin.setContent(addon_handle, 'movies')

args = urlparse.parse_qs(sys.argv[2][1:])
mode = args.get('mode', None)
base_url = "http://animebaka.tv"
api_base = "http://animebaka.tv/api/v1"
bakavideo_base = 'https://bakavideo.tv/view/'

defaultOpts = (
    { 'label': 'Latest Releases', 'href': 'latest', 'mode': 'latest' },
    { 'label': 'All Shows', 'href': '/browse/shows' },
    { 'label': 'Currently Airing', 'href': '/browse/status/ongoing' },
    { 'label': 'Filter by Alphabet', 'href': 'filter' },
    { 'label': 'Genres', 'href': 'genres' },
    { 'label': 'Video by Type', 'href': 'types' },
    { 'label': 'Movies', 'href': 'type/movie' }    
)
	
def addDirectoryItem( urlParams, title, img, isFolder, streamInfo={} ):
    url = build_url( urlParams )
    try:
        li = xbmcgui.ListItem( fixEncoding( title ), iconImage=img, thumbnailImage=img )
    except: #mirrors will cause an exceptions.UnicodeDecodeError
        li = xbmcgui.ListItem( title, iconImage=img, thumbnailImage=img )

    print( streamInfo )
    for key, value in streamInfo.items():
        li.addStreamInfo( key, value )

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
    
    return reqJSON.result

def play( href ):
    #Determine the Download page URL
    videoHREF = getYQLAlias( 'download_link', {'videoHREF': base_url + href } )[0]['href'] #scrape the download link from player foot area
    print( videoHREF )
    xbmc.Player().play( getYQLAlias( 'download_video', {'videoHREF': videoHREF } )[0]['href'] ) #scrape the file link on file host and play

def extractStreamInfo( mirror ):
    streamInfo = {}

    if mirror['span'][0]['em'] == 'HD':
        streamInfo['video'] = { 'width': '1280', 'height': '720' }
    else:
        streamInfo['video'] = { 'width': '640', 'height': '480' }

    subDub = mirror['span'][ len( mirror['span'] ) - 1 ]['content']
    if subDub == '[Subbed]':
        streamInfo['subtitle'] = { 'language': 'en' }

    return streamInfo

def listMirrors( href, title ):
    mirrors = getYQLAlias( 'video_mirrors', {'videoHREF': base_url + href } )

    for mirror in getYQLAlias( 'video_mirrors', {'videoHREF': base_url + href } ):
        streamInfo = extractStreamInfo( mirror )
        subDub = mirror['span'][ len( mirror['span'] ) - 1 ]['content']

        li = addDirectoryItem( {'mode': 'play', 'href': mirror['href'] }, title + ' ' + fixEncoding( subDub ), 'DefaultVideo.png', False, streamInfo )

    return { 'mirrors': mirrors, 'li': li }

#Start Mode support
if mode is None: #Default View, uses defaultOpts to build menu
    for opt in defaultOpts:
        if 'mode' in opt:
            modeStr = opt['mode']
        else:
            modeStr = 'browse'
        
        addDirectoryItem( {'mode': modeStr, 'href': opt['href'] }, opt['label'], 'DefaultFolder.png', True )
		
elif mode[0] == 'browse': #Browse links, based on the animebaka.tv menu
    if args['href'][0] == 'genres': #Menu of Genres
        for genre in getAPI( 'genres' ):
            addDirectoryItem( {'mode': 'browse', 'href': 'genres/' + genre['name'], 'api': 'true' }, genre['name'], 'DefaultFolder.png', True )

    elif args['href'][0] == 'types': #Menu of Video types, from the Type filter
        for type in getYQLAlias( 'types' ):
            if 'content' in type:
                addDirectoryItem( {'mode': 'browse', 'href': type['href'] }, type['content'], 'DefaultFolder.png', True )
	
    elif args['href'][0] == 'filter': #Menu of Alpha filters, does not include the # filter yet
        addDirectoryItem( {'mode':'browse', 'href': 'shows', 'filterAlpha': '[^a-zA-Z].*', 'api': 'true'}, '#', 'DefaultFolder.png', True ) #add a filter for shows starting without alpha
        for c in ascii_lowercase:
            addDirectoryItem( {'mode': 'browse', 'href': 'shows', 'filterAlpha': c, 'api': 'true' }, c.upper(), 'DefaultFolder.png', True )
		
    else:
        if 'filterAlpha' in args: #run a different YQL if alpha filtering
            filterAlpha = args['filterAlpha'][0]
        else:
            filterAlpha = ''
        
        if args['api'][0] == 'true':
            for show in getAPI( args['href'][0] ):
                if re.match( filterAlpha, show['title'] ):
                    addDirectoryItem( {'mode': 'list', 'href': 'shows/' + show['id'] }, show['title'], getImgURL( show['id'] ), True )
        else:
            for show in getYQLAlias( 'browse', {'showsHREF': base_url + args['href'][0] }):
                if re.match( '/anime/' + filterAlpha, show['href'] ):
                    addDirectoryItem( {'mode': 'list', 'href': show['href'] }, show['span']['content'], getImgURL( show['data-show-id'] ), True )
	
elif mode[0] == 'latest': #pages of latest results from animebaka.tv front page
    if 'page' in args:
        page = int( args[ 'page' ][0] )
    else:
        page = 1
    
    for episode in getYQLAlias( 'latest', { 'pageHREF': base_url + '/?page=' + str( page ) } ):
        addDirectoryItem( {'mode': 'watch', 'href': episode['href'], 'title': fixEncoding( episode['img']['alt'] ) }, episode['img']['alt'], "http:" + episode['img']['src'].replace( 'lcap', 'lth' ), True )
        
    addDirectoryItem( { 'mode': 'latest', 'page': str( page + 1 ) }, 'More', 'DefaultFolder.png', True ) #Add a More link to get more results
     
elif mode[0] == 'list': #List videos linked at the series/movie endpoint
    show = getAPI( args['href'][0] ).result #getYQLAlias( 'list', {'showHREF':  base_url + args['href'][0]} )

    if len( episodes ) == 1: #Only one, advance to mirrors
        listMirrors( fixEncoding( episodes[0]['href'] ), episodes[0]['span']['content'] )
        
    else:
        for key, value in show.episodes:
            if value != null:
                title = key + ' - ' + value
            else:
                title = key + ' - ' + show['title']

            li = addDirectoryItem( { 'mode': 'watch', 'href': 'shows/' + show['id'] + '/episode/' + key, 'title': fixEncoding( title ) }, title, 'DefaultFolder.png', True )

elif mode[0] == 'watch': #get available videos from video page
    episode = getAPI( args['href'] ) #listMirrors( args['href'][0], args['title'][0] )

    if len( episode['mirrors'] ) == 1: #if only 1, play it
        xbmcplugin.setResolvedUrl( addon_handle, False, bakavideo_base + episode['mirrors'][0]['video_code'] )
        play( bakavideo_base + episode['mirrors'][0]['video_code'] )

    else:
        for mirror in episode['mirrors']:
            if mirror['service'] == 'BakaVideo':
                addDirectoryItem( {'mode': 'play', 'href': })
                
elif mode[0] == 'play': #Watch the selected show from list view
    play( args['href'][0] )
	
xbmcplugin.endOfDirectory( addon_handle )
