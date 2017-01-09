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
import time
import datetime

_url = sys.argv[0]
_handle = int(sys.argv[1])
_api = 'https://iptv.kartina.tv/api/json/'

def get_setting(setting):
    return xbmcaddon.Addon().getSetting(setting)

def get_sid():
    url = '%slogin?login=%s&pass=%s'%(_api, get_setting('username'), get_setting('password'))
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    body = res.read()
    sid = json.loads(body).get('sid')
    res.close()
    return sid

def api_call(sid, method, **kwargs):
    url = '%s%s?%s'%(_api, method, urlencode(kwargs))
    xbmc.log('URL = '+url)
    req = urllib2.Request(url)
    req.add_header('Cookie', 'MW_SSID=%s'%sid)
    res = urllib2.urlopen(req)
    body = res.read()
    doc = json.loads(body)
    res.close()
    return doc

def get_url(**kwargs):
    return '%s?%s'%(_url, urlencode(kwargs))

def list_channels(sid):
    doc = api_call(sid, 'channel_list', show='all', protect_code=get_setting('protect'))
    for group in doc.get('groups'):
        for channel in group.get('channels'):
            if channel.get('is_video') == 1:
                li = xbmcgui.ListItem()
                arch = channel.get('have_archive')
                if arch == 1:
                    rec = '[COLOR red]%s[/COLOR]'%u'\u2022'
                    url = get_url(action='epg', cid=channel.get('id'), sid=sid, date=time.time())
                    li.addContextMenuItems([('Archive','XBMC.Container.Update(%s)'%url)], replaceItems=True)
                else:
                    rec = '[COLOR gray]%s[/COLOR]'%u'\u2022'
                start = ' [B]--------[/B]  '
                program = ''
                if 'epg_progname' in channel:
                    progname = channel.get('epg_progname').splitlines()
                    program = ' - ' + progname[0]
                    info = {'title': progname[0]}
                    if len(progname) > 1:
                        info['plot'] = ' '.join(progname[1:])
                    if 'epg_start' in channel and 'epg_end' in channel:
                        start = '[[B]%s[/B]] '%datetime.datetime.fromtimestamp(channel.get('epg_start')).strftime("%H:%M")
                        info['duration'] = channel.get('epg_end') - channel.get('epg_start')
                    li.setInfo('video', info)
                color = group.get('color')[1:]
                if color == 'ilver':
                    color = 'efaf80'
                color = 'ff%s'%color
                li.setLabel('%s [COLOR white]%s[/COLOR][COLOR %s][B]%s[/B][/COLOR]%s'%(rec, start, color, channel.get('name'), program))
                li.setArt({'thumb': channel.get('icon_link')})
                li.setProperty('isPlayable', 'false')
                li.addStreamInfo('video', { 'codec':'h264' })
                url = get_url(action='play', cid=channel.get('id'), sid=sid, arch=arch, gmt='-1')
                xbmcplugin.addDirectoryItem(_handle, url, li, False)
    xbmc.executebuiltin('Container.SetViewMode(51)')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=True)

def list_epg(sid, cid, date):
    epg_min, epg_max = get_min_max(sid)
    day = datetime.datetime.fromtimestamp(float(date))
    if datetime.datetime.fromtimestamp(epg_min) < day.replace(hour=0, minute=0, second=0):
        day_before = day - datetime.timedelta(days=1) 
        li = xbmcgui.ListItem(label=day_before.strftime("%A, %d %B"))
        url = get_url(action='epg', cid=cid, sid=sid, date=day_before.strftime('%s'))
        xbmcplugin.addDirectoryItem(_handle, url, li, True)
    doc = api_call(sid, 'epg', cid=cid, day=day.strftime("%d%m%y"))
    st = int(doc.get('servertime'))
    index = 0
    found_index = False
    for epg in doc.get('epg'):
        ut_start = int(epg.get('ut_start'))
        progname = epg.get('progname').splitlines();
        label = '[COLOR white][[B]%s[/B]][/COLOR] - %s'%(time.strftime("%H:%M", time.localtime(ut_start)), progname[0])
        li = xbmcgui.ListItem()
        li.addStreamInfo('video', { 'codec':'h264' })
        li.setArt({'thumb': os.path.join(xbmcaddon.Addon().getAddonInfo("path"), 'icon.png')})
        if not found_index:
            if ut_start > st:
                found_index = True
            else:
                index += 1
        if st > ut_start and ut_start > epg_min:
            label = '[COLOR ffefaf80]%s[/COLOR]'%label
        else:
            label = '[I]%s[/I]'%label
        li.setProperty('isPlayable', 'false')
        li.setLabel(label)
        info = {'title': progname[0]}
        if len(progname) > 1:
            info['plot'] = ' '.join(progname[1:])
        li.setInfo('video', info)
        url = get_url(action='play', cid=cid, sid=sid, arch=1, gmt=ut_start)
        xbmcplugin.addDirectoryItem(_handle, url, li, False)
    xbmc.executebuiltin('Container.SetViewMode(51)')
    xbmcplugin.endOfDirectory(_handle, True)
    xbmc.sleep(100)
    if found_index:
        try:
            win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            win.getControl(win.getFocusId()).selectItem(index)
        except:
            pass

def get_min_max(sid):
    doc = api_call(sid, 'settings', var='stream_standard')
    catchup = doc.get('settings').get('list')[0].get('catchup') 
    max = int(doc.get('servertime')) - catchup.get('delay')
    min = max - catchup.get('length')
    return (min, max)

closescript = False

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
        if self.gmt ==  -1:
            doc = api_call(self.sid, 'get_url', cid=self.cid, protect_code=get_setting('protect'))
        else:
            doc = api_call(self.sid, 'get_url', cid=self.cid, gmt=self.gmt, protect_code=get_setting('protect'))
        url = doc.get('url')
        url = re.sub('http/ts(.*?)\s(.*)', 'http\\1', url)
        s = time.strftime("%d %b %H:%M", time.localtime(self.gmt))
        i = time.strftime("%d %b %H:%M", time.localtime(self.min))
        self.li = xbmcgui.ListItem('%s / %s'%(s,i))
        self.play(url, self.li)

    def onPlayBackStopped(self):
        global closescript
        closescript = True

    def onPlayBackSeek(self, time, seekOffset):
        if self.arch == '1' and not (self.gmt == -1 and seekOffset >= 0):
            self.pause()
            self.min, self.max = get_min_max(self.sid)
            if self.gmt == -1:
                self.gmt = self.max
            self.gmt = self.gmt + int(self.getTime()) + int(seekOffset/1000)
            if self.gmt < self.min:
                self.gmt = self.min
            elif self.gmt > self.max:
                self.gmt = -1
            self.play_channel()

def play_video(sid, cid, arch, gmt):
    monitor = MyMonitor()
    player = MyPlayer(sid=sid, cid=cid, arch=arch, gmt=gmt)
    player.play_channel()
    while not ( closescript ):
        #if player.isPlaying():
        #    xbmc.log("--- "+str(player.gmt)+" "+str(player.getTime()))
        xbmc.sleep(500)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['sid']:
            sid = params['sid']
        else:
            sid = get_sid()
        if params['action'] == 'play':
            play_video(sid, params['cid'], params['arch'], params['gmt'])
        elif params['action'] == 'epg':
            list_epg(sid, params['cid'], params['date'])
        else:
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        sid = get_sid()
        list_channels(sid)

if __name__ == '__main__':
    router(sys.argv[2][1:])
