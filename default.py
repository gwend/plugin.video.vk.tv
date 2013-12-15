#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs
import urllib
import urllib2
import json

__addonname__ = "vk.com TV"
__timeout__ = 5

""" Load cache """

def vk_load_cache(path, items):
    # checks
    if path is None or path == "":
        return False

    # try to read
    del items[:]
    try:
        with open(path, 'r') as f:
            items.extend(json.load(f))
    except:
        return False
    return True

""" Save cache """

def vk_save_cache(path, items):
    # checks
    if path is None or path == "":
        return False

    # try to write
    try:
        # open file
        with open(path + ".new", 'wb') as f:
            json.dump(items, f)

        # fix updating
        import os

        os.rename(path + ".new", path)
    except:
        return False
    return True

""" vk.com API """

def vk_api(token, method, params):
    try:
        params.append(("access_token", token))
        url = "https://api.vk.com/method/%s?%s" % (method, urllib.urlencode(params))
        data = urllib2.urlopen(url, timeout=__timeout__).read()
        return json.loads(data)["response"]
    except:
        return None

""" Load URL for video """

def vk_load_url(player, image):
    import re
    # load player page with data for SWT
    try:
        data = urllib2.urlopen(player, timeout=__timeout__).read()
    except:
        return ''

    # find vtag
    pattern = re.compile("var video_vtag = \'([^\\\']*)");
    vtag = pattern.search(data).group(1)
    # find cs
    pattern = re.compile("http://([^.]*)");
    cs = pattern.search(image).group(1)
    cs = 'c' + cs[2:]
    # find u
    pattern = re.compile("vk.me/([^/']*)");
    u = pattern.search(image).group(1)
    # base url
    base_url = 'https://ps.vk.me/'
    # check url
    video_url = base_url + cs + '/' + u + '/videos/' + vtag + '.720.mp4'
    try:
        code = urllib2.urlopen(video_url, timeout=__timeout__).code
    except:
        code = 0

    # check code
    #if code != 200:
    #    try:
    #        video_url = base_url + cs + '/' + u + '/videos/' + vtag + '.480.mp4'
    #        code = urllib2.urlopen(video_url, timeout=__timeout__).code
    #    except:
    #        code = 0


    # check result
    if code != 200:
        return ''
        # return direct url
    return video_url

""" Load user """

def vk_load_user(token, owner_id, limit, cache, urls):
    # clear result
    del urls[:]
    # load until limit
    offset = 0
    videos = []

    # progress bar
    dp = xbmcgui.DialogProgress()
    dp.create(__addonname__, "Loading user...")
    dp.update(0)

    chunk = int(limit * 2)
    chunk = max(1, chunk)
    chunk = min(100, chunk)
    depth = 300

    while offset < depth:
        # check cancel
        if dp.iscanceled():
            return True

        # get posts from wall
        print 'video.get ' + str(offset) + ' videos ' + str(len(videos))
        # params
        params = [("owner_id", owner_id), ("offset", offset), ("count", chunk)]
        # update offset
        offset += chunk
        data = vk_api(token, 'video.get', params)
        if data is None:
            return False
            # remove first element
        del data[0]
        # update progress
        dp.update(100 * offset / depth)
        print 'video.get received ' + str(len(data))
        # parse videos
        for video in data:
            try:
                # get vid and owner_id
                item = str(video['owner_id']) + '_' + str(video['vid'])
                # add to video list
                videos.append(item)
                # check limit
                if len(videos) >= limit:
                    break
            except:
                print 'exception'
                continue

            # check limit
            if len(videos) >= limit:
                break

        # check limit
        print 'len = ' + str(len(videos))
        if len(videos) >= limit:
            break

    if dp.iscanceled():
        return True

    # close progress
    dp.update(100)
    dp.close()

    # load videos by list
    return vk_load_videos(token, videos, cache, urls)

""" Load wall """

def vk_load_wall(token, owner_id, limit, cache, urls):
    # check user
    try:
        owner_id = int(owner_id)
    except:
        return vk_load_user(token, 0, limit, cache, urls)

    # clear result
    del urls[:]
    # load until limit
    offset = 0
    videos = []

    # progress bar
    dp = xbmcgui.DialogProgress()
    dp.create(__addonname__, "Loading wall...")
    dp.update(0)

    chunk = int(limit * 2)
    chunk = max(1, chunk)
    chunk = min(100, chunk)
    depth = 300

    while offset < depth:
        # check cancel
        if dp.iscanceled():
            return True

        # get posts from wall
        print 'wall.get ' + str(offset) + ' videos ' + str(len(videos))
        # params
        params = [("owner_id", owner_id), ("offset", offset), ("count", chunk)]
        # update offset
        offset += chunk
        data = vk_api(token, 'wall.get', params)
        if data is None:
            return False
        dp.update(100 * offset / depth)
        print 'wall.get received ' + str(len(data))
        # parse posts
        for post in data:
            try:
                # parse attachments
                attachments = post['attachments']
                for attach in attachments:
                    try:
                        # check type
                        if attach['type'] != 'video':
                            continue

                        # get video info
                        video = attach['video']

                        # get vid and owner_id
                        item = str(video['owner_id']) + '_' + str(video['vid'])
                        # add to video list
                        videos.append(item)
                        # check limit
                        if len(videos) >= limit:
                            break
                    except:
                        continue

                # check limit
                if len(videos) >= limit:
                    break
            except:
                continue

        # check limit
        print 'len = ' + str(len(videos))
        if len(videos) >= limit:
            break

    if dp.iscanceled():
        return True

    # close progress
    dp.update(100)
    dp.close()

    # load videos by list
    return vk_load_videos(token, videos, cache, urls)

""" Load videos """

def vk_load_videos(token, videos, cache, urls):
    print 'cache size: ' + str(len(cache))
    print 'videos size: ' + str(len(videos))
    # result list
    result = []
    # prepare request
    req = []
    for video in videos:
        # check in cache
        for (i, t, u) in cache:
            if i == video:
                result.append((i, t, u))
                break
        else:
            # add for request
            req.append(video)

    # no requests?
    if len(req) == 0:
        print 'urls load from cache'
        urls.extend(result)
        return True

    print str(len(req)) + ' urls will be loaded...'
    print(req)

    # load videos
    params = [("videos", ','.join(req)), ("extended", 0)]
    data = vk_api(token, 'video.get', params)
    if data is None:
        return False
        # remove first element
    del data[0]

    # progress bar
    dp = xbmcgui.DialogProgress()
    dp.create(__addonname__, "Loading videos...")
    dp.update(0)

    pos = 0
    # parse videos
    for video in data:
        # check cancel
        if dp.iscanceled():
            return True

        # update progress
        dp.update(pos * 100 / len(data))
        pos += 1

        try:
            # try parse count
            #if pos == 1:
            #    count = str(video)

            # get video info
            vid = video['vid']
            owner_id = video['owner_id']
            title = video['title']
            player = video['player']
            image = video['image']
            # video unique id
            item = str(owner_id) + '_' + str(vid)
            # load url
            url = vk_load_url(player, image)
            # add to result
            if url is None:
                result.append((item, None, None))
            else:
                result.append((item, title, url))

        except:
            continue

    # make urls
    for video in videos:
        # check in result
        for (i, t, u) in result:
            if i == video:
                urls.append((i, t, u))
                break
        else:
            # check in cache
            for (i, t, u) in cache:
                if i == video:
                    urls.append((i, t, u))
                    break
            else:
                # add empty
                urls.append((video, None, None))

    # progress bar
    dp.update(100)
    dp.close()
    # OK
    return True

""" Play all videos in playlist """

def playAll(urls):
    # create playlist
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    # generating items
    for (i, t, u) in urls:
        if t is None or u is None:
            continue
        item = xbmcgui.ListItem(t, iconImage='DefaultVideo.png', thumbnailImage='')
        item.setInfo(type='Video', infoLabels={'Title': t})
        playlist.add(url=u, listitem=item)

    # start playing
    xbmc.Player().play(playlist)

# addon settings
addon = xbmcaddon.Addon(id='plugin.video.vk.tv')
cfg_app_id = addon.getSetting("cfg_app_id")
cfg_email = addon.getSetting("cfg_email")
cfg_password = addon.getSetting("cfg_password")
cfg_depth = addon.getSetting("cfg_depth")
cfg_source = addon.getSetting("cfg_source")

try:
    cfg_depth = int(cfg_depth)
except:
    cfg_depth = 10

profile = addon.getAddonInfo('profile')

# load token
token_updated = False
tokens = []
if vk_load_cache(xbmc.translatePath(profile + 'token'), tokens):
    token = ''.join(tokens)
else:
    print 'token not loaded'
    token = None

# auth
if token is None:
    import vk_auth
    # check user and password
    if len(cfg_email) < 1 or len(cfg_password) < 1:
        import sys

        xbmcgui.Dialog().ok(__addonname__, 'Emtpy email or password')
        sys.exit()

    # auth
    try:
        token, user_id = vk_auth.auth(cfg_email, cfg_password, cfg_app_id, 'offline,video,wall')
        token_updated = True
    except:
        xbmcgui.Dialog().ok(__addonname__, 'Invalid login or password')
        sys.exit()

# load cache
urls = []
cache = []

#if not vk_load_cache(xbmc.translatePath(profile + 'cache.json'), cache):
#    print 'cache not loaded'

# load wall

if not vk_load_wall(token, cfg_source, cfg_depth, cache, urls):
    import vk_auth
    # auth
    try:
        token, user_id = vk_auth.auth(cfg_email, cfg_password, cfg_app_id, 'offline,video,wall')
        token_updated = True
    except:
        xbmcgui.Dialog().ok(__addonname__, 'Invalid login or password')
        sys.exit()

    # load wall again
    vk_load_wall(token, cfg_source, cfg_depth, cache, urls)

# save token
if token_updated:
    if not vk_save_cache(xbmc.translatePath(profile + 'token'), token):
        print 'token not saved'

# checks
if len(urls) == 0:
    xbmcgui.Dialog().ok(__addonname__, 'No videos for playing')
    sys.exit()

# save cache
#if not vk_save_cache(xbmc.translatePath(profile + 'cache.json'), urls):
#    print 'cache not saved'

# play all
print 'playing...'
playAll(urls)