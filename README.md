# BREAK IS OVER
## STOP PLAYING GAMES
### STOP WATCHING YOUTUBE
Discord bot that will check if a google meet link is open and teacher is online before pinging.

Currently only works in yrdsb. This may be modified by changing the *startDriver* function

*This bot does not simply remind you when class is about to start. It checks if the teacher is online and you are able to join the room.*

## Setup

Install [chrome driver](https://chromedriver.chromium.org/) and add it to your PATH

Download `main.py` and the provided sample `.json` files and put them in the same directory. 

In `pws.json`, change the `username` field to your yrdsb student id, the `pw` field to your yrdsb password, and the `token` field to your discord bot token. 

Copy the channel id of some channel you want the bot to initially message upon start up, and put it under the `channel` field in `channel.json`. 

Run `main.py`, and the bot should be ready to go. 

Use `pingo help pls` to access the help menu. 
