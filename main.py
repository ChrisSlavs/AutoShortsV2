import csv
import elevenlabs
import os
import praw
import subprocess
import re
import copy
import requests
import random as rand
from praw import models
from pathlib import Path
from CONSTANTS import *


from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip

class Post():
    def __init__(self, url:str):
        self.url = url
        self.ID = None
        # final path should be set when final videos are cut, in case there are more than one video
        self.filePaths = {"text": None, "voiceover": None, "subtitles": None,
                          "background": None, "final": []}
    
    # gets all attributes for class not set by instantiation
    def set_attributes(self, redditInstance:praw.Reddit, filePaths:dict):
        self.ID = praw.reddit.Submission(redditInstance, url=self.url).id_from_url(self.url)
        
        # set file paths
        for key in filePaths.keys():
            if os.path.isdir(filePaths[key]):
                match key:
                    case "text":
                        self.filePaths[key] = filePaths[key] + self.ID + ".txt"  
                    case "voiceover":
                        self.filePaths[key] = filePaths[key] + self.ID + ".mp4"  
                    case "subtitles":
                        self.filePaths[key] = filePaths[key] + self.ID + ".srt"  
                    case "background":
                        self.filePaths[key] = filePaths[key] + self.ID + ".mp4"
                    case "final":
                        self.filePaths[key][-1] = filePaths[key] + self.ID + ".mp4"
            else:
                self.filePaths[key] = filePaths[key]
        
        return

        # TODO add check for proper filepath extensions and if paths exist

    # get the submission text and write it to a text file
    def get_text(self, redditInstance:praw.Reddit):
        # local variables
        # get submission text
        text = redditInstance.submission(self.url).selftext

        # sorts submission text and writes to text file
        finalstring = []
        newLineIndex = 0 
        lastLineIndex = 0
        if len(text) <= 50 or str.find(text, " ") == -1:
            file = open(self.filePaths["text"], "x", encoding="utf-8")
            file.write(text)
            file.close()
        
        # will print out text with a new line preceeding it < 50 characters
        # as the newline is treated like any other character not a whitespace
        # text is outputted well enough to not have to fix
        else:
            #split textlength into a multiple of 50
            texlength = int(len(text) / 50) * 50
            
            for i in range(50, texlength, 50):
                newLineIndex = text.find(" ", i)
                finalstring.append(text[lastLineIndex:newLineIndex + 1])
                lastLineIndex = newLineIndex
                i = newLineIndex

        finalstring.append(text[lastLineIndex: -1])
        strippedText = [line.strip() for line in finalstring]
        strippedText = "\n".join(strippedText)

        file = open(self.filePaths["text"], "x", encoding="utf-8")
        file.write(strippedText)
        file.close()
        
        return

    def get_voiceover(self, voiceID:str="hKULXlJp90RYPLVAaOJI"):
        # copy data to add variable data
        payload = copy.deepcopy(elevenlabs_data)
        # add voice ID to request path
        thisUrl = payload["url"] + voiceID
        # request
        with open(self.filePaths["text"], "r") as f:
            payload["data"]["text"] = f.read()
        
        # recieve
        response = requests.post(url=thisUrl, json=payload["data"], headers=payload["headers"])
        with open(self.filePaths["voiceover"], "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return

    def get_srt(self, model:str='base'):
        subprocess.Popen(f"whisper {self.filePaths['voiceover']} {model} --word_timestamps True --max_words_per_line 3 --output_format srt -o {self.filePaths['subtitles']}", shell=True).wait()
        
        return
    
    def burn_final(self, ogBgVideo:str):

        # duration of voice over
        voiceover = AudioClip(self.filePaths["voiceover"])
        voiceoverDuration = voiceover.duration
        voiceover.close()

        #duration of background video
        bgVideo = VideoClip(ogBgVideo)
        bgDuration = bgVideo.duration
        bgVideo.close()

        start = rand.randint(0, int(bgDuration) - int(voiceoverDuration))

        # cut background video
        subprocess.Popen(f"ffmpeg -ss {start} -i {ogBgVideo} -c copy -t {voiceoverDuration} {self.filePaths['background']}")

        # add audio and subtitles
        subprocess.Popen(f"ffmpeg -i {self.filePaths['background']} -i {self.filePaths['voiceover']} -vf 
                         subtitles={self.filePaths['subtitles']}:force_style='FontName=Roboto,Alignment=10,Fontsize=24,OutlineColour=#000000,Outline=1' 
                         -c:v libx264 -c:a aac -strict experimental {self.filePaths['final'][-1]}")

        return
    
    def cut_finals(self):
        # maybe cut video before to preserve quality
        video = VideoClip(self.filePaths["final"][-1])
        duration = video.duration
        video.close()
        
        fileName = ""
        if (duration > 60):
            segmentCount = 0
            multipleCheck = int(video.duration) // 60
            
            for i in range(0, segmentCount):
                fileName = f"{self.filePaths['final'][-1]} Part{i}"
                start = i * 60
                subprocess.Popen(f"ffmpeg -ss {start} -i {self.filePaths['final']} -c copy -t {start + 60} {fileName}")

            if (duration % 60) != 0:
                subprocess.Popen(f"ffmpeg -ss {segmentCount * 60} -i {self.filePaths['final']} -c copy -t {duration % 60} {fileName}")

        return

    def run(self, redditInstance:praw.Reddit, filePaths:dict, ogBgVideo:str, voiceID:str="hKULXlJp90RYPLVAaOJI", model:str="base"):
        self.set_attributes(redditInstance=redditInstance, filePaths=filePaths)
        self.get_text(redditInstance=redditInstance)
        self.get_voiceover(voiceID)
        self.get_srt(model)
        self.burn_final(ogBgVideo=ogBgVideo)
        self.cut_finals()


def init_all(clientID, clientSecret, clientPass, userAgent, clientUser):
    reddit = praw.Reddit(
        client_id=clientID,
        client_secret=clientSecret,
        password=clientPass,
        user_agent=userAgent,
        username=clientUser,
    )

    return reddit