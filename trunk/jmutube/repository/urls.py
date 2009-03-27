from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import direct_to_template

from views import *

urlpatterns = patterns('',
    (r'^([^/]+)/playlist/([^/]+)/rss', playlist_rss_feed),
    (r'^([^/]+)/file/([^/]+)/rss', single_file_rss_feed),
    (r'^([^/]+)/playlist/([^/]+)/json', playlist_json),
    (r'^([^/]+)/playlist/([^/]+)/play', playlist_play),
    (r'^([^/]+)/playlist/([^/]+)/download', playlist_download),
    (r'^([^/]+)/playlists/json', playlists_json),
    (r'^([^/]+)/store_playlist', store_playlist),
    (r'^([^/]+)/delete_playlist', delete_playlist),
)
