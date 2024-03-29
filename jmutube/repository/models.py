from django.db import models
from django.contrib.auth.models import User
import os.path
import jmutube.settings
from jmutube.util import *
from jmutube.jmu_authentication import user_authenticated
from impersonate.functions import user_impersonated

FILE_TYPES = {
    'video': ('*.mp4', '*.flv', '*.mov'),  # remove .m4a when audio comes online
    'audio': ('*.mp3', '*.m4a'),
#    'images': ('*.jpg', '*.png', '*.gif',),
    'presentations': ('*.zip',),
    'crass': (),
}

MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.m4v': 'video/x-m4v',
    '.mov': 'video/quicktime',
    '.flv': 'video/x-flv',
    '.mp3': 'audio/mpeg',
    '.m4a': 'audio/mp4a-latm',
#    '.jpg': 'image/jpeg',
#    '.png': 'image/png',
#    '.gif': 'image/gif',
    '.zip': 'application/zip',
}

DELIVERY_CHOICES = (
    ('P', 'Progressive Download'),
    ('S', 'Streaming'),
    ('B', 'P,S'),
)

class File(models.Model):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    file = models.CharField(max_length=255)
    type = models.CharField(max_length=16)
    size = models.PositiveIntegerField()
    delivery = models.CharField(max_length=1, choices=DELIVERY_CHOICES, default='B')

    def __unicode__(self):
        return u'%s/%s (%s)' % (self.type, self.file, self.user)

    def _get_mime_type(self):
        return MIME_TYPES.get(os.path.splitext(self.file)[1]) or 'application/binary'
    mime_type = property(_get_mime_type)

    def get_url(self, delivery=None):
        if not delivery:
            delivery=self.delivery
        m = self.mime_type
        if delivery == 'P' or (m[:5] != 'video' and m[:5] != 'audio'):
            return "http://jmutube.cit.jmu.edu/users/%s/%s/%s" % (self.user.username, self.type, self.file)
        else:
            prot = 'mp4:' if m in ('video/mp4','video/quicktime') else ''
            prot = 'mp3:' if m in ('audio/mpeg') else prot
            file = self.file[:-4] if m in ('audio/mpeg') else self.file
            return "rtmp://flash.streaming.jmu.edu:80/videos/users/%s%s/%s/%s" % (
                    prot, self.user.username, self.type, file)

    @property
    def url(self):
        return self.get_url()

    @property
    def jmutube_player_url(self):
        return self.get_url(delivery='S' if self.mime_type == 'audio/mpeg' else None)

    class Meta:
        unique_together = (("user", "type", "file"),)


class Playlist(models.Model):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=255)
    urltitle = models.CharField(max_length=255)

    def __unicode__(self):
        return u'%s (%s)' % (self.urltitle, self.user)

    class Meta:
        unique_together = (("user", "urltitle"),)


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist)
    file = models.ForeignKey(File)
    delivery = models.CharField(max_length=1, choices=DELIVERY_CHOICES)

    @property
    def url(self):
        return self.file.get_url(delivery=self.delivery)

    @property
    def jmutube_player_url(self):
        return self.file.get_url(delivery='S' if self.file.mime_type == 'audio/mpeg' else self.delivery)

    def __unicode__(self):
        return u'%s in %s' % (self.file, self.playlist)

    class Meta:
        order_with_respect_to = 'playlist'


def file_create_or_update(user, title, filename, type, filesize):
    file = File.objects.filter(user__username=user, type=type, file=filename)
    if file:
        file = file[0]
        if file.size != filesize:
            file.size = filesize
            file.save()
    else:
        file = File(user=User.objects.get(username=user),
                    title=title,
                    file=filename,
                    type=type,
                    size=filesize)
        file.save()

def sync_with_filesystem(user):
    for type in FILE_TYPES:
        path = get_media_path(user, type)
        for filename in filter(lambda f: os.path.split(f)[1][0] != ".",
                               all_files(path, patterns=';'.join(FILE_TYPES[type]), single_level=True)):
            filesize = os.path.getsize(filename)
            filename = os.path.basename(filename)
            file_create_or_update(user,
                                  us_to_sp(os.path.splitext(filename)[0]),
                                  filename,
                                  type,
                                  filesize)

def check_filesystem_on_login(sender, **kwargs):
    username = kwargs['username']
    for type in FILE_TYPES:
        dir = get_media_path(username, type)
        if not os.path.exists(dir):
            os.makedirs(dir)
    sync_with_filesystem(username)

user_authenticated.connect(check_filesystem_on_login)
user_impersonated.connect(check_filesystem_on_login)
