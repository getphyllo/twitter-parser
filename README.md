# Twitter Parser

## Problem Statement
Most developers face challenges getting the user's data (Tweet and their engagement information) from the Twitter platform. Twitter provides data in the downloadable zip format based on the user's request.
But the main challenge is to parse and have them in some data structure to be used in a consumable form.

## Solution
This library parses the user's Twitter data and exposes it in a data structure to directly consume in any application or library.
The user needs to download the Twitter data from the Twitter platform and provide input to this library.
It helps the user access tweets and engagement information in the memory and smoothly consume it to build any business use case. 

## How to use it?
1. [Download your Twitter archive](https://twitter.com/settings/download_your_data) (Settings > Your account > Download an archive of your data).
2. Twitter may take around 24 hours to provide the zip file.
3. After 24 hours, download the zip file from the above location [Download your Twitter archive](https://twitter.com/settings/download_your_data)
4. Download the zip file into your local system.
5. Import the twitter-parser library into your local project.
6. To import the library, follow these steps.
   1. Install pip and pipenv.
   2. There will be two options, import the library directly from GitHub or clone it into your local and use it.
      1. Import directly from GitHub (recommended)
         ```python
         # If you are using pipenv, use this
         """pipenv install git+ssh://git@github.com/getphyllo/twitter-parser@<branch_name>#egg=twitter_parser"""
         # If you are using pip, use this
         """pip install git+ssh://git@github.com/getphyllo/twitter-parser@<branch_name>#egg=twitter_parser"""
         ```
      2. Clone the twitter-parser into your local and use it.
         ```python
         # If you are using pipenv, use this
         """pipenv install <path_to_git_clone_directory>"""
         # If you are using pip, use this
         """pip install <path_to_git_clone_directory>"""
         ```
   3. The library will be installed in your local project.
7. Provide the `path_to_zip_file` of the archived data as a parameter to TwitterDataParser class.
   ```python
   from twitter_parser.core.parser import TwitterDataParser
   
   if __name__ == "__main__":
       twitter_info = TwitterDataParser(path_to_zip_file='/Users/my_user_name/Desktop/twitter_data.zip')
       #  Here, I have saved the zip file on the desktop, so the path is /Users/my_user_name/Desktop/twitter_data.zip
       var = twitter_info.retrieve_information()
       print(var)
   ```
8. To extract the information of other users, you need to provide the bearer token. (This is mandatory; with this, we can get the other user's info.)
9. Once the bearer token is received, go to the `twitter_parser/utils/constants.py` file and search for the variable `BEARER_TOKEN` and paste it there.
10. In the above code snippet, we have called the `retrieve_information` method, but you can also call `tweets,` `following,` `followers,` `direct_messages,` `group_direct_messages` methods.
11. `retrieve information` method returns the following information:
    ```pydantic
    user_name
    following
    followers
    tweets
    DMs
    media
    groups_dms
    following_count
    follower_count
    ```

## What does it do?
1. Extracts the zip file's contents to the current working directory.
2. Converts the tweets to readable format and stores them in List[Tweet] format.
   ```pydantic
    Tweet(BaseModel):
       tweet_year
       tweet_type
       retweeted_from
       replied_to_names
       replying_to_tweet
       tweet_data
       tweeted_at
       tweet_url
       tweets_attached_media
   ```
3. Replaces URLs with their original versions (the ones found in the archive).
4. Copies used images to an output folder to allow them to move to a new home.
5. It will query Twitter for the missing user handles (check with yours first).
6. Convert DMs to List[DirectMessage] format 
   ```pydantic
   DirectMessage(BaseModel):
       dm_from
       dm_to
       dm_data
       dm_at
   ```
7. Convert Group DMs to List[GroupDirectMessages] format
   ```pydantic
   GroupDirectMessages(BaseModel):
      group_name
      group_dms
      group_participant
   GroupDirectMessage(BaseModule):
      group_dm_from 
      group_dm_data 
      group_dm_at
   ```
8. Converts the following and followers into List[User] format
   ```pydantic
   class User(BaseModel):
       user_handle
       user_profile_url
   ```
9. Converts all the data in TwitterUserInfo format.
   ```pydantic
   TwitterUserInfo(BaseModel):
      user_name
      following
      followers
      tweets
      DMs
      media
      groups_dms
      following_count
      follower_count
   ```
