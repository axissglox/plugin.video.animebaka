# TODO: Include a # filter in the Anime by Alphabet
#		Refactor href in a lot of places. It's really an endpoint string
import sys
import xbmc
import xbmcgui
import xbmcplugin

import json
import urllib
import urllib2
import urlparse
from string import ascii_lowercase

addon_handle = int( sys.argv[1] )
    
xbmcplugin.setContent(addon_handle, 'movies')

args = urlparse.parse_qs(sys.argv[2][1:])
mode = args.get('mode', None)
base_url = "http://animebaka.tv"

defaultOpts = (
    { 'label': 'Latest Releases', 'href': 'latest', 'mode': 'latest' },
    { 'label': 'All Shows', 'href': '/browse/shows' },
    { 'label': 'Currently Airing', 'href': '/browse/status/ongoing' },
    { 'label': 'Filter by Alphabet', 'href': 'filter' },
    { 'label': 'Genres', 'href': 'genres' },
    { 'label': 'Video by Type', 'href': 'types' },
    { 'label': 'Movies', 'href': '/browse/type/movie' }    
)

def toList( data ):
    theList = data
    
    if isinstance( data, list ) is False: #only turn into a list if it's not
    	theList = [ data ]
    	
    return theList 
	
def addDirectoryItem( urlParams, title, img, isFolder ):
    url = build_url( urlParams )
    li = xbmcgui.ListItem( title, iconImage=img, thumbnailImage=img )
    xbmcplugin.addDirectoryItem( addon_handle, url, li, isFolder )

def getImgURL( showID ):
    return 'http://images.animebaka.tv/a_lth/' + showID + '_lth.jpg' #large thumb
    
def build_url( query ):
    return sys.argv[0] + '?' + urllib.urlencode( query )
    
def fixEncoding( str ): #YQL turns ' into &#039;, that needs to be undone
    return str.encode('utf-8').replace( "&#039;", "\'" ) 
    
def fixHREF( str ):
    return urllib.quote( fixEncoding( str ) )

def YQL_Links( endpoint, xpath ):
    json    = YQL( endpoint, xpath )
    As      = []
    
    if json[ 'query' ][ 'results' ] != None:
        As = toList( json[ 'query' ][ 'results' ][ 'a' ] ) #YQL doesn't return an array if only 1 result, make list for list item building 
    
    return As

def YQL( endpoint, xpath ): #shorthand version that prepends base_url
    return YQL_fullURL( base_url + endpoint, xpath )
       
def YQL_fullURL( url, xpath ): # run a query against YQL, returns a content JSON
    req = urllib2.Request( 'http://query.yahooapis.com/v1/public/yql?format=json&q=select%20*%20from%20html%20where%20url=%22' + url + '%22%20and%20xpath=%27' + xpath + '%27' )
    reqContent = urllib2.urlopen( req )
    
    return json.load( reqContent, 'utf-8' )
	
def buildBrowseMenu( endpoint ): #Builds a menu of shows based on the specified collection
    if 'filterAlpha' in args: #run a different YQL if alpha filtering
        xpath = '//a[contains(@class,%22show%22)][contains(@href,%22/anime/' + args['filterAlpha'][0] + '%22)]'
    else:
        xpath = '//a[contains(@class,%22show%22)]'

    for show in YQL_Links( endpoint, xpath ):
        addDirectoryItem( {'mode': 'list', 'href': fixEncoding( show['href'] ) }, show['span']['content'], getImgURL( show['data-show-id'] ), True )
		
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
        for genre in YQL_Links( '/browse/genres', '//a[contains(@href,%22/browse/genre%22)][contains(@class,%22btn%22)]' ):
            addDirectoryItem( {'mode': 'browse', 'href': fixEncoding( genre['href'] )}, genre['content'].replace( ' Shows', ''), 'DefaultFolder.png', True )

    elif args['href'][0] == 'types': #Menu of Video types, from the Type filter
        for type in YQL_Links( '/browse/shows', '//a[contains(@href,%22/browse/type/%22)]' ):
            if 'content' in type:
                addDirectoryItem( {'mode': 'browse', 'href': fixEncoding( type['href'] ) }, type['content'], 'DefaultFolder.png', True )
	
    elif args['href'][0] == 'filter': #Menu of Alpha filters, does not include the # filter yet
        for c in ascii_lowercase:
            addDirectoryItem( {'mode': 'browse', 'href': '/browse/shows', 'filterAlpha': c }, c.upper(), 'DefaultFolder.png', True )
		
    else:
        buildBrowseMenu( args['href'][0] )
	
elif mode[0] == 'latest': #pages of latest results from animebaka.tv front page
    if 'page' in args:
        page = int( args[ 'page' ][0] )
    else:
        page = 1
    
    for episode in YQL_Links( '/?page=' + str( page ), '//div[contains(@class,"release-wrapper")]/a[contains(@class,"poster")]' ):
        #JSON varies a bit from series listing of episodes, so cannot exactly resuse
        addDirectoryItem( {'mode': 'watch', 'href': fixHREF( episode['href'] ) }, episode['img']['alt'], "http:" + episode['img']['src'].replace( 'lcap', 'lth' ), False )
        
    #Add a More link to get more results
    page += 1
    addDirectoryItem( { 'mode': 'latest', 'page': str( page ) }, 'More', 'DefaultFolder.png', True )
     
elif mode[0] == 'list': #List videos linked at the series/movie endpoint
    href = fixHREF( args['href'][0] )
    
    #Having problems with URLs that have a + in them. Though they end up as whitespaces for some wierd reason. Hacky replacement with a %2B
    for episode in YQL_Links( href , '//td[contains(@class,%22episode%22)]/a' ):
        if isinstance( episode['span'], list ) is True:
            addDirectoryItem( { 'mode': 'watch', 'href': fixHREF( episode['href'] ) }, episode['span'][0]['content'] + ' - ' + episode['span'][1]['content'], 'DefaultVideo.png', False )
        else:
            addDirectoryItem( { 'mode': 'watch', 'href': fixHREF( episode['href'] ) }, episode['span']['content'], 'DefaultVideo.png', False )
		
elif mode[0] == 'watch': #Watch the selected show from list view
    #Determine the Download page URL
    href = args['href'][0]
    watchDLJSON = YQL( href, '//a[contains(@class,%22download%22)]' ) #scrape the download link from player foot area
    watchDLURL = watchDLJSON['query']['results']['a']['href']
    
    #Extract the direct download link URL from Download page, then play that URL
    dlJSON = YQL_fullURL( watchDLURL.encode('utf-8'), '//a[contains(@id,%22download%22)]' ) #scrape the file link on file host
    url = dlJSON['query']['results']['a']['href']
    xbmc.Player().play( url )
	
xbmcplugin.endOfDirectory( addon_handle )