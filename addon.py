# TODO: Include a # filter in the Anime by Alphabet
#		Refactor href in a lot of places. It's really an endpoint string
#		A lot of the menu building feels like it could be simplified more
#		Should I use a class for something so small?
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
    { 'label': 'Filter by Alphabet', 'href': 'filter' },
    { 'label': 'Currently Airing', 'href': 'status/ongoing' },
    { 'label': 'Genres', 'href': 'genres' },
    { 'label': 'Video by Type', 'href': 'types' },
    { 'label': 'Movies', 'href': 'type/movie' },
    { 'label': 'All Shows', 'href': 'shows' }
)

def toList( data ):
    theList = data
    
    if isinstance( data, list ) is False: #only turn into a list if it's not
    	theList = [ data ]
    	
    return theList 
	
def escapeSingleQuote( str ): #YQL turns ' into &#039;, that needs to be undone
    return str.replace( "&#039;", "\'" ) 
    
def YQL( url, xpath ): # run a query against YQL, returns a content JSON
    req = urllib2.Request( 'http://query.yahooapis.com/v1/public/yql?format=json&q=select%20*%20from%20html%20where%20url=%22' + url  + '%22%20and%20xpath=%27' + xpath + '%27' )
    reqContent = urllib2.urlopen( req )
    
    return json.load( reqContent, 'utf-8' )
	
def buildBrowseMenu( collection ): #Builds a menu of shows based on the specified collection
    if 'filterAlpha' in args: #run a different YQL if alpha filtering
        showsJSON = YQL( 'http://animebaka.tv/browse/' + collection, '//a[contains(@class,%22show%22)][contains(@href,%22/anime/' + args['filterAlpha'][0] + '%22)]' )
    else:
        showsJSON = YQL( 'http://animebaka.tv/browse/' + collection, '//a[contains(@class,%22show%22)]' )
    
    if showsJSON[ 'query' ][ 'results' ] != None:
    	showsA = toList( showsJSON[ 'query' ][ 'results' ][ 'a' ] ) #YQL doesn't return an array if only 1 result, make sure it's a list object
    	
    	for show in showsA:
            url = sys.argv[0] + "?mode=list&href=" + escapeSingleQuote( show['href'] )         
            li = xbmcgui.ListItem( escapeSingleQuote( show['span']['content'] ), iconImage='http://images.animebaka.tv/a_lth/' + show['data-show-id'] + '_lth.jpg' )
            xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
		
def buildGenresMenu(): #Menu of Genres
    genresJSON = YQL( 'http://animebaka.tv/browse/genres', '//a[contains(@href,%22/browse/genre%22)][contains(@class,%22btn%22)]' )
    genresA = genresJSON[ 'query' ][ 'results' ][ 'a' ]
    
    for genre in genresA:
        label = genre['content'].replace( ' Shows', '')
        url = sys.argv[0] + '?mode=browse&href=' + genre['href'].replace( '/browse/', '' )
        li  = xbmcgui.ListItem( label, iconImage='DefaultFolder.png' )
        xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
			
def buildTypesMenu(): #Menu of Video types, from the Type filter
    typesJSON = YQL( 'http://animebaka.tv/browse/shows', '//a[contains(@href,%22/browse/type/%22)]' )
    if typesJSON[ 'query' ][ 'results' ] != None:
        typesA = typesJSON[ 'query' ][ 'results' ][ 'a' ]
        
        for type in typesA:
            if 'content' in type:
                label = type['content']
                    
                url = sys.argv[0] + '?mode=browse&href=' + type['href'].replace( '/browse/', '' )
                li  = xbmcgui.ListItem( label, iconImage='DefaultFolder.png' )
                xbmcplugin.addDirectoryItem( addon_handle, url, li, True )

def buildAlphaMenu(): #Menu of Alpha filters, does not include the # filter yet
	for c in ascii_lowercase:
		url = sys.argv[0] + '?mode=browse&filterAlpha=' + c + '&href=shows'
		li  = xbmcgui.ListItem( c.upper(), iconImage='DefaultFolder.png' )
		xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
		
if mode is None: #Default View, uses defaultOpts to build menu
    for opt in defaultOpts:
        if 'mode' in opt:
            modeStr = opt['mode']

        else:
            modeStr = 'browse'
        
        url = sys.argv[0] + '?mode=' + modeStr + '&href=' + opt['href']
        li  = xbmcgui.ListItem( opt['label'], iconImage='DefaultFolder.png' )
        xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
		
elif mode[0] == 'browse': #Browse links, based on the animebaka.tv menu
    if args['href'][0] == 'genres':
        buildGenresMenu()

    elif args['href'][0] == 'types':
        buildTypesMenu()
	
    elif args['href'][0] == 'filter':
        buildAlphaMenu();
		
    else:
        buildBrowseMenu( args['href'][0] )
	
elif mode[0] == 'latest': #pages of latest results from animebaka.tv front page
    if 'page' in args:
        page = int( args[ 'page' ][0] )
    else:
        page = 1
    
    episodesJSON = YQL( 'http://animebaka.tv/?page=' + str( page ), '//div[contains(@class,"release-wrapper")]/a[contains(@class,"poster")]' )
    
    if episodesJSON[ 'query' ][ 'results' ] != None:
        episodesA = toList( episodesJSON[ 'query' ][ 'results' ][ 'a' ] )
        
        for episode in episodesA:
            #JSON varies a bit from series listing of episodes, so cannot exactly resuse
            url = sys.argv[0] + '?mode=watch&href=' + urllib.quote( escapeSingleQuote( episode['href'].encode('utf-8') ) ) #fix href with % urlencodes
            
            img = episode['img']
            li  = xbmcgui.ListItem( img['alt'], iconImage="http:" + img[ 'src' ].replace( 'lcap', 'lth' ) ) #use the big thumb, also src lacks http:
            xbmcplugin.addDirectoryItem( addon_handle, url, li )
            
        #Add a More link to get more results
        page += 1
        url = sys.argv[0] + '?mode=latest&page=' + str( page )
        li = xbmcgui.ListItem( 'More', iconImage='DefaultFolder.png' )
        xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
     
elif mode[0] == 'list': #List Episode list for an Anime
    href = args['href'][0]
    
    #Having problems with URLs that have a + in them. Though they end up as whitespaces for some wierd reason. Hacky replacement with a %2B
    episodesJSON = YQL( 'http://animebaka.tv/' + href.replace( " ", "%2B" ), '//td[contains(@class,%22episode%22)]/a' )
    
    if episodesJSON[ 'query' ][ 'results' ] != None:
        episodesA = toList( episodesJSON[ 'query' ][ 'results' ][ 'a' ] )
  
        for episode in episodesA:
            url = sys.argv[0] + '?mode=watch&href=' + urllib.quote( escapeSingleQuote( episode['href'].encode('utf-8') ) ) #fix href with % urlencodes
            
            if isinstance( episode['span'], list ) is True:
                title = escapeSingleQuote( episode['span'][0]['content'] ) + ' - ' + episode['span'][1]['content']
            else:
                title = escapeSingleQuote( episode['span']['content'] )
			
            li  = xbmcgui.ListItem( title, iconImage='DefaultVideo.png')
            xbmcplugin.addDirectoryItem( addon_handle, url, li )
		
elif mode[0] == 'watch': #Watch the selected show from list view
    #Determine the Download page URL
    href = args['href'][0]
    watchDLJSON = YQL( 'http://animebaka.tv' + href.encode('utf-8'), '//a[contains(@class,%22download%22)]' )
    watchDLURL = watchDLJSON['query']['results']['a']['href']
    
    #Extract the direct download link URL from Download page, then play that URL
    dlJSON = YQL( watchDLURL.encode('utf-8'), '//a[contains(@id,%22download%22)]' )
    url = dlJSON['query']['results']['a']['href']
    xbmc.Player().play( url )
	
xbmcplugin.endOfDirectory( addon_handle )