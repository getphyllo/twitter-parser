UTF_8 = 'utf-8'
WRITE_MODE = 'w'
READ_MODE = 'r'
GUEST_TOKEN = 'guest_token'
ACCOUNT = 'account'
USERNAME = 'username'
SPACE = ' '
USER_URL_TEMPLATE = 'https://twitter.com/i/user/{}'
DATA = 'data'
ACCOUNT_FILE = 'account.js'
TWITTER_PARSER_OUTPUT = 'twitter_parser-output'
MEDIA = 'media'
TWITTER_PARSER_CACHE = 'twitter_parser-cache'
TWITTER_GUEST_TOKEN_ENDPOINT = 'https://api.twitter.com/1.1/guest/activate.json'
TWITTER_USER_METADATA_ENDPOINT = 'https://api.twitter.com/1.1/users/lookup.json?user_id={user_id_list}'
BEARER_TOKEN = 'Paste you Bearer Token here'
SCREEN_NAME = 'screen_name'
CHARACTERS_TO_ESCAPE = r'\_*[]()~`>#+-=|{}.!'
TWEET = 'tweet'
TWEET_CREATED_AT = 'created_at'
TWEET_FULL_TEXT = 'full_text'
TWEET_ID_STR = 'id_str'
TWEET_ENTITIES = 'entities'
TWEET_MEDIA = 'media'
URLS = 'urls'
URL = 'url'
TWEET_EXPANDED_URL = 'expanded_url'
TWEET_DISPLAY_URL = 'display_url'
TWEET_INDICES = 'indices'
RT = 'RT'
TWEET_REPLY_TO_STATUS_ID = 'in_reply_to_status_id'
TWEET_REPLY_TO_SCREEN_NAME = 'in_reply_to_screen_name'
TWEET_REPLY_TO_USER_ID = 'in_reply_to_user_id'
REPLAY_TO_TWEET = 'https://twitter.com/{in_reply_to_screen_name}/status/{in_reply_to_status_id}'
TWEET_EXTENDED_ENTITIES = 'extended_entities'
TWEET_MEDIA_URL = 'media_url'
BEST_QUALITY_URL = 'https://pbs.twimg.com/media/{original_filename}:orig'
TWEET_VIDEO_INFO = 'video_info'
TWEET_VIDEO_INFO_VARIANTS = 'variants'
TWEET_VIDEO_INFO_VARIANTS_BITRATE = 'bitrate'
TWEET_URL = 'https://twitter.com/{username}/status/{tweet_id_str}'
TWEET_USER_MENTIONS = 'user_mentions'
INPUT_TWEET_FILE_TEMPLATES = ['tweet.js', 'tweets.js', 'tweets-part*.js']
INPUT_MEDIA_DIR_TEMPLATES = ['tweet_media', 'tweets_media']
FOLLOWING = 'following'
ACCOUNT_ID = 'accountId'
FOLLOWING_FILE = 'following.js'
UNKNOWN_HANDLE = '~unknown~handle~'
FOLLOWER = 'follower'
FOLLOWER_FILE = 'follower.js'
DIRECT_MESSAGES_FILE = 'direct-messages.js'
DM_CONVERSATION = 'dmConversation'
CONVERSATION_ID = 'conversationId'
MESSAGES = 'messages'
MESSAGE_CREATE = 'messageCreate'
SENDER_ID = 'senderId'
RECIPIENT_ID = 'recipientId'
TEXT = 'text'
CREATED_AT = 'createdAt'
EXPANDED = 'expanded'
DM_MEDIA_URLS = 'mediaUrls'
DIRECT_MESSAGE_MEDIA = 'direct_messages_media'
JOIN_CONVERSATION = 'joinConversation'
INITIATING_USER_ID = 'initiatingUserId'
PARTICIPANTS_SNAPSHOT = 'participantsSnapshot'
PARTICIPANTS_JOIN = "participantsJoin"
USER_IDS = 'userIds'
DIRECT_MESSAGES_GROUP_FILE = 'direct-messages-group.js'
DIRECT_MESSAGES_GROUP_MEDIA = 'direct_messages_group_media'
CONVERSATION_NAME_UPDATE = "conversationNameUpdate"
NAME = 'name'
KNOWN_TWEETS_JSON = "known_tweets.json"
LIST_OF_FILES = [
    "TweetArchive.html",
    "*Tweet-Archive*.html",
    "*Tweet-Archive*.md",
    "DMs-Archive-*.html",
    "DMs-Archive-*.md",
    "DMs-Group-Archive-*.html",
    "DMs-Group-Archive-*.md",
    "followers.txt",
    "following.txt",
]
