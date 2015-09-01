#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""Summary

Attributes:
    debug (boolean): Description
"""

## Imports

import os, xml.dom.minidom, platform, re, shutil, datetime, glob, sys, json, argparse, time, uuid
from collections import OrderedDict

try:
    import configparser as ConfigParser
except:
    import ConfigParser

try:
    import urllib.request as urllib2
except:
    import urllib2

## Globals
debug = false


class Cleaner:
    """A single cleaner that'll remove the extra crud from Plex in one clean sweep!

    Attributes:
        config (argparser): Description
    """

    def __init__(self, config):
        """Summary

        Args:
            config (TYPE): Description
        """
        self.config = config

    # Cleans up orphaned folders in a section that are less than the max_size (in megabytes)
    def cleanUpFolders(section, max_size):
        for directory in doc_sections.getElementsByTagName("Directory"):
            if directory.getAttribute("key") == section:
                for location in directory.getElementsByTagName("Location"):
                    path = getLocalPath(location.getAttribute("path"))
                    if os.path.isdir(path):
                        for folder in os.listdir(path):
                            dir_path = os.path.join(path, folder)
                            if os.path.isdir(dir_path):
                                if len(
                                        folder) == 1:  # If folder name length is one assume videos are categorized alphabetically, search subdirectories
                                    subfolders = os.listdir(dir_path)
                                else:
                                    subfolders = (" ",)
                                for subfolder in subfolders:
                                    subfolder_path = os.path.join(path, folder, subfolder).strip()
                                    if os.path.exists(os.path.join(subfolder_path,
                                                                   '.nodelete')):  # Do not delete folders that have .nodelete in them
                                        continue
                                    size = getTotalSize(subfolder_path)
                                    if os.path.isdir(subfolder_path) and size < max_size * 1024 * 1024:
                                        try:
                                            if test:  # or default_action.startswith("f"):
                                                log("**[Flagged]: " + subfolder_path)
                                                log("Size " + str(size) + " bytes")
                                                continue
                                            shutil.rmtree(subfolder_path)
                                            log("**[DELETED] " + subfolder_path)
                                        except Exception as e:
                                            log("Unable to delete folder: %s" % e, True)
                                            continue


class Plex:
    """A single Plex server and all methods required to interact with it."""

    def __init__(self, config):
        self.config = config

    def getToken(user, passw):
        """Summary

        Args:
            user (TYPE): Description
            passw (TYPE): Description

        Returns:
            TYPE: Description
        """
        import base64

        if sys.version < '3':
            encode = base64.encodestring('%s:%s' % (user, passw)).replace('\n', '')
        else:
            auth = bytes('%s:%s' % (user, passw), 'utf-8')
            encode = base64.b64encode(auth).replace(b'\n', b'')
        URL = "https://plex.tv/users/sign_in.json"
        headers = {
            'X-Plex-Device-Name': 'Python',
            'X-Plex-Username': user,
            'X-Plex-Platform': platform.system(),
            'X-Plex-Device': platform.system(),
            'X-Plex-Platform-Version': platform.release(),
            'X-Plex-Provides': 'Python',
            'X-Plex-Product': 'PlexCleaner',
            'X-Plex-Client-Identifier': '10101010101010',
            'X-Plex-Version': platform.python_version(),
            'Authorization': b'Basic ' + encode
        }
        try:
            if sys.version < '3':
                req = urllib2.Request(URL, "None", headers)
                response = urllib2.urlopen(req)
                str_response = response.read()
            else:
                import urllib

                req = urllib.request.Request(URL, b"None", headers)
                response = urllib.request.urlopen(req)
                str_response = response.readall().decode('utf-8')
            loaded = json.loads(str_response)
            return loaded['user']['authentication_token']
        except:
            return ""

    # For Shared users, get the Access Token for the server, get the https url as well
    def getAccessToken(Token):
        """Summary

        Args:
            Token (TYPE): Description

        Returns:
            TYPE: Description
        """
        resources = getURLX("https://plex.tv/api/resources?includeHttps=1")
        if not resources:
            return ""
        devices = resources.getElementsByTagName("Device")
        for device in devices:
            if len(devices) == 1 or (Settings['DeviceName'] and (Settings['DeviceName'].lower() in device.getAttribute('name').lower() or Settings['DeviceName'].lower() in device.getAttribute('clientIdentifier').lower())):
                access_token = device.getAttribute('accessToken')
                if not access_token:
                    return ""
                return access_token
            connections = device.getElementsByTagName("Connection")
            for connection in connections:
                if connection.getAttribute('address') == Settings['Host']:
                    access_token = device.getAttribute("accessToken")
                    if not access_token:
                        return ""
                    uri = connection.getAttribute('uri')
                    match = re.compile("(http[s]?:\/\/.*?):(\d*)").match(uri)
                    # print(device.toprettyxml())
                    if match:
                        Settings['Host'] = match.group(1)
                        Settings['Port'] = match.group(2)
                        # print("Host: " + Settings['Host'])
                        # print("Port: " + Settings['Port'])
                    return access_token
        return ""

    def getURLX(URL, data = None, parseXML = True, max_tries = 3, timeout = 1, referer = None):
        for x in range(0, max_tries):
            if x > 0:
                time.sleep(timeout)
            try:
                headers = {
                    'X-Plex-Username': Settings['Username'],
                    "X-Plex-Token": Settings['Token'],
                    'X-Plex-Platform': platform.system(),
                    'X-Plex-Device': platform.machine(),
                    'X-Plex-Device-Name': 'Python',
                    'X-Plex-Platform-Version': platform.release(),
                    'X-Plex-Provides': 'controller',
                    'X-Plex-Product': 'PlexCleaner',
                    'X-Plex-Version': str(CONFIG_VERSION),
                    'X-Plex-Client-Identifier': client_id.hex,
                    'Accept': 'application/xml'
                }
                if referer:
                    headers['Referer'] = referer
                req = urllib2.Request(url=URL, data=data, headers=headers)
                page = urllib2.urlopen(req)
                if page:
                    if parseXML:
                        return xml.dom.minidom.parse(page)
                    else:
                        return page
            except Exception as e:
                print(e)
                continue
        return None

    def precheck(func):
        def func_wrapper(mediaFile, mediaId, location):
            if not os.path.isfile(mediaFile):
                log("[NOT FOUND] " + mediaFile)
                return False
            if this.config.test:
                log("**[FLAGGED] " + mediaFile)
                FlaggedCount += 1 #TODO: replace global
                return False
            if this.config.similar_files:
                regex = re.sub("\[", "[[]", os.path.splitext(mediaFile)[0]) + "*"
                log("Finding files similar to: " + regex)
                fileList = glob.glob(regex)
            else:
                fileList = (mediaFile,)
            return func(mediaFile, mediaId, location, fileList)
        return func_wrapper

    @precheck
    def actionDelete(mediaFile, mediaId = 0, location ="", fileList = None):
        if self.settings['plex_delete']:
            try:
                URL = ("http://" + Settings['Host'] + ":" + Settings['Port'] + "/library/metadata/" + str(mediaId))
                req = urllib2.Request(URL, None, {"X-Plex-Token": Settings['Token']})
                req.get_method = lambda: 'DELETE'
                urllib2.urlopen(req)
                DeleteCount += 1 # TODO: Replace global
                log("**[DELETED] " + mediaFile)
                return True
            except Exception as e:
                log("Error deleting file: %s" % e, True)
                return False
        else:
            for deleteFile in filelist:
                try:
                    os.remove(deleteFile)
                    log("**[DELETED] " + deleteFile)
                except Exception as e:
                    log("error deleting file: %s" % e, True)
                    continue
            DeleteCount += 1 #TODO: Replace global
            return True

    @precheck
    def actionMove(file, mediaId = 0, location = "", fileList = None):
        for f in filelist:
            try:
                os.utime(os.path.realpath(f), None)
                shutil.move(os.path.realpath(f), location)
                log("**[MOVED] " + f)
            except Exception as e:
                log("error moving file: %s" % e)
                return False
            if os.path.islink(f):
                os.unlink(f)

    @precheck
    def actionCopy(mediaFile, mediaId = 0, location = "", fileList):
        try:
            for f in fileList:
                shutil.copy(os.path.realpath(f), location)
                log("**[COPIED] " + file)
            CopyCount += 1 #TODO: Come on...
            return True
        except Exception as e:
            log("error copying file: %s" % e, True)
            return False

    def performAction(file, action, media_id = 0, location = ""):
        global DeleteCount, MoveCount, CopyCount, FlaggedCount

        file = getLocalPath(file)

        elif action.startswith('m'):
            for f in filelist:
                try:
                    os.utime(os.path.realpath(f), None)
                    shutil.move(os.path.realpath(f), location)
                    log("**[MOVED] " + f)
                except Exception as e:
                    log("error moving file: %s" % e)
                    return False
                if os.path.islink(f):
                    os.unlink(f)
            MoveCount += 1
            return True
        elif action.startswith('d'):
            for deleteFile in filelist:
                try:
                    os.remove(deleteFile)
                    log("**[DELETED] " + deleteFile)
                except Exception as e:
                    log("error deleting file: %s" % e, True)
                    continue
            DeleteCount += 1
            return True
        else:
            log("[FLAGGED] " + file)
            FlaggedCount += 1
            return False

    def CheckOnDeck(media_id):
        global OnDeckCount
        if not deck:
            return False
        for DeckVideoNode in deck.getElementsByTagName("Video"):
            if DeckVideoNode.getAttribute("ratingKey") == str(media_id):
                OnDeckCount += 1
                return True
        return False

    def getMediaInfo(VideoNode):
        view = VideoNode.getAttribute("viewCount")
        if view == '':
            view = 0
        view = int(view)
        ################################################################
        ###Find number of days between date video was viewed and today
        lastViewedAt = VideoNode.getAttribute("lastViewedAt")
        if lastViewedAt == '':
            DaysSinceVideoLastViewed = 0
        else:
            d1 = datetime.datetime.today()
            d2 = datetime.datetime.fromtimestamp(float(lastViewedAt))
            DaysSinceVideoLastViewed = (d1 - d2).days
        ################################################################
        ################################################################
        ###Find number of days between date video was added and today
        addedAt = VideoNode.getAttribute("addedAt")
        if addedAt == '':
            DaysSinceVideoAdded = 0
        else:
            d1 = datetime.datetime.today()
            da2 = datetime.datetime.fromtimestamp(float(addedAt))
            DaysSinceVideoAdded = (d1 - da2).days
        ################################################################
        MediaNode = VideoNode.getElementsByTagName("Media")
        media_id = VideoNode.getAttribute("ratingKey")
        for Media in MediaNode:
            PartNode = Media.getElementsByTagName("Part")
            for Part in PartNode:
                file = Part.getAttribute("file")
                if sys.version < '3':  # remove HTML quoted characters, only works in python < 3
                    file = urllib2.unquote(file.encode('utf-8'))
                else:
                    file = urllib2.unquote(file)
                return {'view': view, 'DaysSinceVideoAdded': DaysSinceVideoAdded,
                        'DaysSinceVideoLastViewed': DaysSinceVideoLastViewed, 'file': file, 'media_id': media_id}

    # Movies are all listed on one page
    def checkMovies(doc, section):
        global FileCount
        global KeptCount

        changes = 0
        movie_settings = default_settings.copy()
        movie_settings.update(Settings['MoviePreferences'])
        for VideoNode in doc.getElementsByTagName("Video"):
            title = VideoNode.getAttribute("title")
            movie_id = VideoNode.getAttribute("ratingKey")
            m = getMediaInfo(VideoNode)
            onDeck = CheckOnDeck(movie_id)
            if movie_settings['watched']:
                if m['DaysSinceVideoLastViewed'] > m['DaysSinceVideoAdded']:
                    compareDay = m['DaysSinceVideoAdded']
                else:
                    compareDay = m['DaysSinceVideoLastViewed']
                log("%s | Viewed: %d | Days Since Viewed: %d | On Deck: %s" % (
                    title, m['view'], m['DaysSinceVideoLastViewed'], onDeck))
                checkedWatched = (m['view'] > 0)
            else:
                compareDay = m['DaysSinceVideoAdded']
                log("%s | Viewed: %d | Days Since Viewed: %d | On Deck: %s" % (
                    title, m['view'], m['DaysSinceVideoAdded'], onDeck))
                checkedWatched = True
            FileCount += 1
            checkDeck = False
            if movie_settings['onDeck']:
                checkDeck = onDeck
            check = (not movie_settings['action'].startswith('k')) and checkedWatched and (
                compareDay >= movie_settings['minDays']) and (not checkDeck)
            if check:
                if performAction(file=m['file'], action=movie_settings['action'], media_id=movie_id,
                                 location=movie_settings['location']):
                    changes += 1
            else:
                log('[Keeping] ' + m['file'])
                KeptCount += 1
            log("")
        if cleanup_movie_folders:
            log("Cleaning up orphaned folders less than " + str(minimum_folder_size) + "MB in Section " + section)
            cleanUpFolders(section, minimum_folder_size)
        return changes


class Config:
    """Handles configurations for the cleaner and plex servers with default values."""

    def __init__(self, args):
        """Summary
            self.settings = parsed dictionary of settings
            self.args = the original args from argparser
            self.config = the location of the config file

        Args:
            args (TYPE): Description
        """
        parseArgs(args)
        this.args = args

    /**
    def parseArgs(self, args):
        """Summary

        Args:
            args (TYPE): Description

        Returns:
            TYPE: Description
        """

        if args.dump:
            # Output settings to a json config file and exit
            print("Saving settings to " + args.dump)
            dumpSettings(args.dump)
            exit()

        self.test = args.test

        if args.config:
            self.config = args.config
        # If no config file is provided, check if there is a config file in first the user directory, or the current directory.
        if self.config == "":
            print(os.path.join(os.path.expanduser("~"), ".plexcleaner"))
            if os.path.isfile(os.path.join(os.path.expanduser("~"), ".plexcleaner")):
                self.config = os.path.join(os.path.expanduser("~"), ".plexcleaner")
            elif os.path.isfile(".plexcleaner"):
                self.config = ".plexcleaner"
            elif os.path.isfile("Cleaner.conf"):
                self.config = "Cleaner.conf"
            elif os.path.isfile(os.path.join(sys.path[0], "Cleaner.conf")):
                self.config = os.path.join(sys.path[0], "Cleaner.conf")
            elif os.path.isfile(os.path.join(sys.path[0], "Settings.cfg")):
                self.config = os.path.join(sys.path[0], "Settings.cfg")

        if self.config and os.path.isfile(self.config):
            print("Loading config file: " + self.config)
            with open(self.config, 'r') as infile:
                opt_string = infile.read().replace('\n', '')  # read in file removing breaks
                # Escape odd number of backslashes (Windows paths are a problem)
                opt_string = re.sub(r'(?x)(?<!\\)\\(?=(?:\\\\)*(?!\\))', r'\\\\', opt_string)
                options = json.loads(opt_string)
                self.settings = loadSettings(options)
            if ('Version' not in options) or not options['Version'] or (options['Version'] < CONFIG_VERSION):
                print("Old version of config file! Updating...")
                dumpSettings(self.config)
        else:
            self.settings = loadSettings(Settings)




    # Load Settings from json into an OrderedDict, with defaults
    def loadSettings(opts):
        """Summary
        Loads settings from the opts array with default values where needed.

        Args:
            opts (argparser.args): An argparser args object

        Returns:
            OrderedDict: A dictionary of configuration options
        """

        settings = OrderedDict()
        settings['host'] = opts.get('Host', '127.0.0.1')
        settings['port'] = opts.get('Port', '32400')
        settings['section_list'] = opts.get('SectionList', SectionList)
        settings['ignore_sections'] = opts.get('IgnoreSections', IgnoreSections)
        settings['log_file'] = opts.get('LogFile', LogFile)
        settings['trigger_rescan'] = opts.get('trigger_rescan', trigger_rescan)
        settings['token'] = opts.get('Token', Token)
        settings['username'] = opts.get('Username', Username)
        settings['password'] = opts.get('Password', Password)
        settings['shared'] = opts.get('Shared', Shared)
        settings['device_name'] = opts.get('DeviceName', DeviceName)
        settings['remote_mount'] = opts.get('RemoteMount', RemoteMount)
        settings['local_mount'] = opts.get('LocalMount', LocalMount)
        settings['plex_delete'] = opts.get('plex_delete', plex_delete)
        settings['similar_files'] = opts.get('similar_files', similar_files)
        settings['cleanup_movie_folders'] = opts.get('cleanup_movie_folders', cleanup_movie_folders)
        settings['minimum_folder_size'] = opts.get('minimum_folder_size', minimum_folder_size)
        settings['default_episodes'] = opts.get('default_episodes', default_episodes)
        settings['default_minDays'] = opts.get('default_minDays', default_minDays)
        settings['default_maxDays'] = opts.get('default_maxDays', default_maxDays)
        settings['default_action'] = opts.get('default_action', default_action)
        settings['default_watched'] = opts.get('default_watched', default_watched)
        settings['default_location'] = opts.get('default_location', default_location)
        settings['default_onDeck'] = opts.get('default_onDeck', default_onDeck)
        settings['show_preferences'] = OrderedDict(sorted(opts.get('ShowPreferences', ShowPreferences).items()))
        settings['movie_preferences'] = OrderedDict(sorted(opts.get('MoviePreferences', MoviePreferences).items()))
        settings['profiles'] = OrderedDict(sorted(opts.get('Profiles', Profiles).items()))
        settings['version'] = opts.get('Version', CONFIG_VERSION)
        return settings

    def dumpSettings(config):
        """Summary

        Args:
            output (TYPE): Description

        Returns:
            TYPE: Description
        """
        # Remove old settings
        if 'End Preferences' in Settings['ShowPreferences']:
            Settings['ShowPreferences'].pop('End Preferences')
        if 'Movie Preferences' in Settings['MoviePreferences']:
            Settings['MoviePreferences'].pop('Movie Preferences')
        Settings['ShowPreferences'] = OrderedDict(sorted(Settings['ShowPreferences'].items()))
        Settings['MoviePreferences'] = OrderedDict(sorted(Settings['MoviePreferences'].items()))
        Settings['Profiles'] = OrderedDict(sorted(Settings['Profiles'].items()))
        Settings['Version'] = CONFIG_VERSION
        with open(output, 'w') as outfile:
            json.dump(Settings, outfile, indent=2)


## Helper Functions

def log(msg, debug = False):
    """Summary

    TODO: Rewrite all PRINT statements and send here instead

    Args:
        msg (TYPE): Description
        debug (bool, optional): Description

    Returns:
        TYPE: Description
    """
    try:
        if LogToFile:
            import logging
            if debug:
                logging.debug(msg)
            else:
                logging.info(msg)
    except:
        print("Error logging message")
    try:
        print(msg)
    except:
        print("Cannot print message")

def get_input(prompt = ""):
    if sys.version < 3:
        return raw_input(prompt)
    else:
        return input(prompt)

# Crude method to replace a remote path with a local path. Hopefully python properly takes care of file separators.
def getLocalPath(file):
    if Settings['RemoteMount'] and Settings['LocalMount']:
        if file.startswith(Settings['RemoteMount']):
            file = os.path.normpath(file.replace(Settings['RemoteMount'], Settings['LocalMount'], 1))
    return file

# gets the total size of a file in bytes, recursively searches through folders
def getTotalSize(file):
    total_size = os.path.getsize(file)
    if os.path.isdir(file):
        for item in os.listdir(file):
            itempath = os.path.join(file, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += getTotalSize(itempath)
    return total_size

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", "-test", help="Run the script in test mode", action="store_true", default=False)
    parser.add_argument("--dump", "-dump", help="Dump the settings to a configuration file and exit", nargs='?',
                        const="Cleaner.conf", default=None)
    parser.add_argument("--config", "-config", "--load", "-load",
                        help="Load settings from a configuration file and run with settings")
    parser.add_argument("--update_config", "-update_config", action="store_true",
                        help="Update the config file with new settings from the script and exit")

    config = Config(parser.parse_args())
    plex = Plex(config)