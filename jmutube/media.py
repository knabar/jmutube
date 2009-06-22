from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseServerError, HttpResponseRedirect
from django.core.files.uploadhandler import FileUploadHandler
from django.core.urlresolvers import reverse
from django.utils.http import urlencode
from django import forms
import os, re
from shutil import rmtree
import jmutube.settings
from jmutube.util import *
from jmutube.repository.models import *
import shutil
from tagging.models import Tag, TaggedItem

@login_required
def media(request, type):
   
    if request.method == 'POST':
        tag = request.POST.get('tag').replace('"', '')
        ids = map(int, filter(None, request.POST.get('files').split(',')))
        if tag and ids:
            for file in File.objects.filter(user=request.user, type=type, id__in=ids):
                Tag.objects.add_tag(file, '"' + tag + '"')
        return HttpResponseRedirect(request.path + '?' + request.GET.urlencode())
    
    selected_tags = request.GET.getlist('tag')

    tag_url = request.path + "?"
    if selected_tags:
        tag_url += urlencode(('tag',t) for t in selected_tags) + "&"

    
    if selected_tags:
        files = TaggedItem.objects.get_by_model(File, '"' + '","'.join(selected_tags) + '"') \
                .filter(user=request.user, type=type).values_list('id', flat=True)
        # rerun by IDs, otherwise it's not possible to retrieve tags due to bad SQL queries in tagging lib
        files = File.objects.filter(id__in=files)
    else:
        files = File.objects.filter(user=request.user, type=type)
        
    files = files.extra(select={'upper_title': 'upper(title)'}, order_by=['upper_title'])    
    
    tags = filter(lambda t: t not in selected_tags, (t.name for t in Tag.objects.usage_for_queryset(files)))
    
    all_tags = (t.name for t in Tag.objects.usage_for_model(File, filters=dict(user=request.user, type=type)))
    
    return render_to_response(os.path.join('media', type + '.html'),
                              { 'type': type,
                               'files': files,
                               'tags': sorted(tags, key=lambda t:t.lower()),
                               'all_tags': sorted(all_tags, key=lambda t:t.lower()),
                               'tag_url': tag_url,
                               'selected_tags': sorted(selected_tags, key=lambda t:t.lower()),},
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
