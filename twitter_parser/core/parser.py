#!/usr/bin/env python3
"""
    twitter-archive-twitter_parser - Python code to parse the Twitter archive file and provides the information
    as an output in various formats.
    Copyright (C) 2022 Tim Hutton - https://github.com/timhutton/twitter-archive-parser

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Optional, List
from urllib.parse import urlparse
import glob
import json
import logging
import os
import re
import shutil
from zipfile import ZipFile

import requests

from twitter_parser.schemas.tweet_data import TwitterUserInfo, User, Tweet, TweetType, DirectMessage, \
    GroupDirectMessages, GroupDirectMessage
from twitter_parser.utils.constants import UTF_8, GUEST_TOKEN, READ_MODE, ACCOUNT, USERNAME, USER_URL_TEMPLATE, \
    DATA, ACCOUNT_FILE, TWITTER_PARSER_OUTPUT, MEDIA, TWITTER_PARSER_CACHE, TWITTER_GUEST_TOKEN_ENDPOINT, \
    TWITTER_USER_METADATA_ENDPOINT, BEARER_TOKEN, SCREEN_NAME, TWEET, TWEET_CREATED_AT, TWEET_FULL_TEXT, TWEET_ID_STR, \
    TWEET_ENTITIES, TWEET_MEDIA, URLS, URL, TWEET_EXPANDED_URL, TWEET_DISPLAY_URL, TWEET_INDICES, RT, \
    TWEET_REPLY_TO_STATUS_ID, TWEET_REPLY_TO_SCREEN_NAME, REPLAY_TO_TWEET, TWEET_EXTENDED_ENTITIES, TWEET_MEDIA_URL, \
    BEST_QUALITY_URL, TWEET_VIDEO_INFO, TWEET_VIDEO_INFO_VARIANTS, TWEET_VIDEO_INFO_VARIANTS_BITRATE, TWEET_URL, \
    TWEET_REPLY_TO_USER_ID, TWEET_USER_MENTIONS, INPUT_TWEET_FILE_TEMPLATES, INPUT_MEDIA_DIR_TEMPLATES, ACCOUNT_ID, \
    FOLLOWING, UNKNOWN_HANDLE, FOLLOWING_FILE, FOLLOWER_FILE, FOLLOWER, DIRECT_MESSAGES_FILE, DM_CONVERSATION, \
    CONVERSATION_ID, MESSAGES, MESSAGE_CREATE, SENDER_ID, RECIPIENT_ID, TEXT, CREATED_AT, EXPANDED, DM_MEDIA_URLS, \
    DIRECT_MESSAGE_MEDIA, JOIN_CONVERSATION, INITIATING_USER_ID, PARTICIPANTS_SNAPSHOT, PARTICIPANTS_JOIN, USER_IDS, \
    DIRECT_MESSAGES_GROUP_FILE, DIRECT_MESSAGES_GROUP_MEDIA, CONVERSATION_NAME_UPDATE, NAME, KNOWN_TWEETS_JSON, \
    LIST_OF_FILES


class UserData:
    def __init__(self, user_id: str, handle: str):
        if user_id is None:
            raise ValueError('user_id = null is not an allowed value in UserData.')
        self.user_id = user_id
        if handle is None:
            raise ValueError('handle=null is not an allowed value in UserData.')
        self.handle = handle


class PathConfig:
    """
    Helper class containing constants for various directories and files.

    The script will only add / change / delete content in its own directories, which start with `twitter_parser-`.
    Files within `twitter_parser-output` are the end result that the user is probably interested in.
    Files within `twitter_parser-cache` are temporary working files, which improve the efficiency if you run
    this script multiple times. They can safely be removed without harming the consistency of  the
    files within `twitter_parser-output`.
    """

    def __init__(self, dir_archive: str):
        self.dir_archive = dir_archive
        self.dir_input_data = os.path.join(dir_archive, DATA)
        self.file_account_js = os.path.join(self.dir_input_data, ACCOUNT_FILE)

        # check if user is in correct folder
        if not os.path.isfile(self.file_account_js):
            msg: str = f'Error: Failed to load {self.file_account_js}'
            raise Exception(msg)

        self.dir_input_media = self.find_dir_input_media()
        self.dir_output = os.path.join(self.dir_archive, TWITTER_PARSER_OUTPUT)
        self.dir_output_media = os.path.join(self.dir_output, MEDIA)
        self.dir_output_cache = os.path.join(self.dir_archive, TWITTER_PARSER_CACHE)
        self.files_input_tweets = self.find_files_input_tweets()

        # structured like an actual tweet output file, can be used to compute relative urls to a media file
        self.example_file_output_tweets = self.create_path_for_file_output_tweets(year=2020, month=12)

    def create_path_for_file_output_tweets(self, year: int, month: int, file_format: str = "html",
                                           kind: str = "tweets") -> str:
        """Builds the path for a tweet-archive file based on some properties."""
        return os.path.join(self.dir_output, f"{kind}-{file_format}", f"{year:04}",
                            f"{year:04}-{month:02}-01-{kind}.{file_format}")

    def find_dir_input_media(self) -> str:
        input_media_dir_templates = INPUT_MEDIA_DIR_TEMPLATES
        input_media_dirs = []
        for input_media_dir_template in input_media_dir_templates:
            input_media_dirs += glob.glob(os.path.join(self.dir_input_data, input_media_dir_template))
        if len(input_media_dirs) == 0:
            logging.error(f'Error: no folders matching {input_media_dir_templates} in {self.dir_input_data}')
            exit()
        if len(input_media_dirs) > 1:
            logging.error(f'Error: multiple folders matching {input_media_dir_templates} in {self.dir_input_data}')
            exit()
        return input_media_dirs[0]

    def find_files_input_tweets(self) -> list:
        """Identify the tweet archive's file and folder names -
        they change slightly depending on the archive size it seems."""
        input_tweets_file_templates = INPUT_TWEET_FILE_TEMPLATES
        files_paths_input_tweets = []
        for input_tweets_file_template in input_tweets_file_templates:
            files_paths_input_tweets += glob.glob(os.path.join(self.dir_input_data, input_tweets_file_template))
        if len(files_paths_input_tweets) == 0:
            logging.error(f'Error: no files matching {input_tweets_file_templates} in {self.dir_input_data}')
            exit()
        return files_paths_input_tweets


class TwitterDataParser:

    def __init__(self, path_to_zip_file: str):
        self._file_path = path_to_zip_file
        self._archive_path = self._extract_and_find_archive()
        self._paths = PathConfig(dir_archive=self._archive_path)
        self.user_name = self._extract_username()
        self._users = {}
        self._user_id_url_template = USER_URL_TEMPLATE

        # To make sure we are updating the old files with new data
        self._migrate_old_output()

        # Tweets
        self.tweets = self._get_tweets()

        # Bulk lookup for user handles from followers, followings, direct messages and group direct messages
        self._bulk_look_up_for_user_handles()

        # Following
        self.following = self._get_following_users()

        # Followers
        self.followers = self._get_followers_users()

        # Direct messages
        self.direct_messages = self._get_direct_messages()

        # group_direct_messages
        self.group_direct_messages = self._get_group_direct_messages()

    def _extract_and_find_archive(self) -> str:
        """
        Extracts the zip file into current working directory, and returns the archive file path
        """

        cd: str = os.getcwd()

        list_file_name: List[str] = self._file_path.split('/')
        file_name_final: str = list_file_name[len(list_file_name) - 1]
        file_name_for_extracted_data: str = f'{cd}/{file_name_final[:len(file_name_final) - 4]}'

        if f'{file_name_final[len(file_name_final) - 4:]}' != '.zip':
            msg: str = "Please provide the zip file of archived twitter data"
            raise Exception(msg)

        # Specifying the zip file name
        file_name: str = self._file_path

        # Opening the zip file in READ mode
        with ZipFile(file_name, 'r') as zipObj:
            # extracting all the files
            logging.info(f'Extracting all the files now to {file_name_for_extracted_data}')
            zipObj.extractall(path=file_name_for_extracted_data)
            logging.info('Done!')

        return file_name_for_extracted_data

    def _extract_username(self) -> str:
        """Returns the user's Twitter username from account.js."""
        account = self._read_json_from_js_file(filename=self._paths.file_account_js)
        return account[0][ACCOUNT][USERNAME]

    def _migrate_old_output(self):
        """If present, moves media and cache files from the archive root to the new locations in
        `paths.dir_output_media` and `paths.dir_output_cache`. Then deletes old output files
        (md, html, txt) from the archive root."""

        # Create new folders, so we can potentially use them to move files there
        os.makedirs(self._paths.dir_output_media, exist_ok=True)
        os.makedirs(self._paths.dir_output_cache, exist_ok=True)

        # Move files that we can re-use:
        if os.path.exists(os.path.join(self._paths.dir_archive, MEDIA)):
            files_to_move = glob.glob(os.path.join(self._paths.dir_archive, MEDIA, "*"))
            if len(files_to_move) > 0:
                logging.info(f"Moving {len(files_to_move)} files from {MEDIA} to '{self._paths.dir_output_media}'")
                for file_path_to_move in files_to_move:
                    file_name_to_move = os.path.split(file_path_to_move)[1]
                    os.rename(file_path_to_move, os.path.join(self._paths.dir_output_media, file_name_to_move))
            os.rmdir(os.path.join(self._paths.dir_archive, MEDIA))

        known_tweets_old_path: str = os.path.join(self._paths.dir_archive, KNOWN_TWEETS_JSON)
        known_tweets_new_path: str = os.path.join(self._paths.dir_output_cache, KNOWN_TWEETS_JSON)
        if os.path.exists(known_tweets_old_path):
            os.rename(known_tweets_old_path, known_tweets_new_path)

        # Delete files that would be overwritten anyway (if user consents):
        output_globs = LIST_OF_FILES
        files_to_delete: list = []

        for output_glob in output_globs:
            files_to_delete += glob.glob(os.path.join(self._paths.dir_archive, output_glob))

        # TODO maybe remove those files only after the new ones have been generated? This way, the user would never
        # end up with less output than before. On the other hand, they might end up with old *and* new versions
        # of the output, if the script crashes before it reaches the code to delete the old version.
        if len(files_to_delete) > 0:
            logging.info(f"\nThere are {len(files_to_delete)} files in the root of the archive, \n"
                         f"which were probably generated from an older version of this script. \n"
                         f"Since then, the directory layout of twitter-archive-twitter_parser has changed \n"
                         f"and these files are generated into the sub-directory 'twitter_parser-output' or \n"
                         f"various sub-sub-directories therein. These are the affected files:")

            for file_to_delete in files_to_delete:
                logging.info(file_to_delete)

            user_input = input(
                '\nOK delete these files? (If the the directory layout would not have changed, '
                'they would be overwritten anyway) [y/N]')
            if user_input.lower() in ('y', 'yes'):
                for file_to_delete in files_to_delete:
                    os.remove(file_to_delete)
                logging.info(f"Files have been deleted. New versions of these files will be generated "
                             f"into 'twitter_parser-output' soon.")

    def _bulk_look_up_for_user_handles(self):

        following_ids: List[str] = self._collect_user_ids_from_followings()
        logging.info(f'found {len(following_ids)} user IDs in followings.')

        follower_ids: List[str] = self._collect_user_ids_from_followers()
        logging.info(f'found {len(follower_ids)} user IDs in followers.')

        dms_user_ids: List[str] = self._collect_user_ids_from_direct_messages()
        logging.info(f'found {len(dms_user_ids)} user IDs in direct messages.')

        group_dms_user_ids: List[str] = self._collect_user_ids_from_group_direct_messages()
        logging.info(f'found {len(group_dms_user_ids)} user IDs in group direct messages.')

        # NOTE -> Bulk lookup for user handles from followers, followings, direct messages and group direct messages
        collected_user_ids_without_followers: List[str] = list(
            set(following_ids).union(set(dms_user_ids)).union(set(group_dms_user_ids))
        )
        collected_user_ids_only_in_followers: set = set(follower_ids).difference(
            set(collected_user_ids_without_followers))
        collected_user_ids: List[str] = list(set(collected_user_ids_without_followers)
                                             .union(collected_user_ids_only_in_followers))

        logging.info(f'\nfound {len(collected_user_ids)} user IDs overall.')

        self._lookup_users(user_ids=collected_user_ids)

    def _collect_user_ids_from_followings(self) -> List[str]:
        """
         Collect all user ids that appear in the followings archive data.
         (For use in bulk online lookup from Twitter.)
        """
        # read JSON file from archive
        following_json = self._read_json_from_js_file(filename=os.path.join(self._paths.dir_input_data, FOLLOWING_FILE))
        # collect all user ids in a list
        following_ids: List[str] = []
        for follow in following_json:
            if FOLLOWING in follow and ACCOUNT_ID in follow[FOLLOWING]:
                following_ids.append(follow[FOLLOWING][ACCOUNT_ID])

        return following_ids

    def _collect_user_ids_from_followers(self) -> List[str]:
        """
         Collect all user ids that appear in the followers archive data.
         (For use in bulk online lookup from Twitter.)
        """
        # read JSON file from archive
        follower_json = self._read_json_from_js_file(filename=os.path.join(self._paths.dir_input_data, FOLLOWER_FILE))
        # collect all user ids in a list
        follower_ids = []
        for follower in follower_json:
            if FOLLOWER in follower and ACCOUNT_ID in follower[FOLLOWER]:
                follower_ids.append(follower[FOLLOWER][ACCOUNT_ID])

        return follower_ids

    def _collect_user_ids_from_direct_messages(self) -> List[str]:
        """
         Collect all user ids that appear in the direct messages archive data.
         (For use in bulk online lookup from Twitter.)
        """
        # read JSON file from archive
        dms_json = self._read_json_from_js_file(filename=os.path.join(self._paths.dir_input_data, DIRECT_MESSAGES_FILE))
        # collect all user ids in a set
        dms_user_ids = set()
        for conversation in dms_json:
            if DM_CONVERSATION in conversation and CONVERSATION_ID in conversation[DM_CONVERSATION]:
                dm_conversation = conversation[DM_CONVERSATION]
                conversation_id = dm_conversation[CONVERSATION_ID]
                user1_id, user2_id = conversation_id.split('-')
                dms_user_ids.add(user1_id)
                dms_user_ids.add(user2_id)

        return list(dms_user_ids)

    def _collect_user_ids_from_group_direct_messages(self) -> List[str]:
        """
         Collect all user ids that appear in the group direct messages archive data.
         (For use in bulk online lookup from Twitter.)
        """
        # read JSON file from archive
        group_dms_json = self._read_json_from_js_file(
            filename=os.path.join(self._paths.dir_input_data, DIRECT_MESSAGES_GROUP_FILE))
        # collect all user ids in a set
        group_dms_user_ids = set()
        for conversation in group_dms_json:
            participants = self._find_group_dm_conversation_participant_ids(conversation)
            for participant_id in participants:
                group_dms_user_ids.add(participant_id)
        return list(group_dms_user_ids)

    @staticmethod
    def _find_group_dm_conversation_participant_ids(conversation: dict) -> set:
        """
        Find IDs of all participating Users in a group direct message conversation
        """
        group_user_ids = set()
        if DM_CONVERSATION in conversation and CONVERSATION_ID in conversation[DM_CONVERSATION]:
            dm_conversation = conversation[DM_CONVERSATION]
            if MESSAGES in dm_conversation:
                for message in dm_conversation[MESSAGES]:
                    if MESSAGE_CREATE in message:
                        group_user_ids.add(message[MESSAGE_CREATE][SENDER_ID])
                    elif JOIN_CONVERSATION in message:
                        group_user_ids.add(message[JOIN_CONVERSATION][INITIATING_USER_ID])
                        for participant_id in message[JOIN_CONVERSATION][PARTICIPANTS_SNAPSHOT]:
                            group_user_ids.add(participant_id)
                    elif PARTICIPANTS_JOIN in message:
                        group_user_ids.add(message[PARTICIPANTS_JOIN][INITIATING_USER_ID])
                        for participant_id in message[PARTICIPANTS_JOIN][USER_IDS]:
                            group_user_ids.add(participant_id)
        return group_user_ids

    def _lookup_users(self, user_ids: List[str]):
        """Fill the users dictionary with data from Twitter"""
        # Filter out any users already known
        filtered_user_ids = [id for id in user_ids if id not in self._users]
        if not filtered_user_ids:
            # Don't bother opening a session if there's nothing to get
            return

        try:
            with requests.Session() as session:
                bearer_token = BEARER_TOKEN
                guest_token = self._get_twitter_api_guest_token(session=session, bearer_token=bearer_token)
                retrieved_users = self._get_twitter_users(session=session, bearer_token=bearer_token,
                                                          guest_token=guest_token, user_ids=filtered_user_ids)
                for user_id, user in retrieved_users.items():
                    if user[SCREEN_NAME] is not None:
                        self._users[user_id] = UserData(user_id=user_id, handle=user[SCREEN_NAME])
        except Exception as err:
            logging.error(f'Failed to download user data: {err}')

    @staticmethod
    def _get_twitter_api_guest_token(session, bearer_token: str) -> str:
        """Returns a Twitter API guest token for the current session."""
        guest_token_response = session.post(TWITTER_GUEST_TOKEN_ENDPOINT,
                                            headers={'authorization': f'Bearer {bearer_token}'},
                                            timeout=2,
                                            )
        guest_token = json.loads(guest_token_response.content)[GUEST_TOKEN]
        if not guest_token:
            raise Exception(f"Failed to retrieve guest token")
        return guest_token

    @staticmethod
    def _get_twitter_users(session, bearer_token: str, guest_token: str, user_ids: list) -> dict:
        """Asks Twitter for all metadata associated with user_ids."""
        users = {}
        while user_ids:
            max_batch = 100
            user_id_batch = user_ids[:max_batch]
            user_ids = user_ids[max_batch:]
            user_id_list = ",".join(user_id_batch)
            query_url = TWITTER_USER_METADATA_ENDPOINT.format(user_id_list=user_id_list)
            response = session.get(query_url,
                                   headers={'authorization': f'Bearer {bearer_token}', 'x-guest-token': guest_token},
                                   timeout=2,
                                   )
            if not response.status_code == 200:
                raise Exception(f'Failed to get user handle: {response}')
            response_json = json.loads(response.content)
            for user in response_json:
                users[user[TWEET_ID_STR]] = user
        return users

    def _get_tweets(self) -> List[Tweet]:
        """Read tweets from paths.files_input_tweets.
           Copy the media used to paths.dir_output_media.
           Collect user_id:user_handle mappings for later use, in 'users'.
        """

        logging.info('Started parsing the tweets...')
        tweets: List[Tweet] = []
        media_sources = []
        for tweets_js_filename in self._paths.files_input_tweets:
            json_obj = self._read_json_from_js_file(filename=tweets_js_filename)
            for tweet in json_obj:
                tweets.append(self._convert_tweet(tweet=tweet, media_sources=media_sources, users=self._users))

        logging.info(f'Parsing the tweets are done, found {len(tweets)} tweets...')

        return tweets

    def _convert_tweet(self, tweet: dict, media_sources: list, users: dict) -> Tweet:
        """Converts a JSON-format tweet and return Tweet"""
        if TWEET in tweet.keys():
            tweet = tweet[TWEET]
        timestamp_str = tweet[TWEET_CREATED_AT]
        # Example: Tue Mar 19 14:05:17 +0000 2019
        body_markdown: str = ""
        for word in tweet[TWEET_FULL_TEXT].split():
            body_markdown += word + " "
        tweet_id_str = tweet[TWEET_ID_STR]

        tweet_type: TweetType = TweetType.TWEET
        retweeted_from: Optional[str] = None
        replied_to_names_list: Optional[List[str]] = None
        replying_to_tweet_by_user: Optional[str] = None
        tweet_data: str
        tweeted_at: str = timestamp_str
        tweet_year: str = timestamp_str.split()[5]
        tweet_attached_media: Optional[str] = None

        if tweet[TWEET_FULL_TEXT].split()[0] == RT:
            tweet_type = TweetType.RETWEET
            retweeted_from_handle = tweet[TWEET_FULL_TEXT].split()[1]
            retweeted_from = retweeted_from_handle[1:len(retweeted_from_handle) - 1]
            body_markdown: str = ""
            words: int = 0
            for word in tweet[TWEET_FULL_TEXT].split():
                if words > 1:
                    body_markdown += word + " "
                else:
                    words += 1

        # NOTE -> For old tweets before embedded t.co redirects were added, ensure the links are added to the urls
        #         entities list so that we can build correct links later on.
        if TWEET_ENTITIES in tweet and TWEET_MEDIA not in tweet[TWEET_ENTITIES] \
                and len(tweet[TWEET_ENTITIES].get(URLS, [])) == 0:
            for word in tweet[TWEET_FULL_TEXT].split():
                try:
                    url = urlparse(word)
                except ValueError:
                    pass  # Don't crash when trying to parse something that looks like a URL but actually isn't
                else:
                    if url.scheme != '' and url.netloc != '' and not word.endswith('\u2026'):
                        # Shorten links similar to twitter
                        netloc_short = url.netloc[4:] if url.netloc.startswith("www.") else url.netloc
                        path_short = url.path if len(url.path + '?' + url.query) < 15 \
                            else (url.path + '?' + url.query)[:15] + '\u2026'
                        tweet[TWEET_ENTITIES][URLS].append({
                            URL: word,
                            TWEET_EXPANDED_URL: word,
                            TWEET_DISPLAY_URL: netloc_short + path_short,
                            TWEET_INDICES: [tweet[TWEET_FULL_TEXT].index(word),
                                            tweet[TWEET_FULL_TEXT].index(word) + len(word)],
                        })

        # NOTE -> replace t.co URLs with their original versions
        if TWEET_ENTITIES in tweet and URLS in tweet[TWEET_ENTITIES]:
            for url in tweet[TWEET_ENTITIES][URLS]:
                if URL in url and TWEET_EXPANDED_URL in url:
                    expanded_url = url[TWEET_EXPANDED_URL]
                    body_markdown = body_markdown.replace(url[URL], expanded_url)

        # NOTE -> If the tweet is a reply, construct a header that links the names of the accounts
        #         being replied to the tweet being replied to
        if TWEET_REPLY_TO_STATUS_ID in tweet:
            # match and remove all occurrences of '@username ' at the start of the body
            replying_to = re.match(r'^(@[0-9A-Za-z_]* )*', body_markdown)[0]
            if replying_to:
                body_markdown = body_markdown[len(replying_to):]
            else:
                # no '@username ' in the body: we're replying to self
                replying_to = f'@{self.user_name}'

            names = replying_to.split()
            tweet_type = TweetType.REPLY
            replied_to_names_list = names

            # Some old tweets lack 'in_reply_to_screen_name': use it if present, otherwise fall back to names[0]
            in_reply_to_screen_name = tweet[TWEET_REPLY_TO_SCREEN_NAME] if TWEET_REPLY_TO_SCREEN_NAME in tweet else \
                names[0]
            in_reply_to_status_id = tweet[TWEET_REPLY_TO_STATUS_ID]
            replying_to_tweet_by_user = REPLAY_TO_TWEET.format(in_reply_to_screen_name=in_reply_to_screen_name,
                                                               in_reply_to_status_id=in_reply_to_status_id)

        # Replace image URLs with image links to local files
        if TWEET_ENTITIES in tweet and TWEET_MEDIA in tweet[TWEET_ENTITIES] and TWEET_EXTENDED_ENTITIES in tweet \
                and TWEET_MEDIA in tweet[TWEET_EXTENDED_ENTITIES]:
            original_url = tweet[TWEET_ENTITIES][TWEET_MEDIA][0][URL]
            markdown = ''
            for media in tweet[TWEET_EXTENDED_ENTITIES][TWEET_MEDIA]:
                if URL in media and TWEET_MEDIA_URL in media:
                    original_expanded_url = media[TWEET_MEDIA_URL]
                    original_filename = os.path.split(original_expanded_url)[1]
                    archive_media_filename = tweet_id_str + '-' + original_filename
                    archive_media_path = os.path.join(self._paths.dir_input_media, archive_media_filename)
                    file_output_media = os.path.join(self._paths.dir_output_media, archive_media_filename)
                    media_url = self._rel_url(file_output_media, self._paths.example_file_output_tweets)
                    markdown += '' if not markdown and body_markdown == original_url else ''
                    if os.path.isfile(archive_media_path):
                        # Found a matching image, use this one
                        if not os.path.isfile(file_output_media):
                            shutil.copy(archive_media_path, file_output_media)
                        markdown += f'{media_url}'
                        # Save the online location of the best-quality version of this file, for later upgrading if wanted
                        best_quality_url = BEST_QUALITY_URL.format(original_filename=original_filename)
                        media_sources.append(
                            (os.path.join(self._paths.dir_output_media, archive_media_filename), best_quality_url)
                        )
                    else:
                        # Is there any other file that includes the tweet_id in its filename?
                        archive_media_paths = glob.glob(os.path.join(self._paths.dir_input_media,
                                                                     tweet_id_str + '*'))
                        if len(archive_media_paths) > 0:
                            for archive_media_path in archive_media_paths:
                                archive_media_filename = os.path.split(archive_media_path)[-1]
                                file_output_media = os.path.join(self._paths.dir_output_media,
                                                                 archive_media_filename)
                                media_url = self._rel_url(file_output_media, self._paths.example_file_output_tweets)
                                if not os.path.isfile(file_output_media):
                                    shutil.copy(archive_media_path, file_output_media)
                                markdown += f'{media_url} > Your browser does not support the video tag'
                                # Save the online location of the best-quality version of this file,
                                # for later upgrading if wanted
                                if TWEET_VIDEO_INFO in media and TWEET_VIDEO_INFO_VARIANTS in \
                                        media[TWEET_VIDEO_INFO]:
                                    best_quality_url = ''
                                    best_bitrate = -1  # some valid videos are marked with bitrate=0 in the JSON
                                    for variant in media[TWEET_VIDEO_INFO][TWEET_VIDEO_INFO_VARIANTS]:
                                        if TWEET_VIDEO_INFO_VARIANTS_BITRATE in variant:
                                            bitrate = int(variant[TWEET_VIDEO_INFO_VARIANTS_BITRATE])
                                            if bitrate > best_bitrate:
                                                best_quality_url = variant[URL]
                                                best_bitrate = bitrate
                                    if best_bitrate == -1:
                                        logging.warning(
                                            f"Warning No URL found for {original_url} {original_expanded_url} "
                                            f"{archive_media_path} {media_url}")
                                        logging.info(f"JSON: {tweet}")
                                    else:
                                        media_sources.append(
                                            (os.path.join(self._paths.dir_output_media, archive_media_filename),
                                             best_quality_url)
                                        )
                        else:
                            logging.warning(
                                f'Warning: missing local file: {archive_media_path}. Using original link instead: '
                                f'{original_url} (expands to {original_expanded_url})')
                            markdown += f'{original_url}'
            body_markdown = body_markdown.replace(original_url, "")
            tweet_attached_media = markdown

        # Append the original Twitter URL as a link
        tweet_url: str = TWEET_URL.format(username=self.user_name, tweet_id_str=tweet_id_str)

        # extract user_id:handle connections
        if TWEET_REPLY_TO_USER_ID in tweet and TWEET_REPLY_TO_SCREEN_NAME in tweet and \
                tweet[TWEET_REPLY_TO_SCREEN_NAME] is not None:
            reply_to_id = tweet[TWEET_REPLY_TO_USER_ID]
            if int(reply_to_id) >= 0:  # some ids are -1, not sure why
                handle = tweet[TWEET_REPLY_TO_SCREEN_NAME]
                users[reply_to_id] = UserData(user_id=reply_to_id, handle=handle)
        if TWEET_ENTITIES in tweet and TWEET_USER_MENTIONS in tweet[TWEET_ENTITIES] \
                and tweet[TWEET_ENTITIES][TWEET_USER_MENTIONS] is not None:
            for mention in tweet[TWEET_ENTITIES][TWEET_USER_MENTIONS]:
                if mention is not None and 'id' in mention and SCREEN_NAME in mention:
                    mentioned_id = mention['id']
                    if int(mentioned_id) >= 0:  # some ids are -1, not sure why
                        handle = mention[SCREEN_NAME]
                        if handle is not None:
                            users[mentioned_id] = UserData(user_id=mentioned_id, handle=handle)

        tweet: Tweet = Tweet(tweet_year=tweet_year, tweet_type=tweet_type, retweeted_from=retweeted_from,
                             replied_to_names=replied_to_names_list, replying_to_tweet=replying_to_tweet_by_user,
                             tweet_data=body_markdown, tweeted_at=tweeted_at, tweet_url=tweet_url,
                             tweets_attached_media=tweet_attached_media)

        return tweet

    @staticmethod
    def _rel_url(media_path: str, document_path: str) -> str:
        """Computes the relative URL needed to link from `document_path` to `media_path`.
           Assumes that `document_path` points to a file (e.g. `.md` or `.html`), not a directory."""
        return os.path.relpath(media_path, os.path.split(document_path)[0]).replace("\\", "/")

    def _get_following_users(self) -> List[User]:
        """Parse paths.dir_input_data/following.js.
                """

        following: List[User] = []
        following_json = TwitterDataParser._read_json_from_js_file(
            filename=os.path.join(self._paths.dir_input_data, FOLLOWING_FILE))
        following_ids = []
        for follow in following_json:
            if FOLLOWING in follow and ACCOUNT_ID in follow[FOLLOWING]:
                following_ids.append(follow[FOLLOWING][ACCOUNT_ID])
        for following_id in following_ids:
            handle = self._users[following_id].handle if following_id in self._users else UNKNOWN_HANDLE
            following.append(User(user_handle=handle, user_profile_url=self._user_id_url_template.format(following_id)))

        return following

    def _get_followers_users(self) -> List[User]:
        """Parse paths.dir_input_data/followers.js.
                """
        followers: List[User] = []
        follower_json = TwitterDataParser._read_json_from_js_file(
            filename=os.path.join(self._paths.dir_input_data, FOLLOWER_FILE))
        follower_ids = []
        for follower in follower_json:
            if FOLLOWER in follower and ACCOUNT_ID in follower[FOLLOWER]:
                follower_ids.append(follower[FOLLOWER][ACCOUNT_ID])
        for follower_id in follower_ids:
            handle = self._users[follower_id].handle if follower_id in self._users else UNKNOWN_HANDLE
            followers.append(User(user_handle=handle, user_profile_url=self._user_id_url_template.format(follower_id)))

        return followers

    def _get_direct_messages(self) -> List[DirectMessage]:
        """Parse paths.dir_input_data/direct-messages.js, write to one markdown file per conversation.
                """

        # Read JSON file
        dms_json = self._read_json_from_js_file(filename=os.path.join(self._paths.dir_input_data, DIRECT_MESSAGES_FILE))

        # Parse the DMs
        dms: List[DirectMessage] = []
        for conversation in dms_json:
            if DM_CONVERSATION in conversation and CONVERSATION_ID in conversation[DM_CONVERSATION]:
                dm_conversation = conversation[DM_CONVERSATION]
                if MESSAGES in dm_conversation:
                    for message in dm_conversation[MESSAGES]:
                        if MESSAGE_CREATE in message:
                            message_create = message[MESSAGE_CREATE]
                            if all(tag in message_create for tag in [SENDER_ID, RECIPIENT_ID, TEXT, CREATED_AT]):
                                to_id = message_create[RECIPIENT_ID]
                                from_id = message_create[SENDER_ID]
                                body = message_create[TEXT]
                                # Replace t.co URLs with their original versions
                                if URLS in message_create and len(message_create[URLS]) > 0:
                                    for url in message_create[URLS]:
                                        if URL in url and EXPANDED in url:
                                            expanded_url = url[EXPANDED]
                                            body = body.replace(url[URL], expanded_url)
                                # Escape message body for markdown rendering:
                                body_markdown = ""
                                for word in body.split():
                                    body_markdown += word + " "
                                # Replace image URLs with image links to local files
                                if DM_MEDIA_URLS in message_create \
                                        and len(message_create[DM_MEDIA_URLS]) == 1 \
                                        and URLS in message_create:
                                    original_expanded_url = message_create[URLS][0][EXPANDED]
                                    message_id = message_create['id']
                                    media_hash_and_type = message_create[DM_MEDIA_URLS][0].split('/')[-1]
                                    archive_media_filename = f'{message_id}-{media_hash_and_type}'
                                    new_url = os.path.join(self._paths.dir_output_media, archive_media_filename)
                                    archive_media_path = \
                                        os.path.join(self._paths.dir_input_data, DIRECT_MESSAGE_MEDIA,
                                                     archive_media_filename)
                                    if os.path.isfile(archive_media_path):
                                        # Found a matching image, use this one
                                        if not os.path.isfile(new_url):
                                            shutil.copy(archive_media_path, new_url)
                                        image_markdown = f'{new_url}'
                                        body_markdown = body_markdown.replace(
                                            original_expanded_url, image_markdown
                                        )
                                    else:
                                        archive_media_paths = glob.glob(
                                            os.path.join(self._paths.dir_input_data, DIRECT_MESSAGE_MEDIA,
                                                         message_id + '*'))
                                        if len(archive_media_paths) > 0:
                                            for archive_media_path in archive_media_paths:
                                                archive_media_filename = os.path.split(archive_media_path)[-1]
                                                media_url = os.path.join(self._paths.dir_output_media,
                                                                         archive_media_filename)
                                                if not os.path.isfile(media_url):
                                                    shutil.copy(archive_media_path, media_url)
                                                video_markdown = f'{media_url} Your browser does not support the video tag'
                                                body_markdown = body_markdown.replace(
                                                    original_expanded_url, video_markdown
                                                )
                                        else:
                                            logging.info(f'Warning: missing local file: {archive_media_path}. '
                                                         f'Using original link instead: {original_expanded_url})')

                                created_at = message_create[CREATED_AT]  # example: 2022-01-27T15:58:52.744Z
                                to_handle = self._users[to_id].handle if to_id in self._users \
                                    else self._user_id_url_template.format(to_id)
                                from_handle = self._users[from_id].handle if from_id in self._users \
                                    else self._user_id_url_template.format(from_id)

                                # make the body a quote
                                body_markdown = '\n'.join(body_markdown.splitlines())
                                dm: DirectMessage = DirectMessage(dm_from=from_handle, dm_to=to_handle,
                                                                  dm_data=body_markdown, dm_at=created_at)
                                dms.append(dm)

        return dms

    def _get_group_direct_messages(self) -> List[GroupDirectMessages]:
        """Parse data_folder/direct-messages-group.js, write to one markdown file per conversation.
                """
        # read JSON file from archive
        group_dms_json = self._read_json_from_js_file(
            filename=os.path.join(self._paths.dir_input_data, DIRECT_MESSAGES_GROUP_FILE))

        # Parse the group DMs, store messages into group_direct_message
        group_direct_message: List[GroupDirectMessages] = []
        for conversation in group_dms_json:
            group_name: Optional[str] = None
            group_dms: Optional[List[GroupDirectMessage]] = []
            group_participant: List[str] = []
            if DM_CONVERSATION in conversation and CONVERSATION_ID in conversation[DM_CONVERSATION]:
                dm_conversation = conversation[DM_CONVERSATION]
                participants = self._find_group_dm_conversation_participant_ids(conversation)
                for participant_id in participants:
                    if participant_id in self._users:
                        group_participant.append(self._users[participant_id].handle)
                    else:
                        group_participant.append(self._user_id_url_template.format(participant_id))

                if MESSAGES in dm_conversation:
                    for message in dm_conversation[MESSAGES]:
                        if MESSAGE_CREATE in message:
                            message_create = message[MESSAGE_CREATE]
                            if all(tag in message_create for tag in [SENDER_ID, TEXT, CREATED_AT]):
                                from_id = message_create[SENDER_ID]
                                body = message_create[TEXT]

                                # Replace t.co URLs with their original versions
                                if URLS in message_create:
                                    for url in message_create[URLS]:
                                        if URL in url and EXPANDED in url:
                                            expanded_url = url[EXPANDED]
                                            body = body.replace(url[URL], expanded_url)

                                body_markdown = ""
                                for word in body.split():
                                    body_markdown += word + " "

                                # Replace image URLs with image links to local files
                                if DM_MEDIA_URLS in message_create \
                                        and len(message_create[DM_MEDIA_URLS]) == 1 \
                                        and URLS in message_create:
                                    original_expanded_url = message_create[URLS][0][EXPANDED]
                                    message_id = message_create['id']
                                    media_hash_and_type = message_create[DM_MEDIA_URLS][0].split('/')[-1]
                                    archive_media_filename = f'{message_id}-{media_hash_and_type}'
                                    new_url = os.path.join(self._paths.dir_output_media, archive_media_filename)
                                    archive_media_path = \
                                        os.path.join(self._paths.dir_input_data, DIRECT_MESSAGES_GROUP_MEDIA,
                                                     archive_media_filename)
                                    if os.path.isfile(archive_media_path):
                                        # found a matching image, use this one
                                        if not os.path.isfile(new_url):
                                            shutil.copy(archive_media_path, new_url)
                                        image_markdown = f'\n![]({new_url})\n'
                                        body_markdown = body_markdown.replace(
                                            original_expanded_url, image_markdown
                                        )
                                    else:
                                        archive_media_paths = glob.glob(
                                            os.path.join(self._paths.dir_input_data, DIRECT_MESSAGES_GROUP_MEDIA,
                                                         message_id + '*'))
                                        if len(archive_media_paths) > 0:
                                            for archive_media_path in archive_media_paths:
                                                archive_media_filename = os.path.split(archive_media_path)[-1]
                                                media_url = os.path.join(self._paths.dir_output_media,
                                                                         archive_media_filename)
                                                if not os.path.isfile(media_url):
                                                    shutil.copy(archive_media_path, media_url)
                                                video_markdown = f'{media_url} Your browser does not support the video tag'
                                                body_markdown = body_markdown.replace(
                                                    original_expanded_url, video_markdown
                                                )
                                        else:
                                            logging.warning(f'Warning: missing local file: {archive_media_path}. '
                                                            f'Using original link instead: {original_expanded_url})')

                                group_dm_at = message_create[CREATED_AT]  # example: 2022-01-27T15:58:52.744Z
                                group_dm_from = self._users[from_id].handle if from_id in self._users \
                                    else self._user_id_url_template.format(from_id)
                                group_dm_data = '\n>'.join(body_markdown.splitlines())
                                group_dms.append(
                                    GroupDirectMessage(group_dm_from=group_dm_from, group_dm_data=group_dm_data,
                                                       group_dm_at=group_dm_at))
                        elif CONVERSATION_NAME_UPDATE in message:
                            conversation_name_update = message[CONVERSATION_NAME_UPDATE]
                            if all(tag in conversation_name_update for tag in [NAME]):
                                group_name = conversation_name_update[NAME]

                group_direct_message.append(GroupDirectMessages(group_name=group_name, group_dms=group_dms,
                                                                group_participant=group_participant))

        return group_direct_message

    @staticmethod
    def _read_json_from_js_file(filename: str):
        """Reads the contents of a Twitter-produced .js file into a dictionary."""
        logging.info(f'Parsing {filename}...')
        with open(filename, READ_MODE, encoding=UTF_8) as f:
            data = f.readlines()
            # if the JSON has no real content, it can happen that the file is only one line long.
            # in this case, return an empty dict to avoid errors while trying to read non-existing lines.
            if len(data) <= 1:
                return {}
            # convert js file to JSON: replace first line with just '[', squash lines into a single string
            prefix = '['
            if '{' in data[0]:
                prefix += ' {'
            data = prefix + ''.join(data[1:])
            # parse the resulting JSON and return as a dict
            return json.loads(data)

    def retrieve_information(self) -> TwitterUserInfo:

        twitter_user_info: TwitterUserInfo = TwitterUserInfo(user_name=self.user_name,
                                                             following=self.following,
                                                             followers=self.followers,
                                                             tweets=self.tweets,
                                                             dms=self.direct_messages,
                                                             groups_dms=self.group_direct_messages,
                                                             following_count=len(self.following),
                                                             follower_count=len(self.followers))

        return twitter_user_info
