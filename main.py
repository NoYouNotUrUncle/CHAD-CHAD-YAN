import asyncio
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import discord
from discord.ext import commands
from discord_slash import SlashCommand
from discord_slash.utils import manage_commands
import datetime
import json
import re
import html2text
import sys

def jsonFromFile(filePath):
  with open(filePath,"r",encoding="utf8") as file:
    return json.loads(file.read())

#top secret stuff !
settings = jsonFromFile("settings.json")
pw = settings["password"]
username = settings["username"]
token = settings["token"]
#admin ids
admins = settings["admins"]
# server id (singular)
guild_id = settings["guild_id"]

#Stuff Stack Overflow told me to put to stop crashes ¯\_(.-.)_/¯
browser_options = Options()
browser_options.add_argument('--no-sandbox')
browser_options.add_argument('--disable-dev-shm-usage')

#headless !!!
if "headless" in settings and settings["headless"]:
  browser_options.add_argument("headless")

#Data
data = jsonFromFile("data.json")
links = data["links"]
#schedule in 24h clock
times = data["times"]
#channel to ping upon start
pingChannel = data["channel"]

def cache():
  with open("data.json", "w") as file:
    file.write(json.dumps({
      "links": links,
      "times": times,
      "channel": pingChannel
    }))

client = commands.Bot(command_prefix=".", intents=discord.Intents.all()) #get discord
slash = SlashCommand(client, sync_commands=True)

async def msgCh(msg, channel):# send a message to a specific channel id
  messageChannel = client.get_channel(channel)
  await messageChannel.send(msg)

#booleans for whether or not a given period has already been added to queue
finishedPeriods = {}
openClasses = 0 #number of classes in queue
linkQueue = {} #queue of links to be checked by channel id
dropLinks = {} #links to drop if requested
period = {} #what period each channel is in

def resetPeriods(): #set all periods to unprocessed
  global finishedPeriods
  finishedPeriods = {}
  for key in times:
    resetList = []
    for i in range(0,len(times[key])): resetList.append(False)
    finishedPeriods[key] = resetList

resetPeriods()

driver = None #browser driver
async def startDriver(): #start a new driver and log in to gapps
  global driver
  #open chrome
  driver = webdriver.Chrome(options=browser_options)
  driver.set_page_load_timeout(10) #restart driver after 5s of monkeying (cus google block prolly!)
  #go to google.yrdsb.ca and log in
  driver.get("https://google.yrdsb.ca/LoginFormIdentityProvider/Login.aspx?ReturnUrl=%2fLoginFormIdentityProvider%2fDefault.aspx")
  print("at login page")
  await asyncio.sleep(2)
  driver.find_element_by_id("UserName").send_keys(username)
  driver.find_element_by_id("Password").send_keys(pw)
  driver.find_element_by_id("LoginButton").click()
  print("login sent")
  await asyncio.sleep(2)
  if "speedbump" in driver.current_url: #press the continue button
    print("speedbump")
    driver.find_element_by_xpath("//*[@id=\"view_container\"]/div/div/div[2]/div/div[2]/div/div[1]/div/div/button/div[2]").click()
  await asyncio.sleep(3)
  print("finished")

#to tell blocked thread to stop monkeying
end = False

#drop a link from the queue
@slash.slash(
  name="drop",
  description="Drop a link",
  options=[
    manage_commands.create_option(
      name="link",
      description="The Meet code/link or Zoom link to be dropped",
      option_type=3,
      required=True
    )
  ],
  guild_ids=[guild_id]
)
@client.command(name="drop", help="drop a link")
async def dropLink(ctx, link):
  global dropLinks
  global linkQueue
  key = str(ctx.channel.id)
  link = None
  for curLink in linkQueue[key]:
    if curLink[1] == "https://meet.google.com/lookup/" + link:  # link matches code
      link = curLink
  if link is None:
    await ctx.send("Link not found in queue.")
  else:
    dropLinks[key].append(link)
    await ctx.send("dropping link to " + link[2] + "'s class from the queue. (Please allow some time for this to take affect.)")

#get invite link
@slash.slash(
  name="invite",
  description="Get the invite link",
  options=[],
  guild_ids=[guild_id]
)
@client.command(name="invite", help="get an invite link")
async def sendInvite(ctx): # TODO: do not hardcode client id
  await ctx.send("https://discord.com/api/oauth2/authorize?client_id=815267324973023234&permissions=8&scope=bot")

#restart the bot from discord (crashes but its fine kind of ???)
@slash.slash(
  name="restart",
  description="Restart the bot",
  options=[],
  guild_ids=[guild_id]
)
@client.command(name="restart", help="restart bot")
async def restart(ctx):
  global pingChannel
  global admins
  global end
  if ctx.author.id not in admins: #lol
    await ctx.send("Permission denied.")
  else: #restart
    pingChannel["channel"] = str(ctx.channel.id)
    cache()
    await ctx.send("Restarting.")
    #os.startfile(__file__)
    end = True
    quit()
    sys.exit(1)

def linkToString(link, ctx):
  pingRole = "(role not found)"
  for role in ctx.guild.roles:
    if str(role.id) == str(link[0]): pingRole = f"<@&{role.id}>"
  code = link
  if not "zoom.us" in link:
    code = link[1][len(link[1])-10:]
    if code[0] == "/": code = code[1:] #meet code may be only 9 chars long apparently ?
  return f"{pingRole} — {link[2]} — {code}"

#view the bot's queue
@slash.slash(
  name="queue",
  description="View the queue for the current period",
  options=[],
  guild_ids=[guild_id]
)
@client.command(name="queue", help="view queue")
async def viewQueue(ctx, isglobal: bool):
  global linkQueue
  global links
  key = str(ctx.channel.id)
  if key in linkQueue and len(linkQueue[key]) > 0:
    embed = discord.Embed(title="Current queue")
    for link in linkQueue[key]: #add all the links
      embed.description += linkToString(link, ctx) + "\n"
    await ctx.send(embed=embed)
  else: await ctx.send("No queued links.")

#delete a link based on the code given in view link
@slash.slash(
  name="delete",
  description="Remove a link/code",
  options=[
    manage_commands.create_option(
      name="code",
      description="The Meet code/link or Zoom link to be dropped",
      option_type=3,
      required=True
    )
  ],
  guild_ids=[guild_id]
)

@client.command(name="delete", help="Remove a link/code")
async def deleteLink(ctx, code):
  global links
  global dropLinks
  global linkQueue
  key = str(ctx.channel.id)
  period = None
  link = None
  for i in range(4):
    for curLink in links[key][i]:
      if curLink[1] == f"https://meet.google.com/lookup/{code}" or curLink[1] == code: #link matches code
        period = i
        link = curLink
  if period is None: await ctx.send("Link not found in schedule.")
  else:
    links[key][period].remove(link)
    cache()
    await ctx.send(f"removed period {period+1} link to {link[2]}'s class")
    if link in linkQueue[key]:
      dropLinks[key].append(link)
      await ctx.send(f"dropping link to {link[2]}'s class from the queue. (Please allow some time for this to take effect.)")
  
@slash.slash(
  name="setchannel",
  description="Change the general ping channel",
  options=[
    manage_commands.create_option(
      name="channel",
      description="the channel to ping",
      option_type=7,
      required=True
    )
  ]
)
@client.command(name="setchannel", help="Change the general ping channel")
async def changeChannel(ctx, channel: discord.TextChannel):
  global pingChannel
  pingChannel = int(channel)
  await ctx.send(f"Changed channel to {str(channel)}")

#view the current links
@slash.slash(
  name="summary",
  description="Get the list and details of all periods and links",
  options=[],
  guild_ids=[guild_id]
)
@client.command(name="summary", help="view all links set")
async def viewLinks(ctx):
  global times
  key = str(ctx.channel.id)
  if key in links:
    embed = discord.Embed(title="Links")
    for i in range(4):
      #get time in H:MM AM/PM format :lul:
      title = f"Period {i+1} — "
      am = times[key][i][0] <= 12
      if times[key][i][0] == 99: am = None
      if am is None or am: title += str(times[key][i][0])
      else: title += str(times[key][i][0]-12)
      title += ":"
      if len(str(times[key][i][1])) == 1: title += "0"
      title += f"{times[key][i][1]} "
      if am: title += "AM"
      elif am is not None: title += "PM"
      text = "\n".join([linkToString(link, ctx) for link in links[key][i]])
      if text == "" or text is None:
        text = "No classes for this period."
      embed.add_field(name=title, value=text, inline=False)
    await ctx.send(embed=embed)
  else: await ctx.send("No schedule set up in this channel yet.")

#add link command
@slash.slash(
  name="add",
  description="Add a link",
  options=[
    manage_commands.create_option(
      name="link",
      description="The Meet code/link or Zoom link to be dropped",
      option_type=3,
      required=True
    ),
    manage_commands.create_option(
      name="role",
      description="The role to ping on class open",
      option_type=8,
      required=True
    ),
    manage_commands.create_option(
      name="period",
      description="The period to assign the class to",
      option_type=4,
      required=True,
      choices=[1, 2, 3, 4]
    ),
    manage_commands.create_option(
      name="teacher",
      description="The name of the teacher as an identifier",
      option_type=3,
      required=True
    )
  ],
  guild_ids=[guild_id]
)
@client.command(name="add", help="add links")
async def addLink(ctx, link, rolePing: discord.Role, period: int, teacher): # TODO: use string for teacher later during slash command int
  global links
  key = str(ctx.channel.id)
  if re.search(r"^https:\/\/meet.google.com\/lookup\/[a-z0-9]{9,10}$",link) or "zoom.us" in link: #check if the link matches the regex for a meet link
    if period in range(1, 4+1):
      if key in links:
        #add the link
        links[key][period-1].append([str(rolePing.id),link,teacher])
        cache()
        await ctx.send("Added link.")
      #errors
      else: await ctx.send("Set up a schedule for this channel with `set times` before proceeding.")
    else: await ctx.send("Period not in the range 1-4")
  else:
    await ctx.send("Invalid link")

#rotate the periods by sorting their current times and then putting them in the desired order
@slash.slash(
  name="rotate",
  description="Change the order of the periods",
  options=[
    manage_commands.create_option(
      name="first",
      description="The first period",
      option_type=4,
      required=True,
      choices=[1, 2, 3, 4]
    ),
    manage_commands.create_option(
      name="second",
      description="The second period",
      option_type=4,
      required=True,
      choices=[1, 2, 3, 4]
    ),
    manage_commands.create_option(
      name="third",
      description="The third period",
      option_type=4,
      required=True,
      choices=[1, 2, 3, 4]
    ),
    manage_commands.create_option(
      name="fourth",
      description="The fourth period",
      option_type=4,
      required=True,
      choices=[1, 2, 3, 4]
    )
  ],
  guild_ids=[guild_id]
)
@client.command(name="rotate", help="rotate period times")
async def rotate(ctx, first, second, third, fourth):
  global times
  key = str(ctx.channel.id)
  periods = []
  for period in [first, second, third, fourth]: #parse period numbers
    if period.isnumeric(): periods.append(int(period))
  if sorted(periods) == [1,2,3,4]: #check if permutation is valid
    if key in links:
      curTimeOrdered = sorted(times[key]) #sorted list of times currently in use
      for i in range(4): #put them in order
        times[key][periods[i]-1] = curTimeOrdered[i]
      cache()
      await ctx.send("shuffled periods to "+str(periods))
    else:
      await ctx.send("Set up a schedule for this channel with `set times` before proceeding.")

def parseTime(time): #parse time from string (return None if invalid)
  parsedTime = None
  if ":" not in time: return None
  if not time[:time.index(":")].isnumeric(): return None
  else:
    hour = int(time[:time.index(":")])
    if not((1 <= hour <= 24) or hour == 99): return None
    parsedTime = hour
  if time.index(":") == len(time)-1: return None
  if not time[time.index(":")+1:].isnumeric(): return None
  else:
    minute = int(time[time.index(":")+1:])
    if not((0 <= minute <= 59) or minute == 99): return None
    parsedTime = [parsedTime,minute]
  return parsedTime

#set the periods to a given list of times
@slash.slash(
  name="timeset",
  description="Change period start times",
  options=[
    manage_commands.create_option(
      name="first",
      description="The first period start time",
      option_type=3,
      required=True,
    ),
    manage_commands.create_option(
      name="second",
      description="The second period start time",
      option_type=3,
      required=True,
    ),
    manage_commands.create_option(
      name="third",
      description="The third period start time",
      option_type=3,
      required=True,
    ),
    manage_commands.create_option(
      name="fourth",
      description="The fourth period start time",
      option_type=3,
      required=True,
    )
  ],
  guild_ids=[guild_id]
)
@client.command(name="timeset", help="Set period time with a 24h clock")
async def timeset(ctx, time1, time2, time3, time4):
  global times
  global links
  newTimes = []
  for time in [time1, time2, time3, time4]: #parse times
    if parseTime(time) is not None: newTimes.append(parseTime(time))
  if len(newTimes) == 4: #all parses succeeded
    key = str(ctx.channel.id)
    if key not in links: #set up new schedule
      times[key] = [[] for i in range(4)]
      links[key] = [[] for i in range(4)]
    #overwrite schedule
    for i in range(4): times[key][i] = newTimes[i]
    cache()
    await ctx.send(f"set the periods to the times `{' '.join([time1, time2, time3, time4])}`")
  else:
    await ctx.send("Invalid times submitted. Please use HH:mm in 24-hour time.")

async def removeLinks(key):
  global driver
  global openClasses
  lastLink = []
  dropLinks[key].sort()
  for link in dropLinks[key]:  # remove finished links from queue
    if link != lastLink:
      linkQueue[key].remove(link)
      openClasses -= 1
      if openClasses == 0:  # close driver if all done
        driver.close()
        driver = None
      lastLink = link
  dropLinks[key] = []

#main thread - remains blocked until the queue has elements, at which point it works through it
@client.event
async def on_ready():
  await client.change_presence(activity=discord.Game(name="with your timetable"))
  print("logged in !1!!")
  global linkQueue
  global period
  global openClasses
  global driver
  #default
  for key in times:
    period[key] = None #no active period
    linkQueue[key] = [] #channels are empty
    dropLinks[key] = [] #nothing to drop initially

  #block
  while not end:
    now = datetime.datetime.now() #current time

    for key in times: #for each channel
      for i in range(len(times[key])): #for each period
        #if within 2 minutes of period start, and not processed this period yet
        if int(times[key][i][0]) == now.hour and abs(int(times[key][i][1]) - now.minute) <= 5 and (not finishedPeriods[key][i]):
          period[key] = i #set period

          for link in links[key][i]: #add all of this period's link to queue
            print(link)
            linkQueue[key].append(link)
            openClasses += 1
            if driver is None: await startDriver() #if the driver was closed before, start it

          #remove any links leftover from last period
          for link in linkQueue[key]:
            if not (link in links[key][i]): dropLinks[key].append(link)
          await removeLinks(key)

          finishedPeriods[key][i] = True #set this period to processed

    print("picking up the queue")
    for key in linkQueue: #for every channel
      for link in linkQueue[key]: #for every link in the queue
        running = False #default to not open
        if "meet.google.com" in link[1]:
          try:
            driver.get(link[1]) #go to link
            print("loading "+link[1])
            await asyncio.sleep(1)
            #it's open if the link went through
            running = ("Join" in html2text.HTML2Text().handle(driver.page_source)) and ("meet" in driver.current_url)
          except: #if timeout, due to bot detection
            running = False #default to not open
            driver.close() #restart driver
            await startDriver()
            print("ohhh nooo")
        else:
          running = True
        print(running)
        if running:
          dropLinks[key].append(link)
          await msgCh(f"<:pingo:822111531063836712> <@&{link[0]}>, {link[2]} is now online at <{link[1]}>",int(key))
        else: print(link[2]+" ded") #log dead teacher
      await removeLinks(key)

    if openClasses == 0:
      await asyncio.sleep(10) #try to wake up every 10 seconds
      print("zzzz")

print("starting")
client.run(token)