#!/usr/bin/python

# check_haproxy.py
# author: Erik Sabowsk <airyk@sabowski.com>
# Copyright 2011 Mopub
# Licensed under the Apache License, Version 2.0
#
# This check will grab the csv status output from the specified haproxy
# server. It returns CRITICAL if any of the servers are in a DOWN state.
#
# Also prints out some information about each cluster:
#   <cluster_name> (Active: <total_up_servers>/<total_servers>)

from optparse import OptionParser
import urllib
import re

# requires options
required = ['hostname', 'port']

# exit statuses
OK       = 0
WARNING  = 1
CRITICAL = 2
UNKNOWN  = 3

# parse command line options
parser = OptionParser("usage: %prog [options]")

parser.add_option('-H', '--hostname', dest='hostname', type='string', metavar='<hostname>',
                    help='[required] Hostname or ip address of haproxy server')
parser.add_option('-p', '--port', dest='port', type='string', metavar='<port>',
                    help='[required] Port number of haproxy server')
parser.add_option('-u', '--uri', dest='uri', type='string', metavar='<uri>',
                    help='location of haproxy csv stats (defaults to "/")')
#parser.add_option('-w', '--warning', dest='warning', type='int', metavar='<seconds>',
#                    help='[required] The warning threshold, in seconds')
#parser.add_option('-c', '--critical', dest='critical', type='int', metavar='<seconds>',
#                    help='[required] The critical threshold, in seconds')

options, args = parser.parse_args()

# check for required arguments, raise error if not all provided
for option in required:
  if not options.__dict__[option]:
    print "UNKNOWN: Missing required parameter {0}".format( option )
    parser.print_help()
    raise SystemExit, UNKNOWN

# construct url
stats_url = "http://{}:{}/{}/;csv".format( options.hostname, options.port, options.uri )

# get the csv stats from the haproxy server
# this will return a string with each line representing a server being proxied
# by the haproxy instance. We split it by line so we can work with one server
# at a time
try:
  stats = urllib.urlopen(stats_url).read().split("\n")
except IOError, e:
  print "HAPROXY UNKNOWN ERROR: {}".format(e)
  raise SystemExit, UNKNOWN

# first row is just column names, pop it off
headers = stats.pop(0)

# regex for getting correct lines of data in the loop below
# we don't want the "BACKEND" or "FRONTEND" data lines
regex = re.compile('(BACK|FRONT)END')

# hashtable to hold information about servers, per cluster
clusters= {}

# default status to ok, change later if we encounter a down server
status = "OK"

# string to output info
output = ""

# get the cluster names and initilize the data structure
for line in stats:
  # we want to skip blank lines
  if not line == '':
    # cluster name is first item in the line
    cluster_name = line.split(",")[0]
    # if we haven't seen this cluster yet add it to 'clusters' and initialize
    # the values for UP and DOWN server totals
    if not cluster_name in clusters:
      clusters[cluster_name] = {}
      clusters[cluster_name]['UP'] = 0
      clusters[cluster_name]['DOWN'] = 0

# iterate through all the data, grabbing and saving the relecant data
for line in stats:
  # skip this iteration if the line is empty
  if line == '':
    continue

  # each line is a string of comma separated values, separate them into an array
  data = line.split(",")

  # get all the lines that aren't FRONTEND or BACKEND
  # data[1]: cluster that this server belongs to
  # data[17]: status of the server ('UP' or 'DOWN') and sometimes a number showing
  #           the number of valid checks on the total number of checks before
  #           transition
  if not regex.match( data[1] ):
    # strip out the numbers (as explained above)
    data[17] = data[17].split(" ")[0]
    # add one to the total
    clusters[data[0]][data[17]] += 1
    # if this was a DOWN status, we have to alert
    if data[17] == "DOWN":
      status = "CRITICAL"

# process information for nagios output, in the format as noting in the notes
# at the top of this script
for cluster_name,cluster_info in clusters.items():
  output += "{} (Active: {}/{}) ".format(cluster_name, cluster_info['UP'],
                                  cluster_info['UP'] + cluster_info['DOWN'])

# output string and send status
if status == "OK":
  print "HAPROXY OK - {}".format( output )
  raise SystemExit, OK
elif status == "CRITICAL":
  print "HAPROXY CRITICAL - {}".format( output )
  raise SystemExit, CRITICAL
else:
  print "HAPROXY UNKNOWN ERROR"
  raise SystemExit, UNKNOWN
