from xml.dom.minidom import parse
from django_extensions.management.jobs import HourlyJob
from django.conf import settings
from django.contrib.auth.models import User
import os
import zipfile
import shutil
import re
from jmutube.util import get_media_path, make_unique
from tagging.models import Tag
from jmutube.repository.models import File

class Job(HourlyJob):
    help = "Import relay files"

    def execute(self):
        
        def getElement(dom, *tagname):
            result = dom
            for t in tagname:
                result = result.getElementsByTagName(t)[0]
            return result
        
        files = filter(lambda f: f.endswith('.xml'), os.listdir(settings.RELAY_INCOMING_FOLDER))
        
        regex = re.compile('[^0-9a-z]+', flags=re.IGNORECASE)
        
        for file in files:
            
            try:
                dom = parse(os.path.join(settings.RELAY_INCOMING_FOLDER, file))
                title = getElement(dom, 'presentation', 'title').firstChild.data
                presenter = getElement(dom, 'presentation', 'presenter', 'userName').firstChild.data
                files = [f.getAttribute('name') for f in
                         getElement(dom, 'presentation', 'outputFiles', 'fileList').getElementsByTagName('file')]
                        
                print file
                
                outfile = regex.sub('_', os.path.splitext(file)[0])
                outfile = make_unique(presenter, 'presentations', outfile, 'zip')
                outfilename = os.path.basename(outfile)
                
                # create zipped version
                
                camrec = False
                
                zipfilename = os.path.join(settings.RELAY_INCOMING_FOLDER, outfilename)
                
                zip = zipfile.ZipFile(zipfilename, 'w', zipfile.ZIP_DEFLATED)
                for f in files:
                    zip.write(os.path.join(settings.RELAY_INCOMING_FOLDER, f), f.encode('ascii'))
                    camrec = camrec or f.endswith('.camrec')
                zip.write(os.path.join(settings.RELAY_INCOMING_FOLDER, file), file)
                zip.close()
                
                # create folder and move everything over
                
                def move_or_remove(file, sourcedir, targetdir):
                    if os.path.exists(os.path.join(targetdir, file)):
                        print "File %s exists in %s" % (file, targetdir)
                        os.remove(os.path.join(sourcedir, file))
                    else:
                        shutil.move(os.path.join(sourcedir, file), targetdir)
                
                outdir = outfile + '.content'
                if not os.path.exists(outdir):
                    os.mkdir(outdir)                
                for f in files:
                    move_or_remove(f, settings.RELAY_INCOMING_FOLDER, outdir)
                move_or_remove(file, settings.RELAY_INCOMING_FOLDER, outdir)
                try:
                    shutil.move(zipfilename, outfile)
                except:
                    print "Cannot move ZIP file %s" % zipfilename
                    os.remove(zipfilename)
                
                # create entry point
                
                html = filter(lambda f: f.endswith(".htm") or f.endswith(".html"), os.listdir(outdir))
                if len(html) == 1 and not html in ('default.htm', 'default.html', 'index.htm', 'index.html'):
                    shutil.copy(os.path.join(outdir, html[0]), os.path.join(outdir, 'index.html'))
                
                # add file entry
                
                fileobj = File.objects.create(user=User.objects.get(username=presenter),
                                    file=outfilename,
                                    type='presentations',
                                    title=title,
                                    size=os.path.getsize(outfile))
                
                # add tags
                
                Tag.objects.add_tag(fileobj, 'Relay')
                if camrec:
                    Tag.objects.add_tag(fileobj, 'CamRec')
                print "done"
            
            except:
            
		raise
		
		pass
