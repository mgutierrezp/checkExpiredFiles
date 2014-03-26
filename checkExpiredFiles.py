#!/usr/bin/python -u

from __future__ import print_function
import ConfigParser, os, datetime, time, sys, unicodedata
from optparse import OptionParser
from itertools import groupby

PROGVERSION="1.0"
DRYRUN=False
FORCE=False
VERBOSE=False
DIRTOSCAN=""
CONFIGFILE=""
EXPIRATION=""

def printVersion():
	global PROGVERSION
	print("Version "+PROGVERSION)
	exit(0)
	
def checkArgs():
	global DRYRUN, DIRTOSCAN, CONFIGFILE, EXPIRATION, FORCE, VERBOSE
	
	parser = OptionParser(usage="usage: %prog [options] [-d DIRTOSCAN] -c CONFIGFILE")
	parser.add_option("-d", "--directory", dest="dirtoscan", help="Directory to scan")
	parser.add_option("-c", "--config-file", dest="configfile", help="a text file to read/write meta-information and configuration")
	parser.add_option("-e", "--expiration-date", dest="expiration", help="expiration date, expressed as +n (where n=days and time=22.00) or YYYY/MM/DD_hh:mm. Default +30 days (@22:00)")
	parser.add_option("-n", "--dry-run", action="store_true", dest="dryrun", default=False, help="does not perform any update/delete operation")
	parser.add_option("-f", "--force", action="store_true", dest="force", default=False, help="force yes to all")
	parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="print file list")
	parser.add_option("-V", "--version", action="store_true", dest="version", default=False, help="print program version and exit")
	
	(options, args) = parser.parse_args()
	if options.version: printVersion()
	DRYRUN=options.dryrun
	DIRTOSCAN=options.dirtoscan
	CONFIGFILE=options.configfile
	EXPIRATION=options.expiration
	FORCE=options.force
	VERBOSE=options.verbose
	
	if options.configfile is None:
		parser.print_help()
		exit(1)

	if os.path.isdir(CONFIGFILE):
		_error(CONFIGFILE+" is a directory... exiting...")
		exit(1)
		
	# check and set EXPIRATION
	if not EXPIRATION is None:
		# -e specified
		try:
			if EXPIRATION[0] == "+":
				# -e +n form
				EXPIRATION=datetime.datetime.combine(datetime.datetime.today()+datetime.timedelta(days=int(EXPIRATION.lstrip("+"))),datetime.time().replace(hour=22,minute=00))
			else:
				# -e DATE form
				EXPIRATION=datetime.datetime.strptime(EXPIRATION,"%Y/%m/%d_%H:%M")
		except:
			_error("invalid date specification!")
			parser.print_help()
			exit(1)
		if EXPIRATION < datetime.datetime.now(): _error("Error: expiration date in the past!"); exit(1)
	else:
		# set default expiration
		try:
			EXPIRATION=datetime.datetime.combine(datetime.datetime.today()+datetime.timedelta(days=30),datetime.time().replace(hour=22,minute=00))
		except:
			_bug("error while setting EXPIRATION date!")
			
	# check DIRTOSCAN
	if not DIRTOSCAN is None and not os.path.isdir(DIRTOSCAN): _error("Error: '"+DIRTOSCAN+"' does not exist."); exit(1)
	if not DIRTOSCAN is None: 
		DIRTOSCAN=DIRTOSCAN.rstrip("/")
		if DIRTOSCAN[len(DIRTOSCAN)-1] == "." or DIRTOSCAN[0] != "/" : _error("Relative dirs are not allowed. Exiting"); exit(1)
	
	if DRYRUN: print(" *** Dry run *** no changes will be made")

def strEXPIRATION():
	return str(EXPIRATION.strftime("%Y/%m/%d_%H:%M"))

def analyzeFiles(config):
	global DIRTOSCAN, DRYRUN, VERBOSE
	
	printHeader()
	
	# this variable will be filled with all the files information: new, deleted, expired and modified
	# it is a dictionary: {filename1:{inode,dateInfo,status}, filename2:{inode,dateInfo,status} ... }
	# the "status" field can take these values: new, update_inode, deleted, expired, non_expired
	allFilesDict=dict()

	# get files from directory tree (disk)
	st="Reading all files from directory tree '"+DIRTOSCAN+"'... "
	print("%-60s" % st ,end="")
	try:
		osWalkDict=dict()
		for root, walkDirs, walkFiles in os.walk(DIRTOSCAN):
			for walkDir in walkDirs:
				if hasControlChars(os.path.join(root,walkDir)):
					_error("  ** Warning: directory '"+os.path.join(root,walkDir)+"' has control characters. Skipping")
				else:
					osWalkDict.update({os.path.join(root,walkDir)[len(DIRTOSCAN)+1:]:{"dateInfo":datetime.datetime.today().strftime("%Y/%m/%d_%H:%M"),"inode":os.lstat(os.path.join(root,walkDir)).st_ino}})
			for walkFile in walkFiles:
				if hasControlChars(os.path.join(root,walkFile)):
					_error("  ** Warning: file '"+os.path.join(root,walkFile)+"' has control characters. Skipping")
				else:
					osWalkDict.update({os.path.join(root,walkFile)[len(DIRTOSCAN)+1:]:{"dateInfo":datetime.datetime.today().strftime("%Y/%m/%d_%H:%M"),"inode":os.lstat(os.path.join(root,walkFile)).st_ino}})
		print("done")
	except:
		_bug("Error!")
	
	# get files from config file
	st="Reading files from config file '"+CONFIGFILE+"'... "
	print("%-60s" % st,end="")
	try:
		configFileDict=dict()
		for f in [list(group) for k, group in groupby(config, lambda x: x == "---\n") if not k]:
			for ff in f:
				ok=False
				if ff.startswith("filename="): filename=ff.split("filename=")[1].rstrip("\n"); ok=True
				if ff.startswith("expiration="): expiration=ff.split("expiration=")[1].rstrip("\n"); ok=True
				if ff.startswith("inode="): inode=ff.split("inode=")[1].rstrip("\n"); ok=True
				if not ok: _bug("Error parsing config file!")
			configFileDict.update({filename:{"expiration":expiration,"inode":inode}})
		print("done")
	except Exception:
		_bug("Error!")

	# build dictionary for new files in disk
	st="Building list of new files... "
	print("%-60s" % st,end="")
	try:
		counter=0
		for addedFile in set(osWalkDict.keys()).difference(set(configFileDict.keys())):
			allFilesDict.update({addedFile:{"dateInfo":strEXPIRATION(),"inode":osWalkDict[addedFile]["inode"],"status":"new"}})
			counter+=1
		for sameName in set(osWalkDict.keys()).intersection(set(configFileDict.keys())):
			if long(osWalkDict[sameName]["inode"]) != long(configFileDict[sameName]["inode"]):
				allFilesDict.update({sameName:{"dateInfo":strEXPIRATION(),"inode":osWalkDict[sameName]["inode"],"status":"update_inode"}})
				counter+=1
		print(str(counter)+" files/dirs found")
		if VERBOSE:
			for addedFile in allFilesDict.keys():
				if allFilesDict[addedFile]["status"] in ["new","update_inode"]:
					print("   %-50s" % addedFile,end='')
					if allFilesDict[addedFile]["status"]=="update_inode":
						print(" -- NEW! file's inode has changed!")
					else:
						print(" -- NEW! file has been added to disk")
					
	except:
		_bug("Error!")
		
	# build dictionary for already deleted files/dirs (exist in config file but not in disk)
	st="Building list of already deleted files... "
	print("%-60s" % st,end="")
	try:
		counter=0
		for deletedFile in set(configFileDict.keys()).difference(set(osWalkDict.keys())):
			allFilesDict.update({deletedFile:{"dateInfo":configFileDict[deletedFile]["expiration"],"inode":configFileDict[deletedFile]["inode"],"status":"deleted"}})
			counter+=1
		print(str(counter)+" files/dirs found")
		if VERBOSE:
			for deletedFile in allFilesDict.keys():
				if allFilesDict[deletedFile]["status"]=="deleted":
					print("   %-50s" % deletedFile,end='')
					print(" -- DELETED! file does not exist anymore in disk")
	except:
		_bug("Error!")
	
	# build dictionary for expired and not already deleted files/dirs
	st="Building list of expired and not deleted files... "
	print("%-60s" % st,end="")
	try:
		counter=0
		for expired in configFileDict:
			if datetime.datetime.today() >= datetime.datetime.strptime(configFileDict[expired]["expiration"],"%Y/%m/%d_%H:%M") and (not expired in allFilesDict or not allFilesDict[expired]["status"] in ["deleted","update_inode"]):
				allFilesDict.update({expired:{"dateInfo":configFileDict[expired]["expiration"],"inode":configFileDict[expired]["inode"],"status":"expired"}})
				counter+=1
		print(str(counter)+" files/dirs expired")
		if VERBOSE:
			for expiredFile in allFilesDict.keys():
				if allFilesDict[expiredFile]["status"]=="expired":
					print("   %-50s" % expiredFile,end='')
					print(" -- EXPIRED! file has expired")
	except:
		_bug("Error!")
	
	# build dictionary for non-expired files/dirs
	st="Getting list of non-expired and not deleted files... "
	print("%-60s" % st,end="")
	try:
		counter=0
		for non_expired in configFileDict:
			if  datetime.datetime.today() < datetime.datetime.strptime(configFileDict[non_expired]["expiration"],"%Y/%m/%d_%H:%M") and (not non_expired in allFilesDict or not allFilesDict[non_expired]["status"] in ["deleted","update_inode"]):
				allFilesDict.update({non_expired:{"dateInfo":configFileDict[non_expired]["expiration"],"inode":configFileDict[non_expired]["inode"],"status":"non_expired"}})
				counter+=1
		print(str(counter)+" files/dirs non-expired")
		if VERBOSE:
			for non_expiredFile in allFilesDict.keys():
				if allFilesDict[non_expiredFile]["status"]=="non_expired":
					print("   %-50s" % non_expiredFile,end='')
					print(" -- NON-EXPIRED! file has NOT expired")
	except:
		_bug("Error!")
	
	return allFilesDict

def printHeader():
	print()
	print("Config file: "+CONFIGFILE)
	print("Directory: "+str(DIRTOSCAN))
	print("Expiration for new files: "+strEXPIRATION())
	print()
	
def createNewConfigFile():
	print("Creating new config file")
	printHeader()
	
	try:
		if os.path.isfile(CONFIGFILE):
			_error("Warning: config file '"+CONFIGFILE+"' already exists!")
			if FORCE:
				_error("Overwriting due to -f option")
			else:
				while True:
					ans=raw_input("do you want to overwrite? [y/N] ")
					if ans.upper()=="N" or ans=="": _error("Aborting!"); exit(1)
					if ans.upper()=="Y": break
		
		print()
		print("Searching files and directories in "+DIRTOSCAN+" ... ",end="")

		filesDict=dict()
		fileCounter, dirCounter = 0,0
		for root, dirs, files in os.walk(DIRTOSCAN):
			for dir in dirs:
				dirFull=os.path.join(root,dir)
				if hasControlChars(dirFull):
					_error("\n** Warning: file name '"+fileFull+"' has control characters. Skipping...")
				else:
					filesDict.update({os.path.join(root,dir)[len(DIRTOSCAN)+1:]:{"expiration":strEXPIRATION(),"inode":str(os.lstat(dirFull).st_ino)}})
					dirCounter+=1
			for file in files:
				fileFull=os.path.join(root,file)
				if hasControlChars(fileFull):
					_error("\n** Warning: file name '"+fileFull+"' has control characters. Skipping...")
				else:
					filesDict.update({os.path.join(root,file)[len(DIRTOSCAN)+1:]:{"expiration":strEXPIRATION(),"inode":str(os.lstat(fileFull).st_ino)}})
					fileCounter+=1
		
		print(str(fileCounter)+" files and "+str(dirCounter)+" directories")
		
		if VERBOSE:
			for f in filesDict: print("   "+f)
		
		print("done")
		
	except Exception:
		_bug("Error!")
		
	if DRYRUN: print();print("** Exiting due to -n option **"); exit(0)
	
	print("Saving information to "+CONFIGFILE)
	
	try:
		_file=open(CONFIGFILE,"w")
		
		_file.write("base="+DIRTOSCAN+"\n")
		for f in filesDict: 	_file.write("---"+"\n"+"filename="+f+"\n"+"expiration="+strEXPIRATION()+ "\n"+"inode="+str(filesDict[f]["inode"])+"\n")
	
		_file.close()
		
	except:
		_bug("Error!!")
	
	print()
	print("Finished.")

def _error(msg):
	print(msg,file=sys.stderr)
	
def _bug(msg):
	print()
	print("******* ooopps!! something went wrong!!!: " + msg,file=sys.stderr)
	print("----------> "+str(sys.exc_info()))
	print()
	exit (1)

def readConfigFile():
	global DIRTOSCAN
	
	try:
		f=open(CONFIGFILE,'r')
		line=f.readline()
		if not line.startswith("base="): 
			exit(1)
		DIRTOSCAN=line.lstrip("base=").rstrip("\n")
		if not os.path.isdir(DIRTOSCAN): _error("Error: '"+DIRTOSCAN+"' (from config file) does not exist."); exit(1)
	except:
		_error("Error: there was a problem while reading config file!")
		exit(1)
	DIRTOSCAN=DIRTOSCAN.rstrip("/")

	return(f.readlines())
	

def hasControlChars(st):
	for f in st.decode('utf-8'): 
		if unicodedata.category(f)[0] == 'C': return True
	return False


def applyChanges(filesDict):
	print()
	
	# ask for confirmation
	if not FORCE:
		while True:
			ans=raw_input("Apply changes? [y/N] ")
			if ans.upper()=="N" or ans=="": _error("Exiting!"); exit(1)
			if ans.upper()=="Y": break
	
	print("Applying changes...")

	print("Removing expired files from filesystem (if any)... ",end="")
	try:
		for ffile in filesDict:
			if filesDict[ffile]["status"]=="expired":
				# file has expired
				fileToDeleteFull=os.path.join(DIRTOSCAN,ffile)
				fileToDeleteRelative=ffile
				if not os.path.exists(fileToDeleteFull) and not os.path.islink(fileToDeleteFull):
					_error("File does not exists anymore, skipping: "+fileToDeleteRelative)
					continue
				if os.path.isdir(fileToDeleteFull) and os.listdir(fileToDeleteFull) and not os.path.islink(fileToDeleteFull):
					# but is a non-empty directory, so skip it!
					continue
				if os.path.islink(fileToDeleteFull) or os.path.isfile(fileToDeleteFull):
					# it's a regular file or symlink, so delete it. In case of symlink, removes only the link
					# also removes the parent(s) directories if empty and expired
					os.unlink(fileToDeleteFull)
					aux=os.path.dirname(fileToDeleteRelative)
					while aux != "":
						if not os.listdir(os.path.join(DIRTOSCAN,aux)) and filesDict[aux]["status"]=="expired":
							# remove empty and expired directory
							os.rmdir(os.path.join(DIRTOSCAN,aux))
						aux=os.path.dirname(aux)
					continue
				if os.path.isdir(fileToDeleteFull) and not os.listdir(fileToDeleteFull):
					# delete empty directory
					os.rmdir(fileToDeleteFull)
					continue

				print(" -- unknown file type! skipping '"+fileToDelete+"'")
	except Exception:
		_bug("Error!")
	print("done.")
	
	# update config file
	try:
		print("Updating config file... ",end="")
		_file=open(CONFIGFILE,"w")
		_file.write("base="+DIRTOSCAN+"\n")
		for file in filesDict:
			if filesDict[file]["status"] in ["new","update_inode","non_expired"]:
				_file.write("---"+"\n"+"filename="+file+"\n"+"expiration="+filesDict[file]["dateInfo"]+ "\n"+"inode="+str(filesDict[file]["inode"])+"\n")
		_file.close()
		print("done.")
	except:
		_bug("Error!")


################### MAIN ####################

checkArgs()
if DIRTOSCAN is None:
	config=readConfigFile()
	filesDict=analyzeFiles(config)
	if DRYRUN:
		print()
		print(" ** no changes applied **")
		exit(0)
	applyChanges(filesDict)
else:
	# create new config file
	createNewConfigFile()
	

