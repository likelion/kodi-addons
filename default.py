# -*- coding: utf-8 -*-
# Module: default
# Author: Leonid Mokrushin
# Created on: 03.01.2017
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib import urlencode
from urlparse import parse_qsl
import urllib2
import json
import xbmcaddon
import xbmcgui
import xbmcplugin

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

_api = 'https://iptv.kartina.tv/api/json/'

def get_setting(setting):
    return xbmcaddon.Addon().getSetting(setting)

def get_sid():
    url = _api+'login?'+'login='+get_setting('username')+'&pass='+get_setting('password')
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    body = res.read()
    sid = json.loads(body).get('sid')
    res.close()
    return sid

def api_call(sid, method, **kwargs):
    url = '{0}?{1}'.format(_api+method, urlencode(kwargs))
    xbmc.log('URL = '+url)
    req = urllib2.Request(url)
    req.add_header('Cookie', 'MW_SSID='+sid)
    res = urllib2.urlopen(req)
    body = res.read()
    doc = json.loads(body)
    res.close()
    return doc

def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.
    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def list_channels(sid):
    doc = api_call(sid, 'channel_list', show='all', protect_code=get_setting('password'))
    for group in doc.get('groups'):
        for channel in group.get('channels'):
            list_item = xbmcgui.ListItem(label=channel.get('name'))
            list_item.setArt({'thumb': channel.get('icon_link')})
            url = get_url(action='listing', sid=sid)
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle)

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['sid']:
            sid = params['sid']
        else:
            sid = get_sid()
        xbmc.log('in params: '+sid)
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            #list_videos(params['category'])
            list_channels(sid)
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        sid = get_sid()
        xbmc.log('new: '+sid)
        list_channels(sid)

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])