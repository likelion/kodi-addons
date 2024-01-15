# -*- coding: utf-8 -*-
# Module: default
# Author: Leonid Mokrushin
# Created on: 10.03.2021
# License: GPL v.3 http://www.gnu.org/copyleft/gpl.html

import sys, os
import xbmcaddon, xbmcgui, xbmcplugin, xbmc
import urllib, urllib.parse, urllib.request
import json

__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])

path_auth = '/photo/webapi/auth.cgi'
path_entry = '/photo/webapi/entry.cgi'
path_thumb = '/photo/mo/sharing/webapi/entry.cgi'

class DsPhoto(xbmcgui.Window):
    def __init__(self):
        self.host = self.getSetting('host')
        self.username = self.getSetting('username')
        self.password = self.getSetting('password')
        self.items_limit = int(self.getSetting('page_limit'))
        self.arguments = sys.argv[2][1:]
        self.params = {}
        self.sid = ''
        self.offset = 0
        self.page = 0
        self.prefix = 1
        self.errorMessage = ''

    def getAuth(self):
        url = 'http://' + self.host + path_auth
        values = {
            'account': self.username,
            'passwd': self.password,
            'api': 'SYNO.API.Auth',
            'method': 'login',
            'version': '3'
        }
        data = urllib.parse.urlencode(values)
        data = data.encode('ascii')

        req = urllib.request.Request(url, data)
        try:
            rsp = urllib.request.urlopen(req)
            content = rsp.read()
            data = json.loads(content)
            self.sid = data['data']['sid']
            return True
        except Exception as e:
            self.errorMessage = e
            return False

    def albumsList(self, parentAlbumId='1'):
        listing = []
        url = 'http://' + self.host + path_entry

        # folders in the folder
        values = {
            'api': 'SYNO.FotoTeam.Browse.Folder',
            'method': 'list',
            'id': parentAlbumId,
            'offset': self.offset,
            'limit': self.items_limit,
            'version': '1'
        }

        data = urllib.parse.urlencode(values)
        data = data.encode('ascii')

        opener = urllib.request.build_opener()
        opener.addheaders.append(('Cookie', 'id='+self.sid))
        rsp = opener.open(url, data)

        content = rsp.read()
        data = json.loads(content)

        if data['success']:
            for item in data['data']['list']:
                list_item = xbmcgui.ListItem(item['name'][self.prefix:], '')
                item_url = '{0}?action=albums&albumid={1}&sid={2}&prefix={3}'.format(__url__, item['id'], self.sid, len(item['name'])+1)
                listing.append((item_url, list_item, True))

        # items in the folder
        values = {
            'api': 'SYNO.FotoTeam.Browse.Item',
            'method': 'list',
            'folder_id': parentAlbumId,
            'offset': self.offset,
            'limit': self.items_limit,
            'version': '1',
            'additional': '["thumbnail"]',
            'sort_direction': 'asc'
        }

        data = urllib.parse.urlencode(values)
        data = data.encode('ascii')

        opener = urllib.request.build_opener()
        opener.addheaders.append(('Cookie', 'id='+self.sid))
        rsp = opener.open(url, data)

        content = rsp.read()
        data = json.loads(content)

        if data['success']:
            for item in data['data']['list']:
                thumb = 'http://{0}{1}?api=SYNO.FotoTeam.Thumbnail&method=get&version=1&size=sm&id={2}&cache_key={3}&type=unit|Cookie=id={4};'.format(self.host, path_thumb, item['id'], item['additional']['thumbnail']['cache_key'], self.sid)
                list_item = xbmcgui.ListItem(item['filename'], '')
                item_url = '{0}?action=albums&albumid={1}&sid={2}'.format(__url__, item['id'], self.sid)
                list_item.setArt({'thumb': thumb})

                # if item['type'] == 'album':
                #     item_url = '{0}?action=albums&albumid={1}&sid={2}'.format(__url__, item['id'], self.sid)
                #     is_folder = True

                # elif item['type'] == 'photo':
                #     item_url = 'http://{0}{1}?api=SYNO.PhotoStation.Thumb&method=get&version=1&size=large&id={2}|Cookie=PHPSESSID={3};'.format(self.host, path_thumb, item['id'], self.sid)
                #     is_folder = False
                #     list_item.setInfo(type='picture', infoLabels={'Title': item['info']['title']})
                #     list_item.setMimeType('image/{0}'.format(item['info']['name'].split(".")[-1]))

                # elif item['type'] == 'video':
                #     item_url = '{0}?action=video&videoid={1}&qualityid={2}&sid={3}'.format(__url__, item['id'], item['additional']['video_quality'][0]['id'], self.sid)
                #     is_folder = True
                #     container = item['additional']['video_codec']['container']
                #     list_item.setLabel('{0} ({1})'.format(item['info']['name'], container))
                #     list_item.setInfo(type='video', infoLabels={'Title': item['info']['title']})
                #     list_item.setMimeType('video/{0}'.format(container))

                # else:
                #     item_url = ''
                #     is_folder = False

                listing.append((item_url, list_item, False))

            # if int(total) > int(offset):
            #     item_url = '{0}?action=albums&albumid={1}&sid={2}&page={3}'.format(__url__, parentAlbumId, self.sid, str(self.page + 1))
            #     list_item = xbmcgui.ListItem('Next page')
            #     is_folder = True
            #     listing.append((item_url, list_item, is_folder))

            xbmcplugin.setContent(__handle__, 'images')
            xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
            xbmc.executebuiltin('Container.SetViewMode(500)')
            xbmcplugin.endOfDirectory(__handle__, cacheToDisc=False)

    def showVideo(self, videoId=None, qualityId=None):
        item_url = 'http://{0}{1}?api=SYNO.PhotoStation.Download&method=getvideo&version=1&id={2}&quality_id={3}&use_mov=true|Cookie=PHPSESSID={4};'.format(self.host, path_download, videoId, qualityId, self.sid)
        xbmc.Player().play(item_url, xbmcgui.ListItem(''))

    def handleRequest(self):
        self.parseParams()

        if 'page' in self.params:
            self.page = int(self.params['page'])
            self.offset = (self.items_limit * self.page) + 1

        if 'sid' in self.params:
            self.sid = self.params['sid']

        if 'prefix' in self.params:
            self.prefix = int(self.params['prefix'])

        if len(self.sid) == 0:
            if self.host and not self.getAuth():
                title = 'ERROR'
                message = 'error: ' + str(self.errorMessage)
                self.errorMessage = ''
                xbmc.executebuiltin("XBMC.Notification(" + title + ", " + message + ")")

        if 'action' in self.params:

            if self.params['action'] == 'albums':
                if 'albumid' in self.params:
                    albumId = self.params['albumid']
                self.albumsList(albumId)

            if self.params['action'] == 'video':
                if 'videoid' in self.params:
                    videoId = self.params['videoid']
                if 'qualityid' in self.params:
                    qualityId = self.params['qualityid']
                self.showVideo(videoId, qualityId)

        else:
            self.albumsList()

    def parseParams(self):
        if "=" in self.arguments:
            try:
                self.params = {}
                for x in self.arguments.split("&"):
                    elems = x.split("=")
                    if len(elems) == 2:
                        self.params[elems[0]] = elems[1]
            except:
                print ('[DSPHOTO] error in params: ' + self.arguments)

    def getSetting(self, name):
        return xbmcplugin.getSetting(__handle__, name);

dsPhoto = DsPhoto()
dsPhoto.handleRequest()
del dsPhoto
