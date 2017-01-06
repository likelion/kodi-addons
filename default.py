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
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import re
import os
from time import strftime, time, localtime

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

#xbmc.log("ARGV = "+str(sys.argv))

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
    doc = api_call(sid, 'channel_list', show='all', protect_code=get_setting('protect'))
    for group in doc.get('groups'):
        for channel in group.get('channels'):
            if channel.get('is_video') == 1:
                li = xbmcgui.ListItem()
                label = '[COLOR white]' + channel.get('name') + '[/COLOR]'
                arch = channel.get('have_archive')
                if arch == 1:
                    label = '[COLOR red]' + u'\u2022' + '[/COLOR] ' + label
                    url = get_url(action='epg', cid=channel.get('id'), sid=sid)
                    li.addContextMenuItems([('EPG and Archive','XBMC.Container.Update(%s)'%url)])
                else:
                    label = '[COLOR gray]' + u'\u2022' + '[/COLOR] ' + label
                if 'epg_progname' in channel:
                    progname = channel.get('epg_progname').splitlines()
                    label += ' - ' + progname[0]
                    info = {'title': progname[0]}
                    if len(progname) > 1:
                        info['plot'] = ' '.join(progname[1:])
                    if 'epg_start' in channel and 'epg_end' in channel:
                        info['duration'] = channel.get('epg_end') - channel.get('epg_start')
                    li.setInfo('video', info)
                li.setLabel(label)
                li.setArt({'thumb': channel.get('icon_link')})
                url = get_url(action='play', cid=channel.get('id'), sid=sid, arch=arch, gmt='-1')
                xbmcplugin.addDirectoryItem(_handle, url, li, True)
    xbmc.executebuiltin('Container.SetViewMode(51)')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=True)

def list_epg(sid, cid):
    doc = api_call(sid, 'epg', cid=cid, day=strftime("%d%m%y", localtime(time())))
    st = int(doc.get('servertime'))
    for epg in doc.get('epg'):
        ut_start = int(epg.get('ut_start'))
        progname = epg.get('progname').splitlines();
        label = '[COLOR cyan]['+strftime("%H:%M", localtime(ut_start))+'][/COLOR] - '+progname[0]
        if st > ut_start:
            label = '[COLOR white]' + label + '[/COLOR]'
        else:
            label = '[I]' + label + '[/I]'
        li = xbmcgui.ListItem(label=label)
        info = {'title': progname[0]}
        if len(progname) > 1:
            info['plot'] = ' '.join(progname[1:])
        li.setInfo('video', info)
        url = get_url(action='play', cid=cid, sid=sid, arch=1, gmt=ut_start)
        xbmcplugin.addDirectoryItem(_handle, url, li, False)
    xbmc.executebuiltin('Container.SetViewMode(51)')
    xbmcplugin.endOfDirectory(_handle)

class MyMonitor(xbmc.Monitor):

    def __init__ (self):
        xbmc.Monitor.__init__(self)

    def onAbortRequested(self):
        global closescript
        closescript = True


class MyPlayer(xbmc.Player):

    def __init__ (self, sid, cid, arch, gmt):
        xbmc.Player.__init__(self)
        self.sid = sid
        self.cid = cid
        self.arch = arch
        self.gmt = int(gmt)
        self.max = -1
        self.min = -1

    def play_channel(self):
        #xbmc.log('sid='+self.sid+' cid='+str(self.cid))
        #xbmc.log('--------- playing from '+str(self.gmt))
        if self.gmt ==  -1:
            doc = api_call(self.sid, 'get_url', cid=self.cid, protect_code=get_setting('protect'))
        else:
            doc = api_call(self.sid, 'get_url', cid=self.cid, gmt=self.gmt, protect_code=get_setting('protect'))
        url = doc.get('url')
        url = re.sub('http/ts(.*?)\s(.*)', 'http\\1', url)
        s = strftime("%d %b %H:%M:%S", localtime(self.gmt))
        i = strftime("%d %b %H:%M:%S", localtime(self.min))
        li = xbmcgui.ListItem(s + ' [' + i + ']')
        #li.addStreamInfo('video', {'width':331, 'duration': 1801})
        self.play(url, li)

    def onPlayBackStopped(self):
        global closescript
        closescript = True
        #xbmc.log("stopped!!!!!!")

    def onPlayBackSeek(self, time, seekOffset):
        if self.arch == '1' and not (self.gmt == -1 and seekOffset >= 0):
            self.pause()
            doc = api_call(self.sid, 'settings', var='stream_standard')
            catchup = doc.get('settings').get('list')[0].get('catchup') 
            self.max = int(doc.get('servertime')) - catchup.get('delay')
            self.min = self.max - catchup.get('length')
            if self.gmt == -1:
                self.gmt = self.max
            self.gmt = self.gmt + int(self.getTime()) + int(seekOffset/1000)
            if self.gmt < self.min:
                self.gmt = self.min
            elif self.gmt > self.max:
                self.gmt = -1
            #xbmc.log('--------- seeking '+str(int(seekOffset/1000))+' to '+str(self.gmt))
            self.play_channel()

closescript = False

def play_video(sid, cid, arch, gmt):
    monitor = MyMonitor()
    player = MyPlayer(sid=sid, cid=cid, arch=arch, gmt=gmt)
    player.play_channel()
    while not ( closescript ):
        xbmc.sleep(500)
    #xbmc.log('aborted!!!!!')

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
        #xbmc.log('in params: '+sid)
        if params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(sid, params['cid'], params['arch'], params['gmt'])
        elif params['action'] == 'epg':
            list_epg(sid, params['cid'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        sid = get_sid()
        #xbmc.log('new: '+sid)
        list_channels(sid)

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])