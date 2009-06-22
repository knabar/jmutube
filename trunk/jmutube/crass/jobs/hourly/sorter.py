from django_extensions.management.jobs import HourlyJob
from django.conf import settings
import os
import shutil
import re
from datetime import datetime
from tagging.models import Tag
from jmutube.crass.models import Mapping, Schedule
from jmutube.repository.models import File
from jmutube.util import make_unique, get_media_path

class Job(HourlyJob):
    help = "Sort CRASS video files"

    file_re = re.compile(r'^(?P<mac>[0-9a-f]{12})_(?P<y>\d{4})-(?P<m>\d\d)-(?P<d>\d\d)_(?P<h>\d\d)-(?P<n>\d\d)-(?P<s>\d\d)\.mp4$', flags=re.IGNORECASE)

    def execute(self):
        
        for file in os.listdir(settings.CRASS_MISC_FOLDER):
            print file,
            match = Job.file_re.match(file)
            if match:
                dt = datetime(int(match.group('y')), int(match.group('m')), int(match.group('d')),
                              int(match.group('h')), int(match.group('n')), int(match.group('s')))
                
                schedules = Schedule.objects.filter(computer__mac_address__iexact=match.group('mac'),
                                                    start_time__lte=dt, end_time__gte=dt)
                if not schedules:
                    print "no schedule found"
                    continue

                schedule = schedules[0]
                
                title = '%s %s (%s)' % (schedule.computer.building, schedule.computer.room, dt)
                
                newname = make_unique(schedule.user.username, 'video', 
                    (schedule.computer.building + ' ' + schedule.computer.room + ' ' + file[13:-4]).replace(' ', '_'),
                    'mp4')
                
                # move file
                
                shutil.move(os.path.join(settings.CRASS_MISC_FOLDER, file), newname)
                
                # add mapping log entry
                
                Mapping.objects.create(source_file=file, target_file=newname, user=schedule.user)
                
                # add file entry
                
                fileobj = File.objects.create(user=schedule.user,
                                    file=os.path.basename(newname),
                                    type='video',
                                    title=title,
                                    size=os.path.getsize(newname))
                
                # add tags
                
                Tag.objects.add_tag(fileobj, '"%s %s"' % (schedule.computer.building, schedule.computer.room))
                Tag.objects.add_tag(fileobj, 'CRASS')
                Tag.objects.add_tag(fileobj, '"Week %s"' % dt.isocalendar()[1])
                Tag.objects.add_tag(fileobj, ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][dt.weekday()])                
                
                print "-> %s" % newname
                
            else:
                print "invalid file"
