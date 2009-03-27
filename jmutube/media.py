from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.files.uploadhandler import FileUploadHandler
from django.core.urlresolvers import reverse
from django import forms
import os, re
from shutil import rmtree
import jmutube.settings
from jmutube.util import *
from jmutube.repository.models import *
import shutil

@login_required
def media(request, type):
    files = File.objects.filter(user=request.user, type=type)
    return render_to_response(os.path.join('media', type + '.html'),
                              { 'type': type, 'files': files },
                              context_instance = RequestContext(request))

@login_required
def migrate_files(request):
    path = get_media_path(request.user.username, '')
    
    if request.method == 'POST':        
        for file in request.POST.getlist('file'):
            shutil.copy2(os.path.join(path, file), os.path.join(path, 'video'))
        sync_with_filesystem(request.user.username)
        return HttpResponseRedirect(reverse('jmutube.media.media', args=['video']))
    
    files = map(lambda f: {'name': os.path.split(f)[1],
                           'exists': os.path.exists(os.path.join(path, 'video', os.path.split(f)[1])) },
                filter(lambda f: os.path.split(f)[1][0] != ".",
                    all_files(path, patterns=';'.join(FILE_TYPES['video']), single_level=True)))
            
    return render_to_response('media/migrate.html',
                              { 'files': files, 'path': path  },
                              context_instance = RequestContext(request))

@login_required
def media_delete(request, type, filename):
    file = get_object_or_404(File, user=request.user, type=type, file=filename)
    fullname = clean_filename(request.user.username, type, file.file)
    
    if request.method == 'POST':
        file.delete()
        try:
            if os.path.exists(fullname + ".content"):
                rmtree(fullname + ".content", ignore_errors=True)
            os.remove(fullname)            
        except:
            pass
        return HttpResponseRedirect(reverse('jmutube.media.media', args=[type]))
    
    return render_to_response("confirm.html",
                              { 'message': 'Are you sure you want to delete the file "%s"?' % file.title, 'type': type },
                              context_instance = RequestContext(request))


class RenameForm(forms.Form):
    title = forms.CharField()
    
@login_required
def media_rename(request, type, filename):
    file = get_object_or_404(File, user=request.user, type=type, file=filename)
    fullname = clean_filename(request.user.username, type, file.file)

    if request.method == 'POST':
        form = RenameForm(request.POST)
        if form.is_valid():
            file.title = form.cleaned_data["title"]
#            base = re.sub(r'[^\w]+', '_', form.cleaned_data["title"])
#            ext = filename.rsplit('.', 1)[1]            
#            if filename != base + '.' + ext:
#                try:
#                    newname = make_unique(request.user.username, type, base, ext)
#                    os.rename(fullname, newname)
#                    file.file = os.path.basename(newname)
#                except:
#                    pass                
            file.save()
            return HttpResponseRedirect(reverse('jmutube.media.media', args=[type]))
    else:
        form = RenameForm(initial={'title': file.title})
    
    return render_to_response("rename.html",
                              { 'form': form, 'type': type },
                              context_instance = RequestContext(request))

@login_required
def media_preview(request, type, filename):
    file = get_object_or_404(File, user=request.user, type=type, file=filename)

    return render_to_response(os.path.join('media', type + '_preview.html'),
                              { 'file': file.file, 'type': 'video' },
                              context_instance = RequestContext(request))
