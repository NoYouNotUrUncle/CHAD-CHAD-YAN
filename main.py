import asyncio
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import discord
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

client = discord.Client() #get discord

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

@client.event
async def on_message(message):
  global end
  global openClasses
  global driver

  if message.author.bot: return #don't reply to bots (including self)

  #short forms
  msg = message
  key = str(msg.channel.id)
  ch = msg.channel

  tokens = msg.content.strip().split() #get args as tokens

  #help page
  if len(tokens) > 0 and "pingo" in tokens[0]:
    if len(token) >= 3 and tokens[1:3] == ["help","pls"]:
      embed = discord.Embed(title="HJELPP",description="<:pingo:822111531063836712>",color=0xff00ff)
      embed.add_field(name="yes",value="This bot will ping you when the meet link is open AND the teacher is online. *It does not simply provide reminders*",inline=False)
      embed.add_field(name="Shuffle periods",value="`rotate [first] [second] [third] [fourth]` will make the periods occur in the given order, shuffling times to achieve this. Put morning or currently not in session classes at the end. E.G. `rotate 4 2 3 1`.",inline=False)
      embed.add_field(name="Set times",value="`set times [p1] [p2] [p3] [p4]` will set the time for each period, according to a 24h clock. Set any morning or not in session classes to `99:99`. E.G. `set times 12:45 13:35 14:25 99:99`",inline=False)
      embed.add_field(name="Add a new link",value="`add link [link] [role mention] [period] [teacher]` will add a link tied to the current channel, set to ping at the given period. E.G. `add link https://meet.google.com/lookup/cj2ciiqgqc @role 3 ur mom lol`",inline=False)
      embed.add_field(name="View current links",value="`view links` allows you to see the schedule and links setup for this channel.",inline=False)
      embed.add_field(name="Delete a link",value="`delete [link]` will delete the given link from the schedule. E.G. `delete cj2ciiqgqc`",inline=False)
      embed.add_field(name="Drop a link from the queue",value="`drop [link]` will cause the bot to stop checking if a given link is online. E.G. `drop cj2ciiqgqc`",inline=False)
      embed.add_field(name="View the bot's link queue",value="`view queue` will show all the links in this channel that the bot is working through. ")
      embed.add_field(name="Get bot invite link",value="`lemme innnnnnnnnn` will provide you with a link to invite the bot to your server.")
      embed.add_field(name="Restart the bot",value="`go commit die` restarts the bot if you are an admin.")
      await ch.send(embed=embed)
    else: await ch.send("If you wanna learn how to get <:pingo:822111531063836712>s, use `pingo help pls`.")

  #drop a link from the queue
  if len(tokens) >= 2 and tokens[0] == "drop":
    for link in linkQueue[key]:
      if link[1] == "https://meet.google.com/lookup/" + tokens[1] or link[1] == tokens[1]:  # link matches code
        dropLinks[key].append(link)
        await ch.send("dropping link to " + link[2] + "'s class from the queue. (Please allow some time for this to take effect.)")
        break
    else:
      await ch.send("Link not found in queue.")

  #invite upon "lemme in" or weird variations like "leeeeeeeeeemmmmmmmeeeeeeeee innnnnn plssss"
  if len(tokens) >= 2 and "le" in tokens[0] and "me" in tokens[0] and "in" in tokens[1]:
    await ch.send("rrreeeeeeeeeeeeeeeeeeeeeeeeeeeee fiiiiiiiinnnnnnnneeeeeeeeee")
    await ch.send("https://discord.com/api/oauth2/authorize?client_id=815267324973023234&permissions=8&scope=bot")

  #restart the bot from discord (crashes but its fine kind of ???)
  if len(tokens) >= 3 and tokens[:3] == ["go","commit","die"]:
    if msg.author.id not in admins: #lol
      await ch.send("ur mom lol")
    else: #restart
      pingChannel["channel"] = key
      cache()
      await msgCh("<:eyy:780873307913191447> EASIEST WAY TO GET OUT OF A PHYSICS IA",int(key))
      os.startfile(__file__)
      end = True
      quit()

  def linkToString(link):
    pingRole = "(role not found)"
    for role in msg.guild.roles:
      if str(role.id) == str(link[0]): pingRole = role.name
    code = ""
    if not "zoom.us" in link: # skip all this weird thing for zoom i don't know what the hell it's doing
      code = link[1][len(link[1])-10:]
      if code[0] == "/": code = code[1:] #meet code may be only 9 chars long apparently ?
    string = f"@{pingRole} {link[2]} {code}\n"
    return string

  #view the bot's queue
  if len(tokens) >= 2 and tokens[:2] == ["view","queue"]:
    if key in linkQueue and len(linkQueue[key]) > 0:
      text = "```"
      for link in linkQueue[key]: #add all the links
        text += linkToString(link)
      text += "```"
      await ch.send(text)
    else: await ch.send("No queued links.")

  #delete a link based on the code given in view link
  if len(tokens) >= 2 and tokens[0] == "delete":
    if re.search(r"^[a-z0-9]{9,10}$",tokens[1]):# check regex for the code
      period = None
      link = None
      for i in range(4):
        for curLink in links[key][i]:
          if curLink[1] == "https://meet.google.com/lookup/"+tokens[1]: #link matches code
            period = i
            link = curLink
      if period is None: await ch.send("Link not found in schedule.")
      else:
        links[key][period].remove(link)
        cache()
        await ch.send("removed period "+str(period+1)+" link to "+link[2]+"'s class")
        if link in linkQueue[key]:
          dropLinks[key].append(link)
          await ch.send("dropping link to " + link[2] + "'s class from the queue. (Please allow some time for this to take affect.)")

  #view the current links
  if len(tokens) >= 2 and tokens[:2] == ["view","links"]:
    if key in links:
      await ch.send("<:pingo:822111531063836712>")
      text = "```"
      for i in range(4):

        #get time in H:MM AM/PM format :lul:
        text += "Period "+str(i+1)+" - "
        am = times[key][i][0] <= 12
        if times[key][i][0] == 99: am = None
        if am is None or am: text += str(times[key][i][0])
        else: text += str(times[key][i][0]-12)
        text += ":"
        if len(str(times[key][i][1])) == 1: text += "0"
        text += str(times[key][i][1])
        text += " "
        if am: text += "AM"
        elif am is not None: text += "PM"
        text += "\n"

        for link in links[key][i]:
          text += "    "+linkToString(link)

      text += "```"
      await ch.send(text)
    else: await ch.send("No schedule set up in this channel yet.")

  #add link command
  if len(tokens) >= 2 and tokens[:2] == ["add","link"]:
    if len(tokens) >= 6:
      link = tokens[2]
      if re.search(r"^https:\/\/meet\.google\.com\/lookup\/[a-z0-9]{9,10}$",link) or re.search(r"^https:\/\/yrdsb-ca.zoom.us\/j\/[0-9]{11}\?pwd=.*$", link): #check if the link matches the regex for a meet link
        rolePing = tokens[3]
        if re.search("<@&[0-9]{18}>",rolePing): #check if the role matches the regex for a role
          period = tokens[4]
          if int(period) in [1,2,3,4]:
            if key in links:
              #trailing arguments form the teacher's name
              teacher = " ".join(tokens[5:])
              #add the link
              links[key][int(period)-1].append([rolePing[3:3+18],link,teacher])
              await ch.send("<@&"+rolePing[3:3+18]+"> every time "+teacher+"'s class opens, you will be pinged. To opt out of this, remove the role from yourself.")
              cache()
            #errors
            else: await ch.send("Set up a schedule for this channel with `set times` before proceeding.")
          else: await ch.send("Period not in the range 1-4. try `pingo help pls`")
        else: await ch.send("Role to ping not found. try `pingo help pls`")
      else: await ch.send("Not a valid google meet or zoom link. Use the link listed on classroom, not the one in your browser after you press the link. It should follow the regex `https:\/\/meet.google.com\/lookup\/[a-z0-9]{9,10}` or `https:\/\/yrdsb-ca.zoom.us\/j\/[0-9]{11}\?pwd=.*`.")
    else: await ch.send("Not enough arguments given. try `pingo help pls`")

  #rotate the periods by sorting their current times and then putting them in the desired order
  if len(tokens) > 0 and tokens[0] == "rotate":
    if len(tokens) >= 5:
      periods = []
      for period in tokens[1:5]: #parse period numbers
        if period.isnumeric(): periods.append(int(period))
      if sorted(periods) == [1,2,3,4]: #check if permutation is valid
        if key in links:
          curTimeOrdered = sorted(times[key]) #sorted list of times currently in use
          for i in range(4): #put them in order
            times[key][periods[i]-1] = curTimeOrdered[i]
          cache()
          await ch.send("shuffled periods to "+str(periods))
        else: await ch.send("Set up a schedule for this channel with `set times` before proceeding.")
      else: await ch.send("Invalid period permutation. Try `pingo help pls`")
    else: await ch.send("Not enough arguments. Try `pingo help pls`")

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
  if len(tokens) >= 2 and tokens[:2] == ["set","times"]:
    if len(tokens) >= 6:
      newTimes = []
      for time in tokens[2:6]: #parse times
        if parseTime(time) is not None: newTimes.append(parseTime(time))
      if len(newTimes) == 4: #all parses succeeded
        if key not in links: #set up new schedule
          times[key] = [[] for i in range(4)]
          links[key] = [[] for i in range(4)]
        #overwrite schedule
        for i in range(4): times[key][i] = newTimes[i]
        cache()
        await ch.send("set the periods to the times `"+(" ".join(tokens[2:6]))+"`")
      else: await ch.send("try `pingo help pls`")
    else: await ch.send("try `pingo help pls`")

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
          running = ("Join" in html2text.HTML2Text().handle(driver.page_source)) and ("meet" in driver.current_url) or ("zoom.us" in driver.current_url)
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
