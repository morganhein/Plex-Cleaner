#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PlexCleaner With Bleach! refactor by Morgan Hein
# PlexCleaner based on PlexAutoDelete by Steven4x4 with modifications from others
# Initial rewrite done by ngovil21 to make the script more cohesive and updated for Plex Home
# Version 1.8 - Added Profies
# Version 1.7 - Added options for Shared Users
# Version 1.1 - Added option dump and load settings from a config file


"""Summary

Attributes:
    DEBUG (enum): Global flag for debug verbosity. Options are WARNINGS, INFO, and DEBUG
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
DEBUG = false
CONFIG_VERSION = 1.8

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
        self.plex = Plex(self.config)
        self.flaggedCount, self.deleteCount, self.moveCount, self.copyCount = 0

    #TODO: This is all wrong, but the concept is there. All this needs to be broken up.
    def scan():
        log("----------------------------------------------------------------------------")
        log("                           Detected Settings")
        log("----------------------------------------------------------------------------")
        log("Host: " + Settings['Host'])
        log("Port: " + Settings['Port'])

        doc_sections = self.plex.getURLX(self.config.settings['Host'] + ":" + Settings['Port'] + "/library/sections/")

        if (not Settings['SectionList']) and doc_sections:
            for Section in doc_sections.getElementsByTagName("Directory"):
                if Section.getAttribute("key") not in Settings['IgnoreSections']:
                    Settings['SectionList'].append(Section.getAttribute("key"))

            Settings['SectionList'].sort(key=int)
            log("Section List Mode: Auto")
            log("Operating on sections: " + ','.join(str(x) for x in Settings['SectionList']))
            log("Skipping Sections: " + ','.join(str(x) for x in Settings['IgnoreSections']))

        else:
            log("Section List Mode: User-defined")
            log("Operating on user-defined sections: " + ','.join(str(x) for x in Settings['SectionList']))

        RescannedSections = []

        for Section in Settings['SectionList']:
            Section = str(Section)

            doc = getURLX(Settings['Host'] + ":" + Settings['Port'] + "/library/sections/" + Section + "/all")
            deck = getURLX(Settings['Host'] + ":" + Settings['Port'] + "/library/sections/" + Section + "/onDeck")

            if not doc:
                log("Failed to load Section %s. Skipping..." % Section)
                continue
            SectionName = doc.getElementsByTagName("MediaContainer")[0].getAttribute("title1")
            log("")
            log("--------- Section " + Section + ": " + SectionName + " -----------------------------------")

            group = doc.getElementsByTagName("MediaContainer")[0].getAttribute("viewGroup")
            changed = 0
            if group == "movie":
                changed = checkMovies(doc, Section)
            elif group == "show":
                for DirectoryNode in doc.getElementsByTagName("Directory"):
                    changed += checkShow(DirectoryNode)
            if changed > 0 and Settings['trigger_rescan']:
                log("Triggering rescan...")
                if getURLX(Settings['Host'] + ":" + Settings['Port'] + "/library/sections/" + Section + "/refresh?deep=1",
                           parseXML=False):
                    RescannedSections.append(Section)

    def precheck(func):
        mediaFile = getLocalPath(mediaFile)
        def func_wrapper(mediaFile, mediaId, location):
            if not os.path.isfile(mediaFile):
                log("[NOT FOUND] " + mediaFile)
                return False
            if this.config.test:
                log("**[FLAGGED] " + mediaFile)
                self.flaggedCount += 1
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
                response = self.plex.delete(mediaId) #TODO Check response for success/failure
                self.deleteCount += 1
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
            self.deleteCount += 1
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
        self.moveCount += 1
        return True

    @precheck
    def actionCopy(mediaFile, mediaId = 0, location = "", fileList):
        try:
            for f in fileList:
                shutil.copy(os.path.realpath(f), location)
                log("**[COPIED] " + file)
            self.copyCount += 1
            return True
        except Exception as e:
            log("error copying file: %s" % e, True)
            return False

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

    def report():
        #TODO: Placeholder for report code
        log("")
        log("----------------------------------------------------------------------------")
        log("----------------------------------------------------------------------------")
        log("                Summary -- Script Completed Successfully")
        log("----------------------------------------------------------------------------")
        log("")
        log("  Total File Count      " + str(FileCount)) #TODO: access these via self.plex.fileCount etc.
        log("  Kept Show Files       " + str(KeptCount))
        log("  On Deck Files         " + str(OnDeckCount))
        log("  Deleted Files         " + str(DeleteCount))
        log("  Moved Files           " + str(MoveCount))
        log("  Copied Files          " + str(CopyCount))
        log("  Flagged Files         " + str(FlaggedCount))
        log("  Rescanned Sections    " + ', '.join(str(x) for x in RescannedSections))
        log("")
        log("----------------------------------------------------------------------------")
        log("----------------------------------------------------------------------------")


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

    def deleteFile(mediaId):
        URL = ("http://" + self.settings['host'] + ":" + self.settings['port'] + "/library/metadata/" + str(mediaId))
        req = urllib2.Request(URL, None, {"X-Plex-Token": self.settings['token']})
        req.get_method = lambda: 'DELETE'
        return urllib2.urlopen(req)

    def checkOnDeck(mediaId):
        if not deck:
            return False
        for DeckVideoNode in deck.getElementsByTagName("Video"):
            if DeckVideoNode.getAttribute("ratingKey") == str(mediaId):
                self.onDeckCount += 1
                return True
        return False

    def getMediaInfo(VideoNode):
        view = VideoNode.getAttribute("viewCount")
        if view == '':
            view = 0
        view = int(view)

        #Find number of days between date video was viewed and today
        lastViewedAt = VideoNode.getAttribute("lastViewedAt")
        if lastViewedAt == '':
            DaysSinceVideoLastViewed = 0
        else:
            d1 = datetime.datetime.today()
            d2 = datetime.datetime.fromtimestamp(float(lastViewedAt))
            DaysSinceVideoLastViewed = (d1 - d2).days

        #Find number of days between date video was added and today
        addedAt = VideoNode.getAttribute("addedAt")
        if addedAt == '':
            DaysSinceVideoAdded = 0
        else:
            d1 = datetime.datetime.today()
            da2 = datetime.datetime.fromtimestamp(float(addedAt))
            DaysSinceVideoAdded = (d1 - da2).days

        MediaNode = VideoNode.getElementsByTagName("Media")
        mediaId = VideoNode.getAttribute("ratingKey")
        for Media in MediaNode:
            PartNode = Media.getElementsByTagName("Part")
            for Part in PartNode:
                file = Part.getAttribute("file")
                if sys.version < '3':  # remove HTML quoted characters, only works in python < 3
                    file = urllib2.unquote(file.encode('utf-8'))
                else:
                    file = urllib2.unquote(file)
                return {'view': view, 'DaysSinceVideoAdded': DaysSinceVideoAdded,
                        'DaysSinceVideoLastViewed': DaysSinceVideoLastViewed, 'file': file, 'media_id': mediaId}

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

    # Shows have a season pages that need to be navigated
    # TODO: This needs to be broken up into smaller parts, this is a little nuts
    def checkShow(showDirectory):
        global KeptCount
        global FileCount
        # Parse all of the episode information from the season pages
        episodes = {}
        show_settings = default_settings.copy()
        show_metadata = getURLX(
            Settings['Host'] + ":" + Settings['Port'] + '/library/metadata/' + showDirectory.getAttribute('ratingKey'))
        collections = show_metadata.getElementsByTagName("Collection")
        for collection in collections:
            collection_tag = collection.getAttribute('tag')
            if collection_tag and collection_tag in Settings['Profiles']:
                show_settings.update(Settings['Profiles'][collection_tag])
                print("Using profile: " + collection_tag)
        show = getURLX(Settings['Host'] + ":" + Settings['Port'] + showDirectory.getAttribute('key'))
        if not show:  # Check if show page is None or empty
            log("Failed to load show page. Skipping...")
            return 0
        media_container = show.getElementsByTagName("MediaContainer")[0]
        show_id = media_container.getAttribute('key')
        show_name = media_container.getAttribute('parentTitle')
        for key in Settings['ShowPreferences']:
            if (key.lower() in show_name.lower()) or (key == show_id):
                show_settings.update(Settings['ShowPreferences'][key])
                break
        # if action is keep then skip checking
        if show_settings['action'].startswith('k'):  # If keeping on show just skip checking
            log("[Keeping] " + show_name)
            log("")
            return 0
        for SeasonDirectoryNode in show.getElementsByTagName("Directory"):  # Each directory is a season
            if not SeasonDirectoryNode.getAttribute('type') == "season":  # Only process Seasons (skips Specials)
                continue
            season_key = SeasonDirectoryNode.getAttribute('key')
            season_num = str(SeasonDirectoryNode.getAttribute('index'))  # Directory index refers to the season number
            if season_num.isdigit():
                season_num = ("%02d" % int(season_num))
            season = getURLX(Settings['Host'] + ":" + Settings['Port'] + season_key)
            if not season:
                continue
            for VideoNode in season.getElementsByTagName("Video"):
                episode_num = str(VideoNode.getAttribute('index'))  # Video index refers to the episode number
                if episode_num.isdigit():  # Check if numeric index
                    episode_num = ("%03d" % int(episode_num))
                if episode_num == "":  # if episode_num blank here, then use something else to get order
                    episode_num = VideoNode.getAttribute('originallyAvailableAt')
                    if episode_num == "":
                        episode_num = VideoNode.getAttribute('title')
                        if episode_num == "":
                            episode_num = VideoNode.getAttribute('addedAt')
                title = VideoNode.getAttribute('title')
                m = getMediaInfo(VideoNode)
                if show_settings['watched']:
                    if m['DaysSinceVideoLastViewed'] > m['DaysSinceVideoAdded']:
                        compareDay = m['DaysSinceVideoAdded']
                    else:
                        compareDay = m['DaysSinceVideoLastViewed']
                else:
                    compareDay = m['DaysSinceVideoAdded']
                key = '%sx%s' % (
                    season_num, episode_num)  # store episode with key based on season number and episode number for sorting
                episodes[key] = {'season': season_num, 'episode': episode_num, 'title': title, 'view': m['view'],
                                 'compareDay': compareDay, 'file': m['file'], 'media_id': m['media_id']}
                FileCount += 1
        count = 0
        changes = 0
        for key in sorted(episodes):
            ep = episodes[key]
            onDeck = CheckOnDeck(ep['media_id'])
            if show_settings['watched']:
                log("%s - S%sxE%s - %s | Viewed: %d | Days Since Last Viewed: %d | On Deck: %s" % (
                    show_name, ep['season'], ep['episode'], ep['title'], ep['view'], ep['compareDay'], onDeck))
                checkWatched = (ep['view'] > 0)
            else:
                log("%s - S%sxE%s - %s | Viewed: %d | Days Since Added: %d | On Deck: %s" % (
                    show_name, ep['season'], ep['episode'], ep['title'], ep['view'], ep['compareDay'], onDeck))
                checkWatched = True
            if ((len(episodes) - count) > show_settings['episodes']) or \
                    (ep['compareDay'] > show_settings[
                        'maxDays'] > 0):  # if we have more episodes, then check if we can delete the file
                checkDeck = False
                if show_settings['onDeck']:
                    checkDeck = onDeck
                check = (not show_settings['action'].startswith('k')) and checkWatched and (
                    ep['compareDay'] >= show_settings['minDays']) and (not checkDeck)
                if check:
                    if performAction(file=ep['file'], action=show_settings['action'], media_id=ep['media_id'],
                                     location=show_settings['location']):
                        changes += 1
                else:
                    log('[Keeping] ' + ep['file'])
                    KeptCount += 1
            else:
                log('[Keeping] ' + ep['file'])
                KeptCount += 1
            log("")
            count += 1
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
        """Loads settings from the opts array with default values where needed.

        Args:
            opts (argparser.args): An argparser args object

        Returns:
            OrderedDict: A dictionary of configuration options
        """

        settings = OrderedDict()
        settings['host'] = opts.get('Host', '127.0.0.1')
        settings['port'] = opts.get('Port', '32400')
        settings['section_list'] = opts.get('SectionList', []])
        settings['ignore_sections'] = opts.get('IgnoreSections', [])
        settings['log_file'] = opts.get('LogFile', TODOCHANGETHIS)
        settings['trigger_rescan'] = opts.get('trigger_rescan', False)
        settings['token'] = opts.get('Token', None)
        settings['username'] = opts.get('Username', None)
        settings['password'] = opts.get('Password', None)
        settings['shared'] = opts.get('Shared', False)
        settings['device_name'] = opts.get('DeviceName', None)
        settings['remote_mount'] = opts.get('RemoteMount', None)
        settings['local_mount'] = opts.get('LocalMount', None)
        settings['plex_delete'] = opts.get('plex_delete', False)
        settings['similar_files'] = opts.get('similar_files', True)
        settings['cleanup_movie_folders'] = opts.get('cleanup_movie_folders', False)
        settings['minimum_folder_size'] = opts.get('minimum_folder_size', 30)
        settings['default_episodes'] = opts.get('default_episodes', 0)
        settings['default_minDays'] = opts.get('default_minDays', 0)
        settings['default_maxDays'] = opts.get('default_maxDays', 30)
        settings['default_action'] = opts.get('default_action', 'flag')
        settings['default_watched'] = opts.get('default_watched', True)
        settings['default_location'] = opts.get('default_location', None)
        settings['default_onDeck'] = opts.get('default_onDeck', True)
        settings['show_preferences'] = OrderedDict(sorted(opts.get('ShowPreferences', {}).items()))
        settings['movie_preferences'] = OrderedDict(sorted(opts.get('MoviePreferences', MoviePreferences).items()))
        settings['profiles'] = OrderedDict(sorted(opts.get('Profiles', Profiles).items()))
        settings['version'] = opts.get('Version', CONFIG_VERSION)

        if not empty(settings['token']):
            if not empty(settings['username']) and not empty(settings['password']):
                settings['token'] = getToken(settings['username'], settings['password'])
                if empty(settings['token']):
                    log("Error getting token, trying without...", True)
                elif test:
                    log("Token: " + Settings['Token'], True)
                    login = True

        if settings['shared'] and settings['token']:
            accessToken = getAccessToken(settings['token'])
            if accessToken:
                settings['token'] = accessToken
                if test:
                    log("Access Token: " + settings['token'], True)
            else:
                log("Access Token not found or not a shared account")

        if not Ssttings['host'].startswith("http"):
            settings['host'] = "http://" + settings['host']

        #TODO: WTF with this
        default_settings = {'episodes': Settings['default_episodes'],
                            'minDays': Settings['default_minDays'],
                            'maxDays': Settings['default_maxDays'],
                            'action': Settings['default_action'],
                            'watched': Settings['default_watched'],
                            'location': Settings['default_location'],
                            'onDeck': Settings['default_onDeck']
                            }

        #TODO: Integrate this into the settings

        ## CUSTOMIZED SHOW SETTINGS ##############################################
        # Customized Settings for certain shows. Use this to override default settings.
        # Only the settings that are being changed need to be given. The setting will match the default settings above
        # You can also specify an id instead of the Show Name. The id is the id assigned by Plex to the show
        # Ex: 'Show Name':{'episodes':3,'watched':True/False,'minDays':,'action':'copy','location':'/path/to/folder'},
        # Make sure each show is separated by a comma. Use this for TV shows
        ShowPreferences = {
            "Show 1": {"episodes": 3, "watched": True, "minDays": 10, "action": "delete", "location": "/path/to/folder",
                       "onDeck": True, "maxDays": 30},
            "Show 2": {"episodes": 0, "watched": False, "minDays": 10, "action": "delete", "location": "/path/to/folder",
                       "onDeck": False, "maxDays": 30},
            "Show 3": {"action": "keep"},  # This show will skipped
            "Show Preferences": {}  # Keep this line
        }
        # Movie specific settings, settings you would like to apply to movie sections only. These settings will override the default
        # settings set above. Change the default value here or in the config file. Use this for Movie Libraries.
        MoviePreferences = {
            'watched': default_watched,  # Delete only watched episodes
            'minDays': default_minDays,  # Minimum number of days to keep
            'action': default_action,  # Action to perform on movie files (delete/move/copy)
            'location': default_location,  # Location to keep movie files
            'onDeck': default_onDeck  # Do not delete move if on deck
        }

        # Profiles allow for customized settings based on Plex Collections. This allows managing of common settings using the Plex Web interface.
        # First set the Profile here, then add the TV show to the collection in Plex.
        Profiles = {
            "Profile 1": {"episodes": 3, "watched": True, "minDays": 10, "action": "delete", "location": "/path/to/folder",
                          "onDeck": True, "maxDays": 30}

        return settings

    def dumpSettings(config):
        """Dumps a configuration file with default values.

        Args:
            config (dict): The default values to write to the config file.
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

def empty(value):
    return value == None or value == ""

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
    cleaner = Cleaner(config)
    cleaner.run()