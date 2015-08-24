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
	
def build_url( query ):
    return sys.argv[0] + '?' + urllib.urlencode( query )
    
def fixEncoding( str ): #YQL turns ' into &#039;, that needs to be undone
    return str.encode('utf-8').replace( "&#039;", "\'" ) 
    
def fixHREF( str ):
    return urllib.quote( fixEncoding( str ) )
    
def YQL( url, xpath ): # run a query against YQL, returns a content JSON
    req = urllib2.Request( 'http://query.yahooapis.com/v1/public/yql?format=json&q=select%20*%20from%20html%20where%20url=%22' + url  + '%22%20and%20xpath=%27' + xpath + '%27' )
    reqContent = urllib2.urlopen( req )
    
    return json.load( reqContent, 'utf-8' )
	
def buildBrowseMenu( endpoint ): #Builds a menu of shows based on the specified collection
    if 'filterAlpha' in args: #run a different YQL if alpha filtering
        showsJSON = YQL( base_url + endpoint, '//a[contains(@class,%22show%22)][contains(@href,%22/anime/' + args['filterAlpha'][0] + '%22)]' )
    else:
        showsJSON = YQL( base_url + endpoint, '//a[contains(@class,%22show%22)]' )
    
    if showsJSON[ 'query' ][ 'results' ] != None:
    	showsA = toList( showsJSON[ 'query' ][ 'results' ][ 'a' ] ) #YQL doesn't return an array if only 1 result, make list for list item building
    	
    	for show in showsA:
            url = build_url( {'mode': 'list', 'href': fixEncoding( show['href'] ) } )
            img = 'http://images.animebaka.tv/a_lth/' + show['data-show-id'] + '_lth.jpg'
            li = xbmcgui.ListItem( show['span']['content'], iconImage=img, thumbnailImage=img )
            xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
		
def buildGenresMenu(): #Menu of Genres
    genresJSON = YQL( 'http://animebaka.tv/browse/genres', '//a[contains(@href,%22/browse/genre%22)][contains(@class,%22btn%22)]' )
    genresA = genresJSON[ 'query' ][ 'results' ][ 'a' ]
    
    for genre in genresA:
        label = genre['content'].replace( ' Shows', '')
        url = build_url( {'mode': 'browse', 'href': fixEncoding( genre['href'] )} )
        li  = xbmcgui.ListItem( label, iconImage='DefaultFolder.png' )
        xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
			
def buildTypesMenu(): #Menu of Video types, from the Type filter
    typesJSON = YQL( 'http://animebaka.tv/browse/shows', '//a[contains(@href,%22/browse/type/%22)]' )
    if typesJSON[ 'query' ][ 'results' ] != None:
        typesA = typesJSON[ 'query' ][ 'results' ][ 'a' ]
        
        for type in typesA:
            if 'content' in type:
                label = type['content']
                    
                url = build_url( {'mode': 'browse', 'href': fixEncoding( type['href'] ) } ) 
                li  = xbmcgui.ListItem( label, iconImage='DefaultFolder.png' )
                xbmcplugin.addDirectoryItem( addon_handle, url, li, True )

def buildAlphaMenu(): #Menu of Alpha filters, does not include the # filter yet
	for c in ascii_lowercase:
		url = build_url( {'mode': 'browse', 'href': '/browse/shows', 'filterAlpha': c } )
		li  = xbmcgui.ListItem( c.upper(), iconImage='DefaultFolder.png' )
		xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
		
#Start Mode support
if mode is None: #Default View, uses defaultOpts to build menu
    for opt in defaultOpts:
        if 'mode' in opt:
            modeStr = opt['mode']

        else:
            modeStr = 'browse'
        
        url = build_url( {'mode': modeStr, 'href': opt['href'] } ) 
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
            url = build_url( {'mode': 'watch', 'href': fixHREF( episode['href'] ) } ) 
            
            img = "http:" + episode['img']['src'].replace( 'lcap', 'lth' )#use the big thumb, also src lacks http:
            li  = xbmcgui.ListItem( img['alt'], iconImage=img, thumbnailImage=img ) 
            xbmcplugin.addDirectoryItem( addon_handle, url, li )
            
        #Add a More link to get more results
        page += 1
        url = build_url( { 'mode': 'latest', 'page': str( page ) } ) 
        li = xbmcgui.ListItem( 'More', iconImage='DefaultFolder.png' )
        xbmcplugin.addDirectoryItem( addon_handle, url, li, True )
     
elif mode[0] == 'list': #List videos linked at the series/movie endpoint
    href = fixHREF( args['href'][0] )
    
    #Having problems with URLs that have a + in them. Though they end up as whitespaces for some wierd reason. Hacky replacement with a %2B
    episodesJSON = YQL( base_url + href , '//td[contains(@class,%22episode%22)]/a' )
    
    if episodesJSON[ 'query' ][ 'results' ] != None:
        episodesA = toList( episodesJSON[ 'query' ][ 'results' ][ 'a' ] ) #make sure it's a list, YQL makes single results an object
  
        for episode in episodesA:
            url = build_url( { 'mode': 'watch', 'href': fixHREF( episode['href'] ) } ) 
            
            if isinstance( episode['span'], list ) is True:
                title = episode['span'][0]['content'] + ' - ' + episode['span'][1]['content']
            else:
                title = episode['span']['content']
			
            li  = xbmcgui.ListItem( title, iconImage='DefaultVideo.png')
            xbmcplugin.addDirectoryItem( addon_handle, url, li )
		
elif mode[0] == 'watch': #Watch the selected show from list view
    #Determine the Download page URL
    href = args['href'][0]
    print( href )
    watchDLJSON = YQL( base_url + href, '//a[contains(@class,%22download%22)]' ) #scrape the download link from player foot area
    watchDLURL = watchDLJSON['query']['results']['a']['href']
    
    #Extract the direct download link URL from Download page, then play that URL
    dlJSON = YQL( watchDLURL.encode('utf-8'), '//a[contains(@id,%22download%22)]' ) #scrape the file link on file host
    url = dlJSON['query']['results']['a']['href']
    xbmc.Player().play( url )
	
xbmcplugin.endOfDirectory( addon_handle )