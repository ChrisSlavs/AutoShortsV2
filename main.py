# Vid maker
# Create video of ai read reddit post
# Ver 3
# Christopher Slaveski
# 2/5/2024

import os
import praw
import subprocess
import copy
import requests
import math
import random as rand
from private import *

from praw import models
from CONSTANTS import *
from moviepy.editor import *

# Global Constants
POST_LIMIT = 2
SUBREDDIT = ""
MANIFEST_FILE = "Working/manifest.txt"

class Post():
    def __init__(self, submission:models.Submission=None):
        # final path and voiceover should be set when final videos are cut, in case there are more than one video/mp3
        self.submission = submission
        self.filePaths = {"text": None, "voiceover":{"basename": None, "final": None}, "subtitles": None, 
                          "background_original":None, "background": None, "final":{"basename":None}}

    # gets all attributes for class not set by instantiation
    def set_attributes(self, filePaths:dict):
        id = self.submission.id
        
        # set file paths
        for key in filePaths.keys():
            if os.path.isdir(filePaths[key]):
                match key:
                    case "text":
                        self.filePaths[key] = filePaths[key] + id + ".txt"  
                    case "voiceover":
                        self.filePaths[key]["basename"] = filePaths[key] + id + ".mp3"  
                    case "subtitles":
                        # cant set exact outputfile path due to whisper only accepting folders for output
                        self.filePaths[key] = filePaths[key]  
                    case "background":
                        self.filePaths[key] = filePaths[key] + id + ".mp4"
                    case "background_original":
                        self.filePaths[key] = filePaths[key]
                    case "final":
                        self.filePaths[key]['basename'] = filePaths[key] + id + ".mp4"
            else:
                self.filePaths[key] = filePaths[key]
        return

        # TODO add check for proper filepath extensions and if paths exist

    # get the submission text and write it to a text file
    def get_text(self):
        # local variables
        text = ""
        finalString = ""
        sortedString = []
        # get submission text
        text = self.submission.selftext
        text = re.sub(regex["NON_ASCII"], "", text)
        
        # sorts submission text and writes to text file
        sortedString = split_text(text, 50, 50)
        finalString = "\n".join(sortedString)
        
        file = open(self.filePaths["text"], "w", encoding="utf-8")
        file.write(finalString)
        file.close()
        
        return

    def get_voiceover(self, payload:dict, voiceID:str="hKULXlJp90RYPLVAaOJI"):
        """
        Requests to elevenlabs api are not sent directly after get_text() method
        due to the need for error checking within the text itself

        Technically it would be easier to send over requests to elevenlabs after get_text()
        due to the fact the text is organized into around 50 char long segments, negating the
        need for this breakdown of the text. It could instead be sent in indexes of around
        30-40, not 50 as the lines do run over 50 char.
        """

        """
        # add voice ID to url
        thisUrl = payload["url"] + voiceID
        #create chunks of text ~2500 char in length
        stringPayload = []
        with open(self.filePaths["text"], "r", encoding="utf-8") as f:
            text = f.read()
            stringPayload = split_text(text, 2500, 2480)
        """
        # request
        """
        for i, seg in enumerate(stringPayload):
            self.filePaths["voiceover"][str(i)] = f"{self.filePaths['voiceover']['basename'][:-4]}PART{str(i)}.mp3"
            payload["data"]["text"] = stringPayload[i]
            response = requests.post(url=thisUrl, json=payload["data"], headers=payload["headers"])
            with open(self.filePaths["voiceover"][str(i)], "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        """
        # set final name for spliced voiceover
        # could just use basename, but both elements serve different purposes, improves readability
        self.filePaths['voiceover']['final'] = f"{self.filePaths['voiceover']['basename']}"
        concatFile = f"{os.path.dirname(self.filePaths['voiceover']['basename'])}{self.submission.id}concat.txt" 
        """
        # write names of voiceovers to file for ffmpeg concat
        with open(f"{concatFile}", "w") as f:
            for i in range(0, len(self.filePaths['voiceover']) - 2):
                print(i)
                f.write(f"file './{self.filePaths['voiceover'][str(i)]}'\n")
        
        
        subprocess.Popen(f"ffmpeg -f concat -safe 0 -i {concatFile} -c copy {self.filePaths['voiceover']['final']}", shell=True).wait()

        # for safety using checks
        for i in range(0, len(self.filePaths['voiceover']) - 2):
            if os.path.exists(self.filePaths['voiceover'][str(i)]) and os.path.isfile(self.filePaths['voiceover'][str(i)]):
                os.remove(self.filePaths['voiceover'][str(i)])
            else:
                print(f"Error: file {self.filePaths['voiceover']['basename'][:-4]}PART{str(i)} does not  exist. skipping.")
                continue
        if os.path.exists
        
        if os.path.exists(concatFile) and os.path.isfile(concatFile):
            os.remove(concatFile)
        else:
            print(f"Error: file {concatFile} does not exists. skipping")

        """

        return

    def get_srt(self, model:str='base'):
        print(self.filePaths["subtitles"])
        subprocess.Popen(f"whisper {self.filePaths['voiceover']['final']} --model {model} --word_timestamps True --max_words_per_line 3 --output_format srt -o {self.filePaths['subtitles']}", shell=True).wait()
        
        return
    
    def burn_final(self):
        # duration of voice over
        voiceover = AudioFileClip(self.filePaths["voiceover"]['final'])
        voiceoverDuration = voiceover.duration
        voiceover.close()

        #duration of background video
        bgVideo = VideoFileClip(self.filePaths["background_original"])
        bgDuration = bgVideo.duration
        bgVideo.close()

        # TODO add two seconds to end of videos
        start = rand.randint(0, int(bgDuration) - int(voiceoverDuration) - 2)

        # cut background video
        subprocess.Popen(f"ffmpeg -ss {start} -i {self.filePaths['background_original']} -force_key_frames expr:gte(t,n_forced*60) -c copy -t {voiceoverDuration + 2} {self.filePaths['background']}").wait()

        # add audio and subtitles
        subtitlePath = self.filePaths["subtitles"] + self.submission.id + ".srt"
        subprocess.Popen(f"ffmpeg -i {self.filePaths['background']} -i {self.filePaths['voiceover']['final']} -force_key_frames expr:gte(t,n_forced*60) -vf subtitles={subtitlePath}:force_style='FontName=Roboto,Alignment=10,Fontsize=36,OutlineColour=#000000,Outline=1' -c:v libx264 -c:a aac -strict experimental -map 0:v -map 1:a {self.filePaths['final']['final']}").wait()

        return
    
    def cut_finals(self):
        # maybe cut video before to preserve quality
        video = VideoFileClip(self.filePaths["final"]["basename"])
        duration = video.duration
        print(duration)
        video.close()
        
        if (duration > 60):
            segmentCount = 0
            segmentCount = int(video.duration) // 60
            print(segmentCount)
            
            for i in range(0, segmentCount):
                self.filePaths['final'][str(i)] = f"{self.filePaths['final']['basename'][:-4]}PART{i}.mp4"
                
                start = i * 60
                print("Start: ", start, "End: ", start + 60, "i Val: ", i)
                subprocess.Popen(f"ffmpeg -ss {start} -i {self.filePaths['final']['basename']} -c copy -t 60 {self.filePaths['final'][str(i)]}").wait()

            if (int(duration) % 60) != 0:
                self.filePaths['final'][str(i+1)] = f"{self.filePaths['final']['basename'][:-4]}PART{i+1}.mp4"
                subprocess.Popen(f"ffmpeg -ss {segmentCount * 60} -i {self.filePaths['final']['basename']} -c copy -t {duration % 60} {self.filePaths['final'][str(i+1)]}").wait()

        return

    def write_manifest(self, manifestFile:str):
        with open(manifestFile, "a") as f:
            f.write(f"{self.submission.id}\n")
        
        return
            
    def run(self, filePaths:dict, payload:dict, manifestFile:str, voiceID:str="hKULXlJp90RYPLVAaOJI", model:str="base"):
        self.set_attributes(filePaths=filePaths)
        #self.get_text()
        #self.get_voiceover(payload, voiceID)
        #self.get_srt(model)
        #self.burn_final()
        #self.cut_finals()
        self.write_manifest(manifestFile=manifestFile)

        return

def check_manifest(manifestFile, submissionID:str):
    # return variable
    check = True
    with open(manifestFile, "r") as f:
        for line in f:
            if submissionID in line.strip():
                check = False

    return check 

# returns dictionary 
def get_posts(subreddit:models.Subreddit, manifestFile:str) -> dict:
    global POST_LIMIT
    # return Dictionary
    posts = {}
    # Key = submission ID Value = Instance of post class wrapping Submission

    posts = {f"{submission.id}":Post(submission=submission) for submission in subreddit.hot(limit=POST_LIMIT) 
              if check_manifest(manifestFile=manifestFile, submissionID=submission.id)}
    
    return posts

def split_text(text:str, lenCheck:int, iterLen:int) -> list:
    newLineIndex = 0
    lastLineIndex = 0
    textSegments = []
    finalString = ""
    textLength = 0    
    textLength = len(text)
    # elevenlabs api only accepts 5000 characters at once
    # TODO probably dont need if statement and can just leave it as the for statement
    if textLength > lenCheck:
        for i in range(iterLen, textLength, iterLen):
            newLineIndex = text.find(" ", i)
            textSegments.append(text[lastLineIndex:newLineIndex].strip())
            lastLineIndex = newLineIndex
            i = newLineIndex
    
        finalString = text[lastLineIndex:]
        textSegments.append(finalString)
    else:
        finalString = text[lastLineIndex:]
        textSegments.append(finalString)
    #print(textSegments)
        
    return textSegments

if __name__=="__main__":
        
        # variables
        reddit = None
        subreddit = None
        # base elevenLabs API payload no key or voice selected
        payload = copy.deepcopy(elevenlabs_api)
        # set elevenlabs xi api key
        payload["headers"]["xi-api-key"] = elevenlabs_key

        # holds Post instances
        posts_dict = {}

        # create reddit instance
        reddit = praw.Reddit(client_id=Reddit_API["CLIENT_ID"],
                             client_secret=Reddit_API["CLIENT_SECRET"],
                             password=Reddit_API["PASSWORD"],
                             user_agent=Reddit_API["USER_AGENT"],
                             username=Reddit_API["USERNAME"])

        # create subreddit instance
        subreddit = reddit.subreddit("AmItheAsshole")
      
        # function calls
        # get raw posts
        # dict comprehension to create Post class instances
        posts_dict = get_posts(subreddit, MANIFEST_FILE)

        print(posts_dict)

        #TESTING
        #posts_dict = {"1aimqy3":Post(submission=models.Submission(reddit=reddit, id='1aimqy3'))}

        # call to write text
        for key in posts_dict.keys():
            posts_dict[key].run(file_paths, manifestFile=MANIFEST_FILE, payload=payload)