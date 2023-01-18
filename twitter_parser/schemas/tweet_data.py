from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, HttpUrl


class User(BaseModel):
    user_handle: Optional[str]
    user_profile_url: Optional[str] = None


class TweetType(str, Enum):
    TWEET = 'TWEET'
    RETWEET = 'RETWEET'
    REPLY = 'REPLY'


class Tweet(BaseModel):
    tweet_year: str
    tweet_type: TweetType
    retweeted_from: Optional[str] = None
    replied_to_names: Optional[List[str]] = None
    replying_to_tweet: Optional[str] = None
    tweet_data: str
    tweeted_at: str
    tweet_url: str
    tweets_attached_media: Optional[str] = None


class DirectMessage(BaseModel):
    dm_from: str
    dm_to: str
    dm_data: str
    dm_at: str


class GroupDirectMessage(BaseModel):
    group_dm_from: str
    group_dm_data: str
    group_dm_at: str


class GroupDirectMessages(BaseModel):
    group_name: Optional[str] = None
    group_dms: Optional[List[GroupDirectMessage]] = None
    group_participant: List[str]


class Media(BaseModel):
    media_url: HttpUrl


class TwitterUserInfo(BaseModel):
    user_name: str
    following: Optional[List[User]] = None
    followers: Optional[List[User]] = None
    tweets: Optional[List[Tweet]] = None
    dms: Optional[List[DirectMessage]] = None
    media: Optional[List[Media]] = None
    groups_dms: Optional[List[GroupDirectMessages]] = None
    following_count: int = 0
    follower_count: int = 0
