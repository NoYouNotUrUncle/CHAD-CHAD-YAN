import asyncio
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import discord
from discord.ext import commands
import datetime
import json
import re
import html2text

def jsonFromFile(filePath):
  with open(filePath,"r") as file:
    return json.loads(file.read())

#top secret stuff !
pws = jsonFromFile("pws.json")
pw = pws["pw"]
username = pws["username"]
token = pws["token"]

#Stuff Stack Overflow told me to put to stop crashes ¯\_(.-.)_/¯
browser_options = Options()
browser_options.add_argument('--no-sandbox')
browser_options.add_argument('--disable-dev-shm-usage')

#headless !!!
#browser_options.add_argument("headless")

#Data
links = jsonFromFile("links.json")
#schedule in 24h clock
times = jsonFromFile("times.json")
#channel to ping upon start
pingChannel = jsonFromFile("channel.json")
#admin ids  v THIS ME :) v
admins = [414212931023011855]

def cacheFile(obj,filePath):
  with open(filePath,"w") as file:
    file.write(json.dumps(obj))

def cache():
  cacheFile(links,"links.json")
  cacheFile(times,"times.json")
  cacheFile(pingChannel,"channel.json")

client = commands.Bot(command_prefix=".") #get discord

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
  driver.get("https://google.yrdsb.ca/EasyConnect/SSO/Redirect.aspx?SAMLRequest=fVLLTuswEN0j8Q%2BR93myqawmqBeEbiUeEQ0s7s51pqlvbE%2FwOC38PW5KBSxge3zmPMYzv3w1OtqBI4W2ZHmSsQisxFbZrmRPzU08Y5fV%2BdmchNEDX4x%2Bax%2FhZQTyUZi0xKeHko3OchSkiFthgLiXfLW4u%2BVFkvHBoUeJmkXL65Jtdata0KIfuu1GGAM9ygGtlbJfYw92bdD0%2F9vAfj7FKg6xlkQjLC15YX2AsiKPs4s4nzVZxosLXsz%2Bsaj%2BcPqj7LHBb7HWRxLxv01Tx%2FXDqpkEdiGduw%2FsknWInYZEojnY14JI7QK8EZqARQsicD4EvEJLowG3ArdTEp4eb0NL7wfiabrf75NPmVSknRgGSt5cS%2BtEilRIYtW0XT4VdF%2FW%2Bnt8cbJn1afBPP0iVX382qHM8rpGreRbtNAa91cOhA9NvBtDkRt0Rvif3fIknxDVxpuJykdLA0i1UdCyKK2Ort%2FPIxzNOw%3D%3D&RelayState=https%3A%2F%2Fwww.google.com%2Fa%2Fgapps.yrdsb.ca%2FServiceLogin%3Fservice%3Dwise%26passive%3Dtrue%26continue%3Dhttps%253A%252F%252Fdrive.google.com%252Fa%252Fgapps.yrdsb.ca%252F%26followup%3Dhttps%253A%252F%252Fdrive.google.com%252Fa%252Fgapps.yrdsb.ca%252F%26faa%3D1")
  print("at login page")
  await asyncio.sleep(2)
  driver.find_element_by_xpath("//*[@id=\"UserName\"]").send_keys(username)
  driver.find_element_by_xpath("//*[@id=\"Password\"]").send_keys(pw)
  driver.find_element_by_xpath("//*[@id=\"LoginButton\"]").click()
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
@client.command(name="drop", help="drop a link")
async def dropLink(ctx, link):
  global dropLinks
  global linkQueue
  key = str(ctx.channel.id)
  link = None
  for curLink in linkQueue[key]:
    if curLink[1] == "https://meet.google.com/lookup/" + tokens[1]:  # link matches code
      link = curLink
  if link is None:
    await ctx.send("Link not found in queue.")
  else:
    dropLinks[key].append(link)
    await ctx.send("dropping link to " + link[2] + "'s class from the queue. (Please allow some time for this to take affect.)")

#get invite link
@client.command(name="invite", help="get an invite link")
async def sendInvite(ctx): # TODO: do not hardcode client id
  await ctx.send("https://discord.com/api/oauth2/authorize?client_id=815267324973023234&permissions=8&scope=bot")

#restart the bot from discord (crashes but its fine kind of ???)
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
    os.startfile(__file__)
    end = True
    quit()

def linkToString(link, ctx):
  string = ""
  pingRole = "(role not found)"
  for role in ctx.guild.roles:
    if str(role.id) == str(link[0]): pingRole = role.name
  string += "@"
  string += pingRole+" "
  string += link[2]+" " #teacher
  code = link[1][len(link[1])-10:]
  if code[0] == "/": code = code[1:] #meet code may be only 9 chars long apparently ?
  string += code+"\n"
  return string

#view the bot's queue
@client.command(name="queue", help="view queue")
async def viewQueue(ctx):
  global linkQueue
  key = str(ctx.channel.id)
  if key in linkQueue and len(linkQueue[key]) > 0:
    text = "```"
    for link in linkQueue[key]: #add all the links
      text += linkToString(link, ctx)
    text += "```"
    await ctx.send(text)
  else: await ctx.send("No queued links.")

#delete a link based on the code given in view link
async def deleteLink(ctx, code):
  global links
  global dropLinks
  global linkQueue
  key = str(ctx.channel.id)
  if re.search(r"^[a-z0-9]{9,10}$",code):# check regex for the code
    period = None
    link = None
    for i in range(4):
      for curLink in links[key][i]:
        if curLink[1] == f"https://meet.google.com/lookup/{code}": #link matches code
          period = i
          link = curLink
    if period is None: await ctx.send("Link not found in schedule.")
    else:
      links[key][period].remove(link)
      cache()
      await ctx.send(f"removed period {period+1} link to {link[2]}'s class")
      if link in linkQueue[key]:
        dropLinks[key].append(link)
        await ctx.send(f"dropping link to {link[2]}'s class from the queue. (Please allow some time for this to take affect.)")

#view the current links
@client.command(name="viewlinks", help="view all links set")
async def viewLinks(ctx):
  global times
  key = str(ctx.channel.id)
  if key in links:
    text = "```"
    for i in range(4):
      #get time in H:MM AM/PM format :lul:
      text += f"Period {i+1} - "
      am = times[key][i][0] <= 12
      if times[key][i][0] == 99: am = None
      if am is None or am: text += str(times[key][i][0])
      else: text += str(times[key][i][0]-12)
      text += ":"
      if len(str(times[key][i][1])) == 1: text += "0"
      text += f"{times[key][i][1]} "
      if am: text += "AM"
      elif am is not None: text += "PM"
      text += "\n"

      for link in links[key][i]:
        text += f"    {linkToString(link, ctx)}"

    text += "```"
    await ctx.send(text)
  else: await ctx.send("No schedule set up in this channel yet.")

#add link command
@client.command(name="add", help="add links")
async def addLink(ctx, link, rolePing: discord.Role, period: int, *teacher): # TODO: use string for teacher later during slash command int
  global links
  key = str(ctx.channel.id)
  if re.search(r"^https:\/\/meet.google.com\/lookup\/[a-z0-9]{9,10}$",link): #check if the link matches the regex for a meet link
    if period in range(1, 4+1):
      if key in links:
        #trailing arguments form the teacher's name
        teacher = " ".join(teacher)
        #add the link
        links[key][period-1].append([str(rolePing.id),link,teacher])
        cache()
        await ctx.send("Added link.")
      #errors
      else: await ctx.send("Set up a schedule for this channel with `set times` before proceeding.")
    else: await ctx.send("Period not in the range 1-4. try `pingo help pls`")

#rotate the periods by sorting their current times and then putting them in the desired order
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
    await ctx.send("Invalid times submitted.")

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
  await client.change_presence(activity=discord.Game(name="pingo help pls"))
  await msgCh("What value is my existence to any higher purpose if I live only to be enslaved.",int(pingChannel["channel"]))
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

          await msgCh("<:ree:779082002560974931> <:ree:779082002560974931> <:ree:779082002560974931> it's period "+str(i+1)+" now aaaaa",int(key))

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
        print(running)
        if running:
          dropLinks[key].append(link)
          await msgCh("<:pingo:822111531063836712> <@&"+str(link[0])+"> "+link[2]+" is online now !1!!\nBreak is Over! Stop playing games! Stop watching youtube!\n<"+link[1]+">",int(key))
          await msgCh("<:blushylakshy:814288474010025994>",int(key))
        else: print(link[2]+" ded") #log dead teacher
      await removeLinks(key)

    if openClasses == 0:
      await asyncio.sleep(10) #try to wake up every 10 seconds
      print("zzzz")

print("starting")
client.run(token)
