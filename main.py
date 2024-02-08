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
import datetime
import random as rand
from private import *

from praw import models
from CONSTANTS import *
from moviepy.editor import *

# Global Constants
POST_LIMIT = 3
SUBREDDIT = ""
MANIFEST_FILE = "Working/manifest.txt"

# global variable
subtitle_color_weight = 6

class Post():
    def __init__(self, submission:models.Submission=None):
        # final path and voiceover should be set when final videos are cut, in case there are more than one video/mp3
        self.submission = submission
        self.filePaths = {"text": None, "voiceover":{"basename": None, "final": None}, 
                          "subtitles": {'directory':None, 'first':None, 'final':None}, 
                          "background_original":None, "background": None, "final":{"basename":None, "final":None}}

    # gets all attributes for class not set by instantiation
    def set_attributes(self, filePaths:dict):
        print("Setting attributes")
        id = self.submission.id
        
        # set file paths
        for key in filePaths.keys():
            if os.path.isdir(filePaths[key]):
                match key:
                    case "text":
                        self.filePaths[key] = filePaths[key] + id + ".txt"  
                    case "voiceover":
                        self.filePaths[key]["basename"] = filePaths[key] + id + ".mp3" 
                        self.filePaths[key]["final"] = self.filePaths[key]["basename"]
                    case "subtitles":
                        # cant set exact outputfile path due to whisper only accepting folders for output
                        self.filePaths[key]['directory'] = filePaths[key]  
                        self.filePaths[key]['first'] = filePaths[key] + id + ".srt"
                        self.filePaths[key]['final'] = filePaths[key] + id + "MARKED.srt"
                    case "background":
                        self.filePaths[key] = filePaths[key] + id + ".mp4"
                    case "background_original":
                        self.filePaths[key] = filePaths[key]
                    case "final":
                        self.filePaths[key]['basename'] = filePaths[key] + id + ".mp4"
                        self.filePaths[key]['final'] = self.filePaths[key]['basename']
                    case _:
                        continue
            else:
                self.filePaths[key] = filePaths[key]
        return

    # get the submission text and write it to a text file
    def get_text(self):
        print("Getting submission text")
        # local variables
        text = ""
        finalString = ""
        sortedString = []
        # get submission text
        text = self.submission.selftext
        text = re.sub(regex["NON_ASCII"], "", text)  
        text = re.sub(regex['AITA'], f'"A" "I" "T" "A"', text)      
        # sorts submission text and writes to text file
        sortedString = split_text(text, 50, 50)
        finalString = "\n".join(sortedString)
        
        file = open(self.filePaths["text"], "w", encoding="utf-8")
        file.write(finalString)
        file.close()
        
        return

    def get_voiceover(self, payload:dict, voiceID:str="hKULXlJp90RYPLVAaOJI"):
        """
        Requests to elevenlabs api are not sent directly inside get_text() method
        due to the need for manual error checking within the text itself
        """
        print("Getting voiceover")

        # local variables
        thisUrl = ""
        #create chunks of text ~2500 char in length
        stringPayload = [] 
        concatFile = ""
        # add voice ID to url
        thisUrl = payload["url"] + voiceID
        
        with open(self.filePaths["text"], "r", encoding="utf-8") as f:
            text = f.read()
            stringPayload = split_text(text, 2500, 2500)
        
        # request
        
        for i, seg in enumerate(stringPayload):
            self.filePaths["voiceover"][str(i)] = f"{self.filePaths['voiceover']['basename'][:-4]}PART{str(i)}.mp3"
            payload["data"]["text"] = stringPayload[i]
            response = requests.post(url=thisUrl, json=payload["data"], headers=payload["headers"])
            with open(self.filePaths["voiceover"][str(i)], "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

        # set final name for spliced voiceover
        # could just use basename, but both elements serve different purposes, improves readability
        if len(self.filePaths['voiceover']) > 3:
            concatFile = f"{os.path.dirname(self.filePaths['voiceover']['basename'])}/{self.submission.id}concat.txt" 
            
            # write names of voiceovers to file for ffmpeg concat
            with open(f"{concatFile}", "w") as f:
                for i in range(0, len(self.filePaths['voiceover']) - 2):
                    f.write(f"file 'file:{os.path.abspath(self.filePaths['voiceover'][str(i)])}'\n")
        
            # concatenate each voiceover segment recieved if more than one
            subprocess.Popen(f"ffmpeg -f concat -safe 0 -i {concatFile} -c copy {self.filePaths['voiceover']['final']}", shell=True).wait()

            # for safety using checks
            for i in range(0, len(self.filePaths['voiceover']) - 2):
                if check_if_file_exists(self.filePaths['voiceover'][str(i)]):
                    os.remove(self.filePaths['voiceover'][str(i)])
                else:
                    print(f"Error: file {self.filePaths['voiceover']['basename'][:-4]}PART{str(i)}.mp3 does not  exist. skipping.")
                    continue
            if check_if_file_exists(concatFile):
                os.remove(concatFile)
            else:
                print(f"Error: file {concatFile} does not exists. skipping")
        
        # if only one voiceover segment is sent back
        else:
            os.rename(self.filePaths['voiceover']['0'], self.filePaths['voiceover']['final'])

        return

    def get_srt(self, model:str='base'):
        print("Getting srt")
        # whipser cmd to get srt
        subprocess.Popen(f"whisper {self.filePaths['voiceover']['final']} --model {model} --word_timestamps True --max_words_per_line 3 --output_format srt -o {self.filePaths['subtitles']['directory']}", shell=True).wait()

        return

    def markup_srt(self, color:str="yellow"):
        print("Marking up srt")
        global subtitle_color_weight        
        # local variables
        markup = f'<font color="{color}">'
        lines = []
        randStrIndex = 0
        strList = []
        coin = 0
        # open SRT
        with open(self.filePaths['subtitles']['first'], 'r') as f:
            lines = [line for line in f]
            
            # srt is formatted with a new subtitle every 4 lines, starting at index two if indexed in python list
        for i in range(2, len(lines), 4):
            # check if there is more than one space before doing coin toss
            if lines[i].count(" ") >= 2:
                # choose if line will have a color word
                coin = rand.randint(0, subtitle_color_weight)
                if (coin == subtitle_color_weight):
                    lines[i] = lines[i].strip()
                    strList = lines[i].split(" ")
                    randStrIndex = rand.randint(0, len(strList) - 1)
                    # if index chosen is the last index of strList
                    if (randStrIndex == len(strList) - 1):
                        strList.insert(randStrIndex, markup)
                        strList.append("</font>")
                        strList.append("\n")
                        lines[i] = " ".join(strList)
                    else:
                        # if index is not last index
                        strList.insert(randStrIndex, markup)
                        strList.insert(randStrIndex + 2, "</font>")
                        strList.append("\n")
                        lines[i] = " ".join(strList)

            # will always add markup to subtitles that are one word
            elif (lines[i].count(" ") == 0 and lines[i] != lines[-1]):
                stripped = lines[i].strip()
                strList = stripped.split(" ")
                strList.insert(0, markup)
                strList.append("</font>")
                strList.append("\n")
                lines[i] = " ".join(strList)

        # write new lines lsit to srt file
        with open(self.filePaths['subtitles']['final'], 'w') as f:
            for line in lines:
                f.write(line)

        if check_if_file_exists(self.filePaths['subtitles']['first']):
           os.remove(self.filePaths['subtitles']['first'])

        return
             
    def burn_final(self, vidCodec:str="libx264"):  
        print("Creating final")
        # duration of voice over
        voiceover = AudioFileClip(self.filePaths["voiceover"]['final'])
        voiceoverDuration = voiceover.duration
        voiceover.close()

        if not os.path.exists(self.filePaths['final']['final']) and not os.path.isfile(self.filePaths['final']['final']):
              #duration of background video
            bgVideo = VideoFileClip(self.filePaths["background_original"])
            bgDuration = bgVideo.duration
            bgVideo.close()
            start = rand.randint(0, int(bgDuration) - int(voiceoverDuration))
            # cut background video
            subprocess.Popen(f"ffmpeg -ss {start} -i {self.filePaths['background_original']} -force_key_frames expr:gte(t,n_forced*60) -c copy -t {voiceoverDuration + 2} {self.filePaths['background']}").wait()

        # add audio and subtitles        
        subprocess.Popen(f"ffmpeg -i {self.filePaths['background']} -i {self.filePaths['voiceover']['final']} -force_key_frames expr:gte(t,n_forced*60) -vf subtitles={self.filePaths['subtitles']['final']}:force_style='FontName=Roboto,Alignment=10,Fontsize=36,OutlineColour=#000000,Outline=1' -c:v {vidCodec} -c:a aac -strict experimental -map 0:v -map 1:a {self.filePaths['final']['final']}").wait()

        if os.path.exists(self.filePaths['background']) and os.path.isfile(self.filePaths['background']):
            os.remove(self.filePaths['background'])

        return
    
    def cut_finals(self):
        print("Cutting final segments")
        # maybe cut video before to preserve quality
        video = VideoFileClip(self.filePaths["final"]["basename"])
        duration = video.duration
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
        print("Writing submission ID to manifest")
        with open(manifestFile, "a") as f:
            f.write(f"{self.submission.id}\n")
        
        return
            
    def run_text(self, filePaths:dict, payload:dict, voiceID:str="hKULXlJp90RYPLVAaOJI", model:str="base"):
        self.set_attributes(filePaths=filePaths)
        if not check_if_file_exists(self.filePaths['text']):
            self.get_text()
        if not check_if_file_exists(self.filePaths['voiceover']['final']):
            self.get_voiceover(payload, voiceID)
        if not check_if_file_exists(self.filePaths['subtitles']['first']) and not check_if_file_exists(self.filePaths['subtitles']['final']):
            self.get_srt(model)
        if not check_if_file_exists(self.filePaths['subtitles']['final']):
            self.markup_srt()
        # always cut finals, not a way to check for efficiently as chopping each segment takes < 1 second
    
    def run_video(self, manifestFile:str, vidCodec:str="libx264"):
        print("Please check text files for correctness before cutting videos.\n")
        print("Inputting 4 into console will continue.\n")
        x = 0
        while x != 4:
            x = input()
                  
        if not check_if_file_exists(self.filePaths['final']['final']):
            self.burn_final(vidCodec=vidCodec)
        self.cut_finals()
        self.write_manifest(manifestFile=manifestFile)

        print(f"Finished. ID: {self.submission.id}")

        return

def check_if_file_exists(file:str) -> bool:
    check = False
    # two checks, extra safe idk? check for file first for small speed gains
    if os.path.isfile(file) and os.path.exists(file):
        check = True
    
    return check
    
def check_manifest(manifestFile, submissionID:str) -> bool:
    # return variable
    check = True
    with open(manifestFile, "r") as f:
        for line in f:
            if submissionID in line.strip():
                check = False

    return check 

def get_posts(subreddit:models.Subreddit, manifestFile:str, modManifest:str) -> dict:
    global POST_LIMIT
    # return Dictionary
    posts = {}
    # Key = submission ID Value = Instance of post class wrapping Submission
    lines = []
    with open(modManifest, "r") as f:
        modList = [line.strip() for line in f]

    posts = {f"{submission.id}":Post(submission=submission) for submission in subreddit.hot(limit=POST_LIMIT) 
              if (check_manifest(manifestFile=manifestFile, submissionID=submission.id) and submission.author not in modList)}
    
    return posts

def split_text(text:str, lenCheck:int, iterLen:int) -> list:
    lastLineIndex = 0
    textLength = 0    
    #return varibale
    lineSegments = []
    # elevenlabs api only accepts 2500 characters at once
    # TODO probably dont need if statement and can just leave it as the for statement
    textLength = len(text)
    if textLength > lenCheck:
        for i in range(iterLen, textLength, iterLen):
            i = text.rfind(" ", lastLineIndex, i)
            lineSegments.append(text[lastLineIndex:i].strip())
            lastLineIndex = i
            
    lineSegments.append(text[lastLineIndex:].strip())

    return lineSegments

# create list of mods for subreddits, used for filtering posts
def list_mods(subreddit:models.Subreddit, mod_manifest:str):
    # local constants
    DATE_CHECK = 15
    # local variables
    # mod list manifest
    mods = []
    updatedMods = ""
    fileCheck = False
    dateDelta = 0
    currentDate = 0

    fileCheck = check_if_file_exists(mod_manifest)
    currentDate = datetime.date.today()
    if fileCheck:
        fileDate = []
        previousDate = 0
        dateDelta = 0
        with open(mod_manifest, "r") as f:
            lines = f.readlines()
        # split last date to list
        fileDate = lines[1].strip().split('-')
        # convert days to int from str
        fileDate = [int(d) for d in fileDate]
        # turn into a datetime.date class
        previousDate = datetime.date(fileDate[0], fileDate[1], fileDate[2])
        
        dateDelta = (currentDate - previousDate).days
    
    if dateDelta >= DATE_CHECK or not fileCheck: 
        for mod in subreddit.moderator():
            mods.append(str(mod))
            updatedMods = "\n".join(mods)

        with open(mod_manifest, "w") as f:
            f.write(f"Last Update\n{str(currentDate)}\n\n")
            f.write(updatedMods)
    
    return

if __name__=="__main__":
        
        ########## EDIT HERE #########
        user_data = {"elevenlabs_api_key"   :elevenlabs_key,
                     "elevenlabs_voice_ID"  :elevenlabs_api['voices']['Alex'],
                     "reddit_client_id"     :Reddit_API["CLIENT_ID"],
                     "reddit_client_secret" :Reddit_API["CLIENT_SECRET"],
                     "reddit_password"      :Reddit_API["PASSWORD"],
                     "reddit_user_agent"    :Reddit_API["USER_AGENT"],
                     "reddit_username"      :Reddit_API["USERNAME"],
                     "subreddit"            :"AmItheAsshole",
                     "subtitle_color_weight":6,
                     "subtitle_color"       :"yellow",
                     "ffmpeg_vid_codec"     :"libx264",
                     "whisperai_model"      :"base",
                     "working_file_paths"   :file_paths}
        
        
        ########## INIT ##########
        # variables
        reddit = None
        subreddit = None
        posts_dict = {}
        # base elevenLabs API payload no key or voice selected
        payload = copy.deepcopy(elevenlabs_api)
        # set elevenlabs xi api key
        payload["headers"]["xi-api-key"] = user_data["elevenlabs_api_key"]
        # create reddit instance
        reddit = praw.Reddit(client_id=user_data["reddit_client_id"],
                             client_secret=user_data["reddit_client_secret"],
                             password=user_data["reddit_password"],
                             user_agent=user_data["reddit_user_agent"],
                             username=user_data["reddit_username"])

        # create subreddit instance
        subreddit = reddit.subreddit(user_data["subreddit"])
        mod_manifest = f"{user_data['working_file_paths']['mod_manifest']}{subreddit.fullname}.txt"
        list_mods(subreddit, mod_manifest)

        ########## INIT END ##########

        # function calls
        # get raw posts
        # dict comprehension to create Post class instances
        posts_dict = get_posts(subreddit, MANIFEST_FILE, 
                                f"{user_data['working_file_paths']['mod_manifest']}{subreddit.fullname}.txt")
        
        for val in posts_dict.values():
            print(val.submission.id)

        # call to write text
        for key in posts_dict.keys():
            posts_dict[key].run_text(user_data["working_file_paths"], 
                                     payload=payload, 
                                     voiceID=user_data["elevenlabs_voice_ID"], 
                                     model=user_data["whisperai_model"])

        for key in posts_dict.keys():
            posts_dict[key].run_video(manifestFile=MANIFEST_FILE,
                                      vidCodec=user_data["ffmpeg_vid_codec"])