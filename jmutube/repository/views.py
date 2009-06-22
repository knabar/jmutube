from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect, Http404
from django.core.files.uploadhandler import FileUploadHandler
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils import simplejson
from django import forms
import os, re
from datetime import datetime
import jmutube.settings
from jmutube.util import *
from models import *
from tagging.models import Tag, TaggedItem

def playlist_rss_feed(request, user, title):
    playlist = get_object_or_404(Playlist, Q(urltitle = title) | Q(id = title), user__username = user)
        
    return render_to_response('playlist.rss',
                              { 'title': playlist.title,
                               'user': playlist.user,
                               'url': 'http://jmutube.cit.jmu.edu/',
                               'playlist': playlist.playlistitem_set.all() },
                              context_instance = RequestContext(request))

def single_file_rss_feed(request, user, file):
    file = get_object_or_404(File, user__username=user, file=file)
        
    return render_to_response('playlist.rss',
                              { 'title': file.title,
                               'user': file.user,
                               'url': 'http://jmutube.cit.jmu.edu/',
                               'playlist': ({'file': file, 'url': file.url },) },
                              context_instance = RequestContext(request))

def playlist_play(request, user, title):
    playlist = get_object_or_404(Playlist, Q(urltitle = title) | Q(id = title), user__username = user)
        
    return render_to_response('playlist.html',
                              { 'title': playlist.title,
                                'feed': 'http://%s%s' % (request.get_host(), reverse(playlist_rss_feed, args=(user, playlist.id))) },
                              context_instance = RequestContext(request))

def playlist_download(request, user, title):
    playlist = get_object_or_404(Playlist, Q(urltitle = title) | Q(id = title), user__username = user)
        
    res = render_to_response('playlist.html',
                              { 'title': playlist.title,
                                'feed': 'http://%s%s' % (request.get_host(), reverse(playlist_rss_feed, args=(user, playlist.id))) },
                              context_instance = RequestContext(request),
                              mimetype = 'application/binary')
    res["Content-Disposition"] = "attachment; filename=playlist.html"
    return res

def playlist_json(request, user, title):
    playlist = get_object_or_404(Playlist, user__username = user, urltitle = title)

    json = simplejson.dumps(
        {'id': playlist.id,
         'user': playlist.user.username,
        'title': playlist.title,
        'urltitle': playlist.urltitle,
        'files': [{'id': item.file.id,
                   'user': item.file.user.username,        
                    'title': item.file.title,
                    'file': item.file.file,
                    'url': 'http://test',
                    'size': item.file.size,
                    'mime_type': item.file.mime_type,
                    'type': item.file.type,
                    'delivery': item.delivery,
                    'deliveryoptions': item.file.delivery} for item in playlist.playlistitem_set.all()]
        })
    
    return HttpResponse(json)

def playlists_json(request, user):
    
    if request.user.username != user:
        raise Http404
    
    playlists = Playlist.objects.filter(user__username = user)
    
    json = simplejson.dumps(
        [{'title': playlist.title, 'urltitle': playlist.urltitle} for playlist in playlists]
    )
    
    return HttpResponse(json)


def store_playlist(request, user):
    
    if request.user.username != user:
        raise Http404
    
    id = int(request.POST['id'])
    title = request.POST['title']
    items = map(int, request.POST['items'].split(','))
    deliveries = request.POST['delivery'].split(',')
    
    if id == 0:
        playlist = Playlist()
        playlist.user = request.user
        playlist.title = title
        playlist.urltitle = "temp" + datetime.now().isoformat()
        playlist.save() # to get id for use in real urltitle
    else:
        playlist = get_object_or_404(Playlist, user=request.user, id=id)
        playlist.title = title
    
    playlist.urltitle = "%s_%s" % (playlist.id, re.sub(r'[^\w]+', '_', title))
    playlist.save()
    
    PlaylistItem.objects.filter(playlist=playlist).delete()
    for (item, delivery) in zip(items, deliveries):
        PlaylistItem(playlist = playlist, file = File.objects.get(user=request.user, id=item), delivery=delivery).save()
    
    json = simplejson.dumps({
        'message': 'Playlist saved',
        'id': playlist.id,
        }
    )
    
    return HttpResponse(json)


def delete_playlist(request, user):
    
    if request.user.username != user:
        raise Http404
    
    id = int(request.POST['id'])
    
    playlist = get_object_or_404(Playlist, user=request.user, id=id)
    playlist.delete();
    
    json = simplejson.dumps(
        {'message': 'Playlist deleted'}
    )
    
    return HttpResponse(json)



def delete_tag(request, user):
    
    if request.user.username != user:
        raise Http404
    
    fileid = int(request.POST['id'])
    tag = int(request.POST['tag'])

    file = get_object_or_404(File, user__username=user, id=fileid)

    TaggedItem.objects.filter(object_id=file.id, tag__id=tag).delete()

    json = simplejson.dumps(
        {'message': 'Tag deleted'}
    )
    
    return HttpResponse(json)
