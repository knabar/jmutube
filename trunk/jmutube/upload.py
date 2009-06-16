from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.files.uploadhandler import FileUploadHandler
from django.core.urlresolvers import reverse
from django import forms
from django.contrib.auth.models import User
import os, fnmatch
import shutil
import re
from jmutube.unzip import unzip
import jmutube.settings
from jmutube.repository.models import File, FILE_TYPES, file_create_or_update
from jmutube.util import *

class UploadFileForm(forms.Form):
    file = forms.FileField()


def unzip_archive(file):
    dirname = file + ".content"
    unzip(verbose=False).extract(file, dirname)
    # check for single root directory
    dirs = os.listdir(dirname)
    if len(dirs) == 1 and os.path.isdir(os.path.join(dirname, dirs[0])):
        dir = os.path.join(dirname, dirs[0])
        os.rename(dir, dir + ".jmutube.temp")
        dir += ".jmutube.temp"
        for f in os.listdir(dir):
            shutil.move(os.path.join(dir, f), os.path.join(dirname, f))
        os.rmdir(dir)
    # check for entry point
    html = filter(lambda f: f.endswith(".htm") or f.endswith(".html"), os.listdir(dirname))
    if len(html) == 1 and not html in ('default.htm', 'default.html', 'index.htm', 'index.html'):
        shutil.copy(os.path.join(dirname, html[0]), os.path.join(dirname, 'index.html'))

def handle_uploaded_file(f, username, type):
    (base, ext) = f.name.rsplit('.', 1)
    name = make_unique(username, type, re.sub(r'[^\w]+', '_', base), ext.lower())
    destination = open(name, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()
    file_create_or_update(username, us_to_sp(base), os.path.basename(name), type, os.path.getsize(name))
    if type == 'presentations':
        unzip_archive(name)

def determine_type(filename):
    ext = "*" + os.path.splitext(filename)[1].lower()
    for type in FILE_TYPES:
        if ext in FILE_TYPES[type]:
            return type
    return None

@login_required
def upload_file(request):
    if request.method == 'POST':
        request.upload_handlers.insert(0, UploadProgressCachedHandler(request))
        uploadform = UploadFileForm(request.POST, request.FILES)
        if uploadform.is_valid():
            file = request.FILES['file']
            type = determine_type(file.name)
            if type:
                handle_uploaded_file(file, request.user.username, type)
                return HttpResponseRedirect(reverse('jmutube.media.media', args=[type]))
            else:
                request.user.message_set.create(message="The file you uploaded does not have a valid extension." +
                                                "Valid files are %s." % (','.join([','.join(x) for x in FILE_TYPES.values()])))
                return HttpResponseRedirect(reverse('jmutube.upload.upload_file'))
    else:
        uploadform = UploadFileForm()
        
    return render_to_response('upload.html', { 'uploadform': uploadform, }, context_instance = RequestContext(request))

def upload_progress(request):
    """
    Return JSON object with information about the progress of an upload.
    """
    progress_id = ''
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
    elif 'X-Progress-ID' in request.META:
        progress_id = request.META['X-Progress-ID']
    if progress_id:
        from django.utils import simplejson
        cache_key = "%s_%s" % (request.META['REMOTE_ADDR'], progress_id)
        data = cache.get(cache_key)
        return HttpResponse(simplejson.dumps(data))
    else:
        return HttpResponseServerError('Server Error: You must provide X-Progress-ID header or query param.')



class UploadProgressCachedHandler(FileUploadHandler):
    """
    Tracks progress for file uploads.
    The http post request must contain a header or query parameter, 'X-Progress-ID'
    which should contain a unique string to identify the upload to be tracked.
    """

    def __init__(self, request=None):
        super(UploadProgressCachedHandler, self).__init__(request)
        self.progress_id = None
        self.cache_key = None

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        self.content_length = content_length
        if 'X-Progress-ID' in self.request.GET :
            self.progress_id = self.request.GET['X-Progress-ID']
        elif 'X-Progress-ID' in self.request.META:
            self.progress_id = self.request.META['X-Progress-ID']
        if self.progress_id:
            self.cache_key = "%s_%s" % (self.request.META['REMOTE_ADDR'], self.progress_id )
            cache.set(self.cache_key, {
                'length': self.content_length,
                'uploaded' : 0
            })

    def new_file(self, field_name, file_name, content_type, content_length, charset=None):
        pass

    def receive_data_chunk(self, raw_data, start):
        if self.cache_key:
            data = cache.get(self.cache_key)
            data['uploaded'] += self.chunk_size
            cache.set(self.cache_key, data)
        return raw_data
    
    def file_complete(self, file_size):
        pass

    def upload_complete(self):
        if self.cache_key:
            cache.delete(self.cache_key)
