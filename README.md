checkExpiredFiles.py
==================================

DESCRIPTION

	You can use this script to set an expiration date to the files of a directory tree.
	The idea is to initialize a config file to store the expiration date of all the files
	under the base directory, and execute the same script periodically to parse the config
	file and delete the expired files/dirs.


REQUIREMENTS

	- Python 2.6 or higher (lower versions may work, but I haven't tested)
	- standard Python modules (have a look to the script header)

INSTALLATION

	No install needed. Simply chmod'it +x and exec


USAGE

	You can obtain some help with -h parameter:

		Usage: checkExpiredFiles.py [options] [-d DIRTOSCAN] -c CONFIGFILE

		  -h, --help            show this help message and exit
		  -d DIRTOSCAN, --directory=DIRTOSCAN
		                        Directory to scan
		  -c CONFIGFILE, --config-file=CONFIGFILE
                		        a text file to read/write meta-information and
		                        configuration
		  -e EXPIRATION, --expiration-date=EXPIRATION
                		        expiration date, expressed as +n (where n=days and
					time is always 22.00) or YYYY/MM/DD_hh:mm. 
					Default +30 days (@22:00)
		  -n, --dry-run         does not perform any update/delete operation
		  -f, --force           force yes to all
		  -v, --verbose         print file list
		  -V, --version         print program version and exit

	The script needs at least one argument to run: the path to the config file.

	So for example if you want to set an expiration date to the directory /foo/bar and
	save the meta-information (expiration date, file names, etc) in /var/configFile, 
	you can run:

		./checkExpiredFiles.py -d /foo/bar -c /var/configFile

	This will create the config file `/var/configFile' which stores the base name to
	scan (/foo/bar) and the information of each file under the directory.
	In subsequents runs, you only have to run:

		./checkExpiredFiles.py -c /var/configFile

	since the directory name to perform the scan is stored within the config file

	If no expiration is specified, it will be set to 30 days later from today, at 22:00.
	The expiration date is set when running the script for the first time or in
	subsequents runs, for new files found. The format is as specified in the help.

	You can use -n option to test what the script would do, or -v option to see
	the list of files the script will find. Please, use them to ensure it will do
	what you want.

	The -f option force all operations (updating, removing, etc.)
	

COPYING

  Copyright (c) 2014 Miguel Gutiérrez

  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:

  The above copyright notice and this permission notice shall be included
  in all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


CHANGELOG

	v1.0 - 2014/03/17 - first version. Bugs will come soon :-)
	v1.1 - 2014/03/26 - bug fix
