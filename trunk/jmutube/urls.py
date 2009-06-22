from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.views.generic.simple import direct_to_template

from jmutube.media import *
from jmutube.upload import upload_file, upload_progress


admin.autodiscover()

urlpatterns = patterns('',
    (r'^$', direct_to_template, {'template': 'home.html'}),
    (r'^accounts/login/$', login, {'template_name': 'registration/login.html', 'SSL': True}),
    (r'^accounts/logout/$', logout, {'template_name': 'registration/logout.html'}),
    (r'^accounts/media/upload/$', upload_file),
    (r'^accounts/media/upload/progress/$', upload_progress),
    url(r'^accounts/media/(video|audio|images|crass|presentations)/$', media, name="all-media"),
#    url(r'^accounts/media/(video|audio|images|crass|presentations)/([^/]+)/$', media, name="tagged-media"),
    (r'^accounts/media/(video|audio|images|crass|presentations)/([^/]+)/delete/$', media_delete),
    (r'^accounts/media/(video|audio|images|crass|presentations)/([^/]+)/rename/$', media_rename),
    (r'^accounts/media/(video|audio|images|crass|presentations)/([^/]+)/preview/$', media_preview),
    (r'^accounts/media/$', media, {'type': 'video'}),
    (r'^accounts/media/migrate/$', migrate_files),
    (r'^content/', include('jmutube.repository.urls')),
    (r'^crass/', include('jmutube.crass.urls')),
    url(r'^options/$', direct_to_template, {'template': 'options.html'}, name="options"),
    (r'^help/$', direct_to_template, {'template': 'help.html'}),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)', admin.site.root, {'SSL': True}),
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': 'django.conf'}),
    
    (r'^impersonate/', include('impersonate.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '../static'}),
    )
