# -*- coding: utf-8 -*-
# Module: default
# Author: Leonid Mokrushin
# Created on: 03.01.2017
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib.parse import urlencode, quote, unquote, parse_qsl
from urllib.error import URLError, HTTPError
import urllib.request 
import json
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import re
import os
import time
import datetime
from html.parser import HTMLParser

_url = sys.argv[0]
_handle = int(sys.argv[1])
_api = 'http://iptv.kartina.tv/api/json/'
_apis = 'https://iptv.kartina.tv/api/json/'
_assets = 'http://anysta.kartina.tv/assets'
colors = ['ffd8b1', '3cb44b', 'b13ed4', 'e6194b', 'ffe119', '0082c8', 'f58231', 'fabebe', '46f0f0', 'fffac8', 'e6beff',
          'ffd8b1', '3cb44b', 'b13ed4', 'e6194b', 'ffe119', '0082c8', 'f58231', 'fabebe', '46f0f0', 'fffac8', 'e6beff' ]
ID = xbmcaddon.Addon().getAddonInfo('id')
DATA_PATH = xbmcvfs.translatePath("special://profile/addon_data/%s" % ID)
CACHE_PATH = os.path.join(DATA_PATH, "cache")

def get_setting(setting):
    return xbmcaddon.Addon().getSetting(setting)

def api_call(api, sid, method, **kwargs):
    url = '%s%s?%s'%(api, method, urlencode(kwargs))
    xbmc.log('URL = '+url, xbmc.LOGDEBUG)
    req = urllib.request.Request(url)
    if sid != None:
        req.add_header('Cookie', 'MW_SSID=%s'%sid)
    res = urllib.request.urlopen(req)
    body = res.read()
    doc = json.loads(body)
    res.close()
    if 'error' in doc:
        xbmc.executebuiltin('Notification(KartinaTV, %s, 5000)' % doc.get('error').get('message'))
        return None
    return doc

def get_url(**kwargs):
    return '%s?%s'%(_url, urlencode(kwargs))

def get_channel_icon(channel):
    path = '%s/%s.png'%(CACHE_PATH, channel)
    if xbmcvfs.exists(path):
      #xbmc.log('Found cached logo of channel %s'%(channel), xbmc.LOGDEBUG)
      return path
    else:
      if not xbmcvfs.exists(CACHE_PATH):
          xbmcvfs.mkdir(CACHE_PATH)
      for i in range(9, 0, -1):
          try:
              uri = '%s/img/logo/comigo/1/%s.%s.png'%(_assets,channel,i)
              response = urllib.request.urlopen(uri)
              xbmc.log('Found logo of channel %s = %s'%(channel, uri), xbmc.LOGDEBUG)
              f = xbmcvfs.File(path, 'wb')
              f.write(response.read())
              f.close()
              return path
          except HTTPError as e:
              continue
          except URLError as e:
              continue
      xbmc.log('Could not find logo of channel %s'%channel, xbmc.LOGINFO)
      return ''

def list_channels(sid):
    doc = api_call(_apis, sid, 'channel_list', show='all', protect_code=get_setting('protect'))
    if doc == None:
        return
    xbmcplugin.setContent(_handle, 'videos')
    colori = 0
    for group in doc.get('groups'):
        color = 'ff%s'%colors[colori]
        colori += 1
        for channel in group.get('channels'):
            if channel.get('is_video') == 1:
                li = xbmcgui.ListItem()
                menu = []
                arch = channel.get('have_archive')
                if arch == 1:
                    rec = '[COLOR red]%s[/COLOR]'%u'\u2022'
                    url = get_url(action='epg', cid=channel.get('id'), sid=sid, date=time.time())
                    menu.append(('Archive','Container.Update(%s)'%url))
                else:
                    rec = '[COLOR gray]%s[/COLOR]'%u'\u2022'
                url = get_url(action='vod_genres', sid=sid)
                menu.append(('Video library', 'Container.Update(%s)'%url))
                li.addContextMenuItems(menu)
                start = ' [B]--------[/B]  '
                program = ''
                plot = ''
                if 'epg_progname' in channel:
                    progname = channel.get('epg_progname').splitlines()
                    program = ' - ' + progname[0]
                    info = {'title': progname[0]}
                    if len(progname) > 1:
                        plot = ' '.join(progname[1:])
                        info['plot'] = plot
                    if 'epg_start' in channel and 'epg_end' in channel:
                        start = '[[B]%s[/B]] '%datetime.datetime.fromtimestamp(channel.get('epg_start')).strftime('%H:%M')
                        info['duration'] = channel.get('epg_end') - channel.get('epg_start')
                    li.setInfo('video', info)
                li.setLabel('%s [COLOR white]%s[/COLOR][COLOR %s][B]%s[/B][/COLOR]%s'%(rec, start, color, channel.get('name'), program))
                #li.setArt({'thumb': channel.get('icon_link')})
                channel_icon = get_channel_icon(channel.get('id'))
                if channel_icon != '':
                    li.setArt({'thumb': channel_icon})
                else:
                    iname = re.search(r"/(\w+)\.gif", channel.get('icon'))
                    li.setArt({'thumb': 'http://iptv.kartina.tv/img/logo/sml/1/%s.2.png'%(iname.group(1))})
                li.setProperty('isPlayable', 'false')
                url = get_url(action='play', cid=channel.get('id'), name=progname[0], plot=plot, sid=sid, arch=arch, gmt='-1')
                xbmcplugin.addDirectoryItem(_handle, url, li, False)
    skin_used = xbmc.getSkinDir()
    if skin_used == 'skin.estuary':
        xbmc.executebuiltin('Container.SetViewMode(55)')
    else:
        xbmc.executebuiltin('Container.SetViewMode(51)')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)

def list_epg(sid, cid, date):
    day = datetime.datetime.fromtimestamp(float(date))
    doc = api_call(_apis, sid, 'epg', cid=cid, day=day.strftime('%d%m%y'))
    xbmcplugin.setContent(_handle, 'videos')
    if doc == None:
        return
    epg_min, epg_max = get_min_max(sid)
    if epg_min == None or epg_max == None:
        return
    if datetime.datetime.fromtimestamp(epg_min) < day.replace(hour=0, minute=0, second=0):
        day_before = day - datetime.timedelta(days=1)
        li = xbmcgui.ListItem(label=day_before.strftime('%A, %d %B'))
        url = get_url(action='epg', cid=cid, sid=sid, date=day_before.strftime('%s'))
        xbmcplugin.addDirectoryItem(_handle, url, li, True)
    st = int(doc.get('servertime'))
    index = 0
    found_index = False
    for epg in doc.get('epg'):
        ut_start = int(epg.get('ut_start'))
        progname = epg.get('progname').splitlines()
        label = '[COLOR white][[B]%s[/B]][/COLOR] - %s'%(time.strftime('%H:%M', time.localtime(ut_start)), progname[0])
        li = xbmcgui.ListItem()
        li.setArt({'thumb': get_channel_icon(cid)})
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
        if len(progname) > 1:
            plot = ' '.join(progname[1:])
        else:
            plot = ''
        li.setInfo('video', {'title': progname[0], 'plot': plot})
        url = get_url(action='play', cid=cid, name=progname[0], plot=plot, sid=sid, arch=1, gmt=ut_start)
        xbmcplugin.addDirectoryItem(_handle, url, li, False)
    skin_used = xbmc.getSkinDir()
    if skin_used == 'skin.estuary':
        xbmc.executebuiltin('Container.SetViewMode(55)')
    else:
        xbmc.executebuiltin('Container.SetViewMode(51)')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)
    xbmc.sleep(100)
    if found_index:
        try:
            win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            win.getControl(win.getFocusId()).selectItem(index)
        except:
            pass

def vod_genres(sid):
    doc = api_call(_api, sid, 'vod_genres')
    for genre in doc.get('genres'):
        url = get_url(action='vod_list', sid=sid, id=genre.get('id'), page=1)
        li = xbmcgui.ListItem(label=genre.get('name'))
        li.setProperty('isPlayable', 'false')
        xbmcplugin.addDirectoryItem(_handle, url, li, True)
    xbmc.executebuiltin('Container.SetViewMode(50)')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)

def vod_list(sid, id, page):
    doc = api_call(_apis, sid, 'vod_list', type='last', genre=id, page=page)
    xbmcplugin.setContent(_handle, 'movies')
    html = HTMLParser()
    for row in doc.get('rows'):
        url = get_url(action='vod_info', sid=sid, id=row.get('id'))
        name = html.unescape(row.get('name'))
        li = xbmcgui.ListItem(label=name)
        li.setProperty('isPlayable', 'false')
        info = {}
        info['title'] = name
        info['plot'] = html.unescape(row.get('description'))
        info['rating'] = float(row.get('rate_imdb'))
        info['userrating'] = row.get('rate_kinopoisk')
        info['year'] = int(row.get('year'))
        info['mpaa'] = row.get('rate_mpaa')
        li.setInfo('video', info)
        poster = row.get('poster_link')
        if poster == None:
            poster = '%s%s'%(_assets,row.get('poster'))
        li.setArt({'poster': poster, 'fanart': poster})
        xbmcplugin.addDirectoryItem(_handle, url, li, True)
    page = int(page)
    total = int(doc.get('total'))
    if 20 * page < total:
        url = get_url(action='vod_list', sid=sid, id=id, page=page+1)
        li = xbmcgui.ListItem(label='[ [COLOR lightgreen]Page %s[/COLOR] ]'%(page+1))
        li.setProperty('isPlayable', 'false')
        xbmcplugin.addDirectoryItem(_handle, url, li, True)
    xbmc.executebuiltin('Container.SetViewMode(515)')
    xbmcplugin.endOfDirectory(_handle, cacheToDisc=False)

def vod_info(sid, id):
    doc = api_call(_apis, sid, 'vod_info', id=id)
    options = []
    ids = []
    names = []
    html = HTMLParser()
    film = doc.get('film')
    name = html.unescape(film.get('name'))
    li = xbmcgui.ListItem()
    poster = film.get('poster_link')
    if poster == None:
        poster = '%s%s'%(_assets, film.get('poster'))
    li.setArt({'thumb': poster})
    for video in film.get('videos'):
        options.append(html.unescape(video.get('title')))
        ids.append(video.get('id'))
        names.append(('%s (%s)'%(film.get('name'),video.get('title'))).encode('utf8'))
    r = xbmcgui.Dialog().select(film.get('name'), options)
    if r > -1:
        li.setLabel(names[r])
        vod_play(sid, ids[r], li)

def vod_play(sid, id, li):
    doc = api_call(_apis, sid, 'vod_geturl', fileid=id)
    xbmc.Player().play(doc.get('url'), li)

def get_min_max(sid):
    doc = api_call(_apis, sid, 'settings', var='stream_standard')
    if doc == None:
        return (None, None)
    catchup = doc.get('settings').get('list')[0].get('catchup')
    max = int(doc.get('servertime')) - catchup.get('delay')
    min = max - catchup.get('length')
    return (min, max)

def play_video(sid, cid, name, plot, arch, gmt):
    if int(gmt) ==  -1:
        doc = api_call(_apis, sid, 'get_url', cid=cid, protect_code=get_setting('protect'))
    else:
        doc = api_call(_apis, sid, 'get_url', cid=cid, gmt=gmt, protect_code=get_setting('protect'))
    if doc == None:
        return
    url = doc.get('url')
    url = re.sub('http/ts(.*?)\s(.*)', 'http\\1', url)
    li = xbmcgui.ListItem(label=name)
    li.setArt({'thumb': get_channel_icon(cid)})
    li.setInfo('video', {'title': name, 'plot': plot})
    xbmc.Player().play(url, li)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'play':
            play_video(params['sid'], params['cid'], params['name'], params['plot'], params['arch'], params['gmt'])
        elif params['action'] == 'epg':
            list_epg(params['sid'], params['cid'], params['date'])
        elif params['action'] == 'vod_genres':
            vod_genres(params['sid'])
        elif params['action'] == 'vod_list':
            vod_list(params['sid'], params['id'], params['page'])
        elif params['action'] == 'vod_info':
            vod_info(params['sid'], params['id'])
        else:
            xbmc.executebuiltin('Notification(KartinaTV, Invalid paramstring: %s, 5000)' % paramstring)
    else:
        doc = api_call(_apis, None, 'login', **{'login': get_setting('username'), 'pass': get_setting('password')})
        if doc == None:
            xbmc.sleep(2000)
            xbmcaddon.Addon().openSettings()
            return
        list_channels(doc.get('sid'))

if __name__ == '__main__':
    router(sys.argv[2][1:])
