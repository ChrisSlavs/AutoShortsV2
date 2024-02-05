# AutoShortsV2
Remake of a previous video automation script I have made

# Why do this???
Well I was very unsatisfied with the spaghetti, procedural style programming used to make the first version. 
As I have become more familiar and worked out the kinks with the tools used in the script (ffmpeg, various ai tools) 
I feel this deserves a rewrite.

## Goals:
More object oriented style programming, preferably a mix of procedural and OOP
Color formatting of subtitles


## TODO
~~Create file structure~~\
test and debug\
write used post id to a manifest\
~~split text into 2500 char or less~~\
~~recieve multiple voiceovers from elevenlabs and handle output~~\
~~splice together elevenlabs api voiceovers after recieving all of them~~\
delete files used for splicing\
add non voiceover ending to video\


## Possible TODO
add title reading intro

## Limitations
Extending the classes of PRAW models does not work in many cases due to its own internal structure,
Therefore it is best to wrap any classes to extend their funtionality.

### Changes
Ver 3:
Added elevenlabs support\
Fixed video freezing issue\
Added checks to remove non-ASCII char from texts\
general clean up