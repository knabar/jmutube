import os, fnmatch
import jmutube.settings

def all_files(root, patterns='*', single_level=False, yield_folders=False):
    patterns = patterns.split(';')
    for path, subdir, files in os.walk(root):
        if yield_folders:
            files.extend(subdirs)
        files.sort()
        for name in files:
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    yield os.path.join(path, name)
                    break
        if single_level:
            break

def get_media_path(username, type):
    return os.path.join(jmutube.settings.MEDIA_ROOT, username, type)
    
def clean_filename(username, type, file, exists=True):
    path = get_media_path(username, type)
    combined = os.path.join(path, file)
    if os.path.basename(file) == file and \
        ((exists and os.path.isfile(combined)) or \
        (not exists and not os.path.isfile(combined))):
        return combined
    else:
        return None    

def make_unique(username, type, file, ext):
    c = 1
    ct = ''
    while True:
        newname = clean_filename(username, type, file + ct + '.' + ext, exists=False)
        if newname:
            return newname
        ct = "(%s)" % c
        c = c + 1

def sp_to_us(filename):
    return filename.replace(" ", "_")

def us_to_sp(filename):
    return filename.replace("_", " ")