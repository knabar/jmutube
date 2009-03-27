from django.core.management.base import BaseCommand
from .... import settings
from ....util import all_files
from subprocess import *
import re
import os

class Command(BaseCommand):
    help = "Identifies the specified video files"
    args = "directory"

    requires_model_validation = False

    def handle(self, directory, **options):
        
        files = all_files(directory, patterns='*.mov;*.mp4;*.m4v', single_level=True)
        r = re.compile("Video: (.+)\n")
        
        for file in files:
        
            ffmpeg = Popen('ffmpeg -i "%s"' % file, executable=settings.FFMPEG_EXECUTABLE, stdout=PIPE, stderr=PIPE)
            ffmpeg.wait()
            match = r.search(ffmpeg.stderr.read())
            name = os.path.basename(file)
            if match:
                print "%s\t%s" % (name, match.group(1).replace(", ", "\t"))
            else:
                print "%s\tno video" % (name)
