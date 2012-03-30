#Andrew Hawker
#LovejoyBot Rev 0.3
#Purpose: Scrape scheduling information from Lovejoy.nmu.edu for the purposes of sending information.
#TODO: Bug fixes, employee listing...
#Last Updated: Jan 29th, 2009
import time, getpass, mechanize, logging
from toc import TocTalk, BotManager
import re, time, operator

logging.basicConfig(filename="log.txt",level=logging.DEBUG)
#class LJ: Contains all of methods required for connecting, scraping and parsing scheduling information from Lovejoy.nmu.edu
class LJ:
	def __init__(self, sn, pw):
		self.sn = sn
		self.pw = pw
		logging.info(time.asctime() + " Compiling regex...")
		self.shifts = re.compile('<td.*?\n+.*?\n+.*?</td>', re.IGNORECASE)
		self.id = re.compile('_(\d)_(\d\d?)_(\d)', re.IGNORECASE)
		self.openHour = re.compile('take\[(\d)\]\[(\d\d?)\]\[(\d)\]\[(\d)\].*<font\s+color\s?=\s?red>(?:<b>)?(.*?)</[a-b]?>', re.IGNORECASE)

#def connect: Using the mechanize module, connect to Lovejoy, submit login form and follow the 'View Schedule' link.
	def connect(self):
		self.b = mechanize.Browser()
		logging.info(time.asctime() + " Opening Lovejoy.nmu.edu")
		self.b.open("http://lovejoy.nmu.edu/")
		self.b.select_form(name="login")
		logging.info(time.asctime() + " Submitting login form...")
		self.b["username"] = self.sn
		self.b["password"] = self.pw
		self.b.submit()
		logging.info(time.asctime() + " Form submitted.")
		self.schedule = self.b.follow_link(text="View Schedule")
		logging.info(time.asctime() + " Reading page source")
		self.source = self.schedule.read()
		self.currTime = time.localtime()

#def reconnect: If 15 minutes has passed, reload the page and navigate to the proper links. Update scrape timer.
	def reconnect(self):
		logging.info(time.asctime() + " Attemping a reconnect...")
		self.b.reload()
		try: self.schedule = self.b.follow_link(text="View Schedule")
		except mechanize.LinkNotFoundError:
			logging.error(" Reconnect failed, creating a fresh connection.") 
			self.connect()
		self.source = self.schedule.read()
		logging.info(time.asctime() + " Updating source code for scrape.")
		self.currTime = time.localtime()

#def get_open_hours: Reloads the schedule page, scans for all open hours and stores in list. Parses list into readable output and return.
	def get_open_hours(self):
		available = sorted(re.findall(self.openHour, self.source), key=operator.itemgetter(0))
		output = self.build_header("open", len(available))
		for i in available:
			#if i[0] <= self.currTime[6]  and self.currTime[3] >= int(i[1]): #day/hour hasn't passed yet
				day = self.parse_dow(i[0])
				hour = self.parse_hod(i[1])
				shift = self.parse_location(i[2])
				output += day + " -- " + hour + " -- " + shift + " -- " + i[4] + "<br>"
		return output

#def get_schedule: Reloads the schedule page, uses the userID from the received IM and attempts to parse out their current schedule for that week.
	def get_schedule(self,userID):
		staff = re.compile('<font\s+color\s?=\s?\w{4,6}>(?:<b>)?('+userID+'?)<\/[a-b]>', re.IGNORECASE)
		eachShift = re.findall(self.shifts, self.source)
		output = "<br>Schedule for " + userID + "<br>"
		for i in eachShift:
			if re.search(staff, i) and re.search(self.id, i): #if it is a valid shift with workers
				userSchedule = re.findall(self.id, i)
				userSchedule.extend(re.findall(staff, i))
				day = self.parse_dow(userSchedule[0][0])
				hour = self.parse_hod(userSchedule[0][1])
				shift = self.parse_location(userSchedule[0][2])
				output += day + " -- " + hour + " -- " + shift + "<br>"
		return output

#def get_help: Returns a list of options that the user can use when communicating with Lovejoybot.
	def get_help(self):
		return "\n--Help Options--<br>open - Open hours for current week. <br>view (Lovejoy ID) - View schedule of person ID. <br>dance - Show me your moves! <br>help - Call the helpdesk."

#def build_header: Builds a header for the outgoing message based on the request.
	def build_header(self, request, hours):
		currTime = time.localtime()
		temp = "<br>"+time.strftime("%A", currTime)+", "+time.strftime("%B", currTime)+" "+str(currTime[2])+"<br>"
		if request == "open": temp += "Total Open Hours: [" + str(hours) + "]\n"
		elif request == "view": temp += "Hours Scheduled this Week: [" + str(hours) + "]\n"
		return temp

#def parse_dow: Determines what day of week the shift is and returns string value.
	def parse_dow(self, day):
		if day == "1": return "Monday"
		elif day == "2": return "Tuesday"
		elif day == "3": return "Wednesday"
		elif day == "4": return "Thursday"
		elif day == "5": return "Friday"
		elif day == "6": return "Saturday"
		else: return "Sunday"

#def parse_hod: Determines what time of day the shift is, converts to 12-hr clock and returns string value.
	def parse_hod(self, hour):
		if(int(hour) > 12): return str(int(hour)-12) + "pm"
		else: return str(int(hour)) + "am"

#def parse_location: Determine location of shift and converts to readable output.
	def parse_location(self, loc):
		if loc == "1": return "Front"
		elif loc == "2": return "Phone"
		else: return "Trainee"

#class AIMBot: Maintains the connection to the AIM server. Does all Lovejoy class calls for scraping information and sends returned information to the screenname that requested it.
parse = ""
class AIMBot(TocTalk):
	def __init__(self, lovejoy, name, passwd):
		TocTalk.__init__(self, name, passwd)
		self._info = "This is the Lovejoy AIM Bot. Type \"help\" for commands."
		self.lovejoy = lovejoy
		self.lovejoy.connect()
		self.currTime = time.localtime()
		self.danceLyrics = ["We can dance if we want too", 
				   "We can leave your friends behind", 
				   "'Cause if your friends don't dance", 
			     	   "and if they don't dance", 
				   "Well they're no friends of mine"]	
	def on_IM_IN_ENC2(self, data):
		global parse
		recIMTime = time.localtime()
		message = data.split(":",2) #parse username and message sent
		temp = self.strip_html(message[2]).strip(":")
		msg = str(temp[15:])

		#Requested Open Hours
		if str(msg[:4]).lower() == "open": 
			if not parse:
				logging.info(time.asctime() + " No stored parse info, doing a fresh open hour scrape.") 
				parse = self.lovejoy.get_open_hours()
				self.currTime = time.localtime()
			elif recIMTime[4] >= self.currTime[4] + 15 or recIMTime[3] > self.currTime[3]:
				logging.info(time.asctime() + " 15+ minutes have passed, updating scrape info.")
				self.lovejoy.reconnect()
				parse = self.lovejoy.get_open_hours()
				self.currTime = time.localtime()
			logging.info(time.asctime() + " Open hours requested from " + str(message[0]))
			bot.do_SEND_IM(message[0], parse)

		#Requested Full Schedule
		elif str(msg[:4]).lower() == "view":
			employeeName = str(msg[4:]).strip()
			if not re.match('[A-Za-z\.]+',employeeName):
				logging.error(time.asctime() + " Invalid Lovejoy ID was requested by " + str(message[0]))
				bot.do_SEND_IM(message[0], "Invalid Lovejoy Name") 
			else: 
				logging.info(time.asctime() +  " " + employeeName + " schedule requested by " + str(message[0]))
				schedule = self.lovejoy.get_schedule(employeeName)
				bot.do_SEND_IM(message[0], schedule)

		#Requested Dance
		elif str(msg[:5]) == "dance": 
			logging.info(time.asctime() + " Dance command was requested by " + str(message[0]))
			for i in self.danceLyrics:
				bot.do_SEND_IM(message[0], str(i))
				time.sleep(1)
		elif str(msg[:4]) == "help" : 
			logging.info(time.asctime() + " Help command was requested by " + str(message[0]))
			bot.do_SEND_IM(message[0], str(self.lovejoy.get_help()))
		elif str(msg[:4]) == "time" : 
			logging.info(time.asctime() + " Time command was requested by " + str(message[0]))
			bot.do_SEND_IM(message[0], time.asctime())
		else: 
			logging.info(time.asctime() + " Unknown command: \"" + str(msg[0:]) + "\" requested by " + str(message[0]))
			bot.do_SEND_IM(message[0], "Your message has me confused. Type help for a list of my commands.")

#Program is run.
#Get Lovejoy and AIM login information and start the AIMBot.
if __name__ == "__main__":
	print "__Lovejoy Login__"
	lovejoySN = raw_input("Username: ").strip()
	lovejoyPW = getpass.getpass("Password: ").strip()
	print "__AIM Login__"
	aimSN = raw_input("Username: ").strip()
	aimPW = getpass.getpass("Password: ").strip()
	bm = BotManager()
	lj = LJ(lovejoySN, lovejoyPW)
	bot = AIMBot(lj, aimSN, aimPW)
	bm.addBot(bot, "AIMBot")
	time.sleep(5)
	bm.wait()
