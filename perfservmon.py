#!/usr/bin/python
"""
@author: varounisdi
@contributor: atterdag
"""

import argparse
import shelve
import anydbm
from xml.etree.ElementTree import parse
import urllib2
import sys
import datetime
import platform
import os
import time
import base64
import ssl
import socket


class GenericServer:
    """Generic WAS Server Prototype"""

    def __init__(self, name, nodename):
        """
        :param name: WAS Server Name
        :param nodename: WAS Node Name the Server belongs
        """
        self.name = name
        self.nodename = nodename
        self.maxheapMB = None
        self.heapusedMB = None

    def printserver(self):
        """
        Print Generic Server Attributes(for debug purposes)
        """
        print 'Name:' + str(self.name)
        print 'NodeName:' + str(self.nodename)
        print 'MaxHeap:' + str(self.maxheapMB)
        print 'HeapUsed:' + str(self.heapusedMB)

    def serverfullname(self):
        """Utility to uniquely identify a server in a Cell"""
        return '.'.join((self.nodename, self.name))


# ###################################################################################
class SIBDestination:
    """WAS SIB Generic Class
    Can be a Topic Space or a Queue
    """

    def __init__(self, name, totalmessagesconsumed, availablemessages):
        """
        :param name: The Destination Name
        :param totalmessagesconsumed: PMI Metric -> Total Messages Consumed since restart of Message Engine
        :param availablemessages: PMI Metric -> No of available msgs in Destination
        """
        self.Name = name
        self.TotalMessagesConsumed = totalmessagesconsumed
        self.AvailableMessages = availablemessages

    def printsibdest(self):
        print 'SIB Destination Name:' + str(self.Name)
        print 'SIB Dest Messages Consumed:' + str(self.TotalMessagesConsumed)
        print 'SIB Dest Available Messages:' + str(self.AvailableMessages)


class SIBQueue(SIBDestination):
    """Queue Destination"""

    def __init__(self, name, totalmessagesconsumed, availablemessages):
        SIBDestination.__init__(self, name, totalmessagesconsumed, availablemessages)


class SIBTopicSpace(SIBDestination):
    """Pub/Sub Destination"""

    def __init__(self, name, totalmessagesconsumed, availablemessages):
        """
        :param name: The Destination Name
        :param totalmessagesconsumed: PMI Metric -> Total Messages Consumed since restart of Message Engine
        :param availablemessages: PMI Metric -> No of available msgs in Destination
        """
        SIBDestination.__init__(self, name, totalmessagesconsumed, availablemessages)
        self.subscribers = []

    def adddurablesubscriber(self, subscrname):
        """Add Active Durable Subscribers to the list"""
        self.subscribers.append(str(subscrname))

    def printsibdest(self):
        SIBDestination.printsibdest(self)
        if len(self.subscribers) > 0:
            print 'SIB Topic Subscribers:' + str(self.subscribers)


# ######################################################################################


class TypicalApplicationServer(GenericServer):
    """Typical WAS Class - Recommended for use in most cases"""

    def __init__(self, name, nodename):
        GenericServer.__init__(self, name, nodename)
        self.wcpoolsize = None
        self.wcactive = None
        self.wcthreadshung = None
        self.orbpoolsize = None
        self.orbactive = None
        self.connpoolspercentused = {}
        self.connpoolsusetime = {}
        self.connpoolswaittime = {}
        self.connpoolswaitingthreadcount = {}
        self.totalactivesessions = None
        self.totallivesessions = None
        self.activesessions = {}
        self.livesessions = {}
        self.destinations = {}
        self.webSecAuthenTime = None
        self.webSecAuthorTime = None

    def printserver(self):
        """
        Print Typical Server Attributes(for debug purposes)
        """
        print '****************************'
        GenericServer.printserver(self)
        print 'WebContainerActive:' + str(self.wcactive)
        print 'WebContainerPoolSize:' + str(self.wcpoolsize)
        print 'WebContainerConcurrentHungThreadCount:' + str(self.wcthreadshung)
        print 'ORBActive:' + str(self.orbactive)
        print 'ORBPoolSize:' + str(self.orbpoolsize)
        print 'JDBC Conn Pools Percent Used:' + str(self.connpoolspercentused)
        print 'JDBC Conn Pools Use Time:' + str(self.connpoolsusetime)
        print 'JDBC Conn Pools Wait Time:' + str(self.connpoolswaittime)
        print 'JDBC Conn Pools Waiting Thread Count:' + str(self.connpoolswaitingthreadcount)
        print 'Total Active Http Sessions:' + str(self.totalactivesessions)
        print 'Total Live Http Sessions:' + str(self.totallivesessions)
        print 'Http Active Sessions:' + str(self.activesessions)
        print 'Http Live Sessions:' + str(self.livesessions)
        for dest in self.destinations:
            (self.destinations[dest]).printsibdest()
        print '****************************'

    def addjdbcconnpoolpercentused(self, name, value):
        self.connpoolspercentused[name] = value

    def addjdbcconnpoolusetime(self, name, value):
        self.connpoolsusetime[name] = value

    def addjdbcconnpoolwaittime(self, name, value):
        self.connpoolswaittime[name] = value

    def addjdbcconnpoolwaitingthreadcount(self, name, value):
        self.connpoolswaitingthreadcount[name] = value

    def addactivehttpsessions(self, modname, nosessions):
        self.activesessions[modname] = nosessions

    def addlivehttpsessions(self, modname, nosessions):
        self.livesessions[modname] = nosessions

    def adddestination(self, sibdest):
        self.destinations[sibdest.Name] = sibdest

    def querywebcontainer(self, warning=75, critical=90):
        if self.wcactive is None or self.wcpoolsize is None:
            return UNKNOWN, 'Could not find WebContainer Usage metrics for server {}'.format(self.name)
        else:
            percentused = int(float(self.wcactive) / float(self.wcpoolsize) * 100)
            msg = 'WebContainer Thread Pool: {actv}/{sz} ({pc}%)|' \
                  'wcthreadpoolusage={pc}%;{warn};{crit} wcthreadpoolused={actv};;;0;{sz}'\
                .format(actv=self.wcactive, sz=self.wcpoolsize, pc=percentused, warn=warning, crit=critical)
            if warning < percentused < critical:
                return WARNING, msg
            elif percentused >= critical:
                return CRITICAL, msg
            else:
                return OK, msg

    def querywebcontainerhungthreads(self, warning=75, critical=90):
        if self.wcthreadshung is None:
            return UNKNOWN, 'Could not find WebContainer Thread Hung metrics for server {}'.format(self.name)
        else:
            wcthreadshung = int(self.wcthreadshung)
            msg = 'WebContainer Declared Thread Hung: {thrh}|wcthreadhung={thrh};{warn};{crit};0'\
                .format(thrh=self.wcthreadshung, warn=warning, crit=critical)
            if warning < wcthreadshung < critical:
                return WARNING, msg
            elif wcthreadshung >= critical:
                return CRITICAL, msg
            else:
                return OK, msg

    def queryorb(self, warning=75, critical=90):
        if self.orbactive is None or self.orbpoolsize is None:
            return UNKNOWN, 'Could not find ORB metrics for server {}'.format(self.name)
        else:
            percentused = int(float(self.orbactive) / float(self.orbpoolsize) * 100)
            msg = 'ORB Thread Pool: {actv}/{sz} ({pc}%)|' \
                  'orbthreadpoolusage={pc}%;{warn};{crit} orbthreadpoolused={actv};;;0;{sz}'\
                .format(actv=self.orbactive, sz=self.orbpoolsize, pc=percentused, warn=warning, crit=critical)
            if warning < percentused < critical:
                return WARNING, msg
            elif percentused >= critical:
                return CRITICAL, msg
            else:
                return OK, msg

    def querydbconnpoolpercentused(self, jndiname=None, warning=75, critical=90):
        if len(self.connpoolspercentused) == 0 or self.connpoolspercentused is None:
            return UNKNOWN, 'Could not find DB Connection Pool Percent Used metrics for server {}'.format(self.name)
        else:
            msg = 'DB Connection Pool Percent Used'
            statuscode = OK
            if jndiname is None:
                # If no jndi name is given, show all Connection Pools
                # alert if any is above Warn, Crit
                for connpool in self.connpoolspercentused:
                    percentused = int(self.connpoolspercentused[connpool])
                    msg += ' - %s %s%%' % (connpool, percentused)
                    # For this loop, Change statuscode only when lower status code is active
                    # e.g. change to warning only when statuscode is OK, not critical or warning
                    if warning < percentused < critical and statuscode == OK:
                        statuscode = WARNING
                    if critical <= percentused:
                        statuscode = CRITICAL
            elif jndiname in self.connpoolspercentused:
                percentused = int(self.connpoolspercentused[jndiname])
                msg = 'DB Connection Pool Percent Used - {jndi} {pc}%|{jndi}_usage={pc}%;{warn};{crit}'\
                    .format(jndi=jndiname, pc=percentused, warn=warning, crit=critical)
                if warning < percentused < critical:
                    statuscode = WARNING
                if critical <= percentused:
                    statuscode = CRITICAL
            else:
                msg = 'No DB Connection Pool for {jndi} was found'.format(jndi=jndiname)
                statuscode = "UNKNOWN"
            return statuscode, msg

    def querydbconnpoolusetime(self, jndiname, warning=10, critical=30):
        if len(self.connpoolsusetime) == 0 or self.connpoolsusetime is None:
            return UNKNOWN, 'Could not find DB Connection Pool Use Time metrics for server {}'.format(self.name)
        else:
            if jndiname in self.connpoolsusetime:
                statuscode = OK
                usetime = int(self.connpoolsusetime[jndiname])
                msg = 'DB Connection Pool Use Time - {jndi} {usets} seconds|' \
                      '{jndi}_usetime={usets}s;{warn};{crit};0'\
                    .format(jndi=jndiname, usets=usetime, warn=warning, crit=critical)
                if warning < usetime < critical:
                    statuscode = WARNING
                if critical <= usetime:
                    statuscode = CRITICAL
            else:
                statuscode = "UNKNOWN"
                msg = 'No DB Connection Pool for {jndi} was found'.format(jndi=jndiname)
            return statuscode, msg

    def querydbconnpoolwaittime(self, jndiname, warning=5, critical=10):
        if len(self.connpoolswaittime) == 0 or self.connpoolswaittime is None:
            return UNKNOWN, 'Could not find DB Connection Pool Wait Time metrics for server {}'.format(self.name)
        else:
            if jndiname in self.connpoolswaittime:
                statuscode = OK
                waittime = int(self.connpoolswaittime[jndiname])
                msg = 'DB Connection Pool Wait Time - {jndi} {waitts} seconds|' \
                      '{jndi}_waittime={waitts}s;{warn};{crit};0'\
                    .format(jndi=jndiname, waitts=waittime, warn=warning, crit=critical)
                if warning < waittime < critical:
                    statuscode = WARNING
                if critical <= waittime:
                    statuscode = CRITICAL
            else:
                statuscode = "UNKNOWN"
                msg = 'No DB Connection Pool for {jndi} was found'.format(jndi=jndiname)
            return statuscode, msg

    def querydbconnpoolwaitingthreadcount(self, jndiname, warning=5, critical=10):
        if len(self.connpoolswaitingthreadcount) == 0 or self.connpoolswaitingthreadcount is None:
            return UNKNOWN, 'Could not find DB Connection Pool Waiting Threads Count metrics for server {}'\
                .format(self.name)
        else:
            if jndiname in self.connpoolswaitingthreadcount:
                statuscode = OK
                waitingthreadcount = int(self.connpoolswaitingthreadcount[jndiname])
                msg = 'DB Connection Pool Waiting Threads Count - {jndi} {waitthrcount}|' \
                      '{jndi}_waitthreads={waitthrcount};{warn};{crit};0'\
                    .format(jndi=jndiname, waitthrcount=waitingthreadcount, warn=warning, crit=critical)
                if warning < waitingthreadcount < critical:
                    statuscode = WARNING
                if critical <= waitingthreadcount:
                    statuscode = CRITICAL
            else:
                statuscode = "UNKNOWN"
                msg = 'No DB Connection Pool for {jndi} was found'.format(jndi=jndiname)
            return statuscode, msg

    def queryheapusage(self, warning=75, critical=90):
        if self.heapusedMB is None or self.maxheapMB is None:
            return UNKNOWN, 'Could not find Heap Usage metrics for server {}'.format(self.name)
        else:
            percentused = int(float(self.heapusedMB) / float(self.maxheapMB) * 100)
            msg = 'Heap Usage: {heapused}/{maxheap} MB ({heappc}%)|' \
                  'heapusage={heappc}%;{warn};{crit} usedheap={heapused}MB;;;0;{maxheap}'\
                .format(heapused=self.heapusedMB, maxheap=self.maxheapMB, heappc=percentused, warn=warning, crit=critical)
            if warning < percentused < critical:
                return WARNING, msg
            elif percentused >= critical:
                return CRITICAL, msg
            else:
                return OK, msg

    def querysecauthen(self, warning=2, critical=5):
        if self.webSecAuthenTime is None:
            return UNKNOWN, 'Could not find Web Authentication Time metrics for server {}'.format(self.name)
        else:
            websecauthentime = int(self.webSecAuthenTime)
            msg = 'Web Authentication Time: {wsecauthtime} seconds|websecauthentime={wsecauthtime}s;{warn};{crit}'\
                .format(wsecauthtime=self.webSecAuthenTime, warn=warning, crit=critical)
            if warning < websecauthentime < critical:
                return WARNING, msg
            elif websecauthentime >= critical:
                return CRITICAL, msg
            else:
                return OK, msg

    def querysecauthor(self, warning=2, critical=5):
        if self.webSecAuthorTime is None:
            return UNKNOWN, 'Could not find Web Authorization Time metrics for server {}'.format(self.name)
        else:
            websecauthortime = int(self.webSecAuthorTime)
            msg = 'Web Authorization Time: {wsecauthortime} seconds|websecauthortime={wsecauthortime}s;{warn};{crit}'\
                .format(wsecauthortime=self.webSecAuthorTime, warn=warning, crit=critical)
            if warning < websecauthortime < critical:
                return WARNING, msg
            elif websecauthortime >= critical:
                return CRITICAL, msg
            else:
                return OK, msg

    def querylivesessions(self):
        if len(self.livesessions) == 0 or self.totallivesessions is None:
            return UNKNOWN, 'Could not find Live Session metrics for server {}'.format(self.name)
        else:
            msg = 'live sessions: total %s' % self.totallivesessions
            for appmodule in self.livesessions:
                msg += ' , %s %s' % (appmodule, str(self.livesessions[appmodule]))
            return OK, msg

    def querysibdestination(self, destname, waitingmsgcountwarn=10, waitingmsgcountcrit=100):
        if len(self.destinations) == 0 or self.destinations is None:
            return UNKNOWN, 'Could not find Destination metrics for server {}'.format(self.name)
        else:
            destination = self.destinations[destname]
            msg = 'Destination:%s - Available Messages:%s , Messages Consumed:%s ' % (
                destination.Name, destination.AvailableMessages, destination.TotalMessagesConsumed)
            if isinstance(destination, SIBTopicSpace) and len(destination.subscribers) > 0:
                msg += ' , Durable Subscribers:'
                for subscriber in destination.subscribers:
                    msg += '%s ' % subscriber
            if waitingmsgcountwarn < int(destination.AvailableMessages) < waitingmsgcountcrit:
                return WARNING, msg
            elif int(destination.AvailableMessages) > waitingmsgcountcrit:
                return CRITICAL, msg
            else:
                return OK, msg


# ############################################################################################################
def parseperfxml(path, cellname):
    """
    Parse the perfsevlet xml and store the needed metrics(defined in metrics dict) for all WAS servers
    of the Cell in a python selve file
    :param path: Where to store the perfserv xml and the python shelve file
    :param cellname: The name of the WAS Cell
    :raise:
    """
    xmlfilename = path + cellname + '.xml'
    shelvefilename = path + cellname + '.dbm'
    pfile = shelve.open(shelvefilename, flag='c')
    metrics = {'Security Authentication': parsesecauthen,
               'Security Authorization': parsesecauthor,
               'JVM Runtime': parsejvmstats,
               'WebContainer': parsewebcontstats,
               'Object Request Broker': parseorbtpstats,
               'JDBC Connection Pools': parseconnpoolsstats,
               'Servlet Session Manager': parsesessionstats,
               'SIB Service': parsesibstats
               }
    try:
        tree = parse(xmlfilename)
        for B in tree.iter('Node'):
            nodename = B.attrib['name']
            for server in B.iter('Server'):
                was = TypicalApplicationServer(server.attrib['name'], nodename)
                for stat in server.iter('Stat'):
                    metricname = stat.attrib['name']
                    if metricname is not None and metricname in metrics:
                        # For each metric call the appropriate method
                        metrics[metricname](was, stat)
                # Comment out for debug purposes
                #was.printserver()
                pfile[was.serverfullname()] = was
    except AttributeError:
        raise


def parsejvmstats(was, stat):
    for jvmstat in stat.iter():
        if jvmstat.attrib['name'] == 'HeapSize':
            was.maxheapMB = int(jvmstat.attrib['upperBound']) / 1024
        if jvmstat.attrib['name'] == 'UsedMemory':
            was.heapusedMB = int(jvmstat.attrib['count']) / 1024


def parsesecauthen(was, stat):
    for secauthen in stat.iter():
        if secauthen.attrib['name'] == 'WebAuthenticationTime':
            was.webSecAuthenTime = int(secauthen.attrib['max']) / 1000


def parsesecauthor(was, stat):
    for secauthor in stat.iter():
        if secauthor.attrib['name'] == 'WebAuthorizationTime':
            was.webSecAuthorTime = int(secauthor.attrib['max']) / 1000


def parsewebcontstats(was, stat):
    for wcstat in stat.iter('BoundedRangeStatistic'):
        if wcstat.attrib['name'] == 'ActiveCount':
            was.wcactive = wcstat.attrib['value']
        if wcstat.attrib['name'] == 'PoolSize':
            was.wcpoolsize = wcstat.attrib['upperBound']
    for wcstat in stat.iter('CountStatistic'):
        if wcstat.attrib['name'] == 'DeclaredThreadHungCount':
            was.wcthreadshung = wcstat.attrib['count']


def parseorbtpstats(was, stat):
    for orbstat in stat.iter('BoundedRangeStatistic'):
        if orbstat.attrib['name'] == 'ActiveCount':
            was.orbactive = orbstat.attrib['value']
        if orbstat.attrib['name'] == 'PoolSize':
            was.orbpoolsize = orbstat.attrib['upperBound']


def parseconnpoolsstats(was, stat):
    for connprovider in stat.findall('./Stat'):
        for connpool in connprovider.findall('./Stat'):
            connpoolpercentused = connpool.find(".//RangeStatistic[@name='PercentUsed']")
            if connpoolpercentused is not None:
                was.addjdbcconnpoolpercentused(connpool.attrib['name'], connpoolpercentused.attrib['value'])
            connpoolwaitingthreadcount = connpool.find(".//RangeStatistic[@name='WaitingThreadCount']")
            if connpoolwaitingthreadcount is not None:
                was.addjdbcconnpoolwaitingthreadcount(connpool.attrib['name'], connpoolwaitingthreadcount.attrib['value'])
            # The following values are measured in ms, convert to seconds
            connpoolusetime = connpool.find(".//TimeStatistic[@name='UseTime']")
            if connpoolusetime is not None:
                was.addjdbcconnpoolusetime(connpool.attrib['name'], int(connpoolusetime.attrib['max'])/1000)
            connpoolwaittime = connpool.find(".//TimeStatistic[@name='WaitTime']")
            if connpoolwaittime is not None:
                was.addjdbcconnpoolwaittime(connpool.attrib['name'], int(connpoolwaittime.attrib['max'])/1000)


def parsesessionstats(was, stat):
    for module in stat.findall('./Stat'):
        modname = module.attrib['name']
        if not modname.startswith('perfServletApp'):
            activesessions = module.find(".//RangeStatistic[@name='ActiveCount']")
            livesessions = module.find(".//RangeStatistic[@name='LiveCount']")
            if activesessions is not None:
                was.addactivehttpsessions(modname, activesessions.attrib['value'])
            if livesessions is not None:
                was.addlivehttpsessions(modname, livesessions.attrib['value'])
    for totals in stat.findall('./RangeStatistic'):
        if totals.attrib['name'] == 'ActiveCount':
            was.totalactivesessions = totals.attrib['value']
        elif totals.attrib['name'] == 'LiveCount':
            was.totallivesessions = totals.attrib['value']


def parsesibstats(was, stat):
    """
    Parse SIB Statistics found in  perfservlet xml and attach them in WAS Object instance
    :param was: Current Typical Application Server instance
    :param stat: Stat tags in perfservlet xml under the specific Server tag
    """
    queuesnode = stat.find(".//Stat[@name='Queues']")
    if queuesnode is not None:
        for queue in queuesnode.findall('./Stat'):
            queuename = queue.attrib['name']
            totammsgsconsumed = queue.find(
                "./CountStatistic[@name='QueueStats.TotalMessagesConsumedCount']")
            availablemsgs = queue.find("./CountStatistic[@name='QueueStats.AvailableMessageCount']")
            if totammsgsconsumed is not None and availablemsgs is not None:
                sibqueue = SIBQueue(queuename, totammsgsconsumed.attrib['count'],
                                    availablemsgs.attrib['count'])
                was.adddestination(sibqueue)
    topicspacesnode = stat.find(".//Stat[@name='Topicspaces']")
    if topicspacesnode is not None:
        # Loop over each topic space
        for topicspace in topicspacesnode.findall('./Stat'):
            topicspname = topicspace.attrib['name']
            totammsgsconsumed = topicspace.find(
                "./Stat/CountStatistic[@name='DurableSubscriptionStats.TotalMessagesConsumedCount']")
            availablemsgs = topicspace.find(
                "./Stat/CountStatistic[@name='DurableSubscriptionStats.AvailableMessageCount']")
            if totammsgsconsumed is not None and availablemsgs is not None:
                sibtopic = SIBTopicSpace(topicspname, totammsgsconsumed.attrib['count'],
                                         availablemsgs.attrib['count'])
                for durablesub in topicspace.findall("./Stat[@name='Durable Subscriptions']/Stat"):
                    dursubname = durablesub.attrib['name']
                    sibtopic.adddurablesubscriber(dursubname)
                was.adddestination(sibtopic)


# #################################################################################################################
def retrieveperfxml(path, cellname, ip, port, username, password, httpprotocol='http', ignorecert=False):
    """
    Perfservlet XML Retrieval Method
    :param path: The file path where perfserv xml and shelve output is stored
    :param cellname: The Name of the WAS Cell
    :param ip: The ip of the perfserv appication
    :param port: The port of the perfserv appication
    :param username: An user which is authorized to access perfservlet
    :param password: perfservlet authorized user password
    :param httpprotocol: The http protocol to access the perfservlet, can be http or https, default http
    :param ignorecert: Ignore TLS Certificate, default False
    :return: The nagios message
    """
    urlopentimeout = 30
    if httpprotocol in ['http', 'https']:
        url = setperfservurl(ip, port, path, cellname, httpprotocol)
    else:
        return UNKNOWN, 'Invalid Perfserv URL'
    xmlfilename = path + cellname + '.xml'
    try:
        req = urllib2.Request(url)
        # if Basic Auth is enabled
        if username and password:
            auth_encoded = base64.encodestring('%s:%s' % (username, password))[:-1]
            req.add_header('Authorization', 'Basic %s' % auth_encoded)

        # Add SSLContext check for Python newer than 2.7.9
        if httpprotocol == 'https' and hasattr(ssl, 'SSLContext') and hasattr(ssl, 'Purpose') and ignorecert is False:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # Default Behaviour: Accept only trusted SSL certificates
            perfserv = urllib2.urlopen(req, context=ctx, timeout=urlopentimeout)
        elif httpprotocol == 'https' and hasattr(ssl, 'SSLContext') and ignorecert is True:
            # On --ignorecert option accept any certificate
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            perfserv = urllib2.urlopen(req, context=ctx, timeout=urlopentimeout)
        else:
            # Pre Python 2.7.9 behaviour or plain http request
            perfserv = urllib2.urlopen(req, timeout=urlopentimeout)
    except urllib2.HTTPError as error:
            return CRITICAL, 'Could not open perfservlet URL - Response Status Code %s' % error.code
    except urllib2.URLError as error:
        return CRITICAL, 'Could not open perfservlet URL - %s' % error.reason
    # Handle HTTP Timeouts
    except socket.timeout:
        return CRITICAL, 'Could not open perfservlet URL: Socket Timeout'
    # Handle HTTPS Timeouts
    except ssl.SSLError:
        return CRITICAL, 'Could not open perfservlet URL: Generic SSL Error, possibly a timeout'
    else:
        with open(xmlfilename, 'w') as xmlfile:
            xmlfile.writelines(perfserv.readlines())
        tree = parse(xmlfilename)
        root = tree.getroot()
        if root.attrib['responseStatus'] == 'failed':
            return CRITICAL, 'Error retrieving PMI data! Check your Cell status!'
        elif root.attrib['responseStatus'] == 'success':
            return OK, 'PerfServlet Data refreshed on %s' % (datetime.datetime.now().strftime('%c'))
        else:
            return UNKNOWN, 'Unknown Perfserv Status: %s' % root.attrib['responseStatus']


def touch(fullpath):
    """
    Used for Refreshing Perfservlet cache, determing the time for this to happen
    Usage Similar to UNIX touch command
    """
    with open(fullpath, 'a'):
        os.utime(fullpath, None)


def setperfservurl(ip, port, path, cellname, httpprotocol, refcacheinterval=3600):
    """Construct PerfServlet URL to call from Collector
    :param ip: IP Addr of the Server where perfservl runs
    :param port: HTTP Port of the Server where perfservl runs
    :param path: Location of .lck file, used for determining the interval window for the specific Cell
    :param cellname: The Name of the WAS Cell, used in .lck file name
    :param refcacheinterval: Interval to Refresh Perfservlet cache
    :param httpprotocol: The http protocol to access the perfservlet, can be http or https
    :return: PerfServlet URL
    """
    cachereffile = path + cellname + '.lck'
    url = httpprotocol + '://' + ip + ':' + port + '/wasPerfTool/servlet/perfservlet'
    if os.path.isfile(cachereffile):
        timeelapsed = time.time() - os.path.getmtime(cachereffile)
        if timeelapsed > refcacheinterval:
            touch(cachereffile)
            return url + '?refreshConfig=true'
        return url
    else:
        touch(cachereffile)
        return url


def parsecmdargs():
    """Parse Given Plugin Attributes"""
    parser = argparse.ArgumentParser(description='Nagios plugin on Websphere Cell Metrics. Uses the PerfServlet App')
    parser.add_argument("-C", type=str, action="store", dest='CellName', help="Cell name", required=True)
    subparsers = parser.add_subparsers(help='Commands', dest='command_name')
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve Data and Store them')
    retrieve_parser.add_argument("-N", type=str, action="store", dest='IPAddress',
                                 help="IP Address of perfservlet server", required=True)
    retrieve_parser.add_argument("-P", type=str, action="store", dest='Port', help="Port of perfservlet server",
                                 required=True)
    retrieve_parser.add_argument("-H", type=str, action="store", dest='HttpProtocol', choices=['http', 'https'],
                                 help="Perfservlet HTTP Protocol", default='http', required=False)
    retrieve_parser.add_argument("--ignorecert", action="store_true",
                                 help="Ignore TLS Server Certificate", required=False)
    retrieve_parser.add_argument("-u", type=str, action="store", dest='Username',
                                 help="Perfservlet authorized user", default='', required=False)
    retrieve_parser.add_argument("-p", type=str, action="store", dest='Password',
                                 help="Perfservlet user password", default='', required=False)
    show_parser = subparsers.add_parser('show', help='Show metrics')
    show_parser.add_argument("-n", type=str, action="store", dest='NodeName', help="Node Name", required=True)
    show_parser.add_argument("-s", type=str, action="store", dest='ServerName', help="Server Name", required=True)
    show_parser.add_argument("-M", type=str, action="store", dest='Metric',
                             choices=['WebContainer', 'WebContainerThreadHung', 'ORB', 'DBConnectionPoolPercentUsed',
                                      'DBConnectionPoolUseTime', 'DBConnectionPoolWaitTime',
                                      'DBConnectionPoolWaitingThreadCount', 'Heap', 'LiveSessions',
                                      'SIBDestinations', 'WebAuthenticationTime', 'WebAuthorizationTime'],
                             help="Metric Type", required=True)
    show_parser.add_argument("-d", type=str, action="store", dest='Destination', help="SIB Destination Name",
                             required=False)
    show_parser.add_argument("-j", type=str, action="store", dest='JndiName', help="JNDI Name", required=False)
    show_parser.add_argument("-c", type=int, action="store", dest='Critical',
                             help="Critical Value for Metric", required=False)
    show_parser.add_argument("-w", type=int, action="store", dest='Warning',
                             help="Warning Value for Metric", required=False)
    return parser.parse_args()


def queryperfdata(path, cellname, nodename, servername, metric, warning, critical, destination=None, jndiname=None):
    """Fundamental Perfservlet Data Query Method - Used by Nagios show Check
    :param path: Where selve file lies
    :param cellname: the WAS Cell Name
    :param nodename: the WAS Node Name
    :param servername: the WAS Server Name
    :param metric: Pick one of WebContainer, ORB, DBConnectionPoolPercentUsed, DBConnectionPoolUseTime,
    DBConnectionPoolWaitTime, DBConnectionPoolWaitingThreadCount, Heap, LiveSessions, SIBDestinations,
    WebAuthenticationTime, WebAuthorizationTime
    :param warning: Warning threshold
    :param critical: Critical threshold
    :param jndiname: JNDI Name. Must be defined if Metric = DBConnectionPool*
    :param destination: Destination Name. Must be defined if Metric = SIBDestinations
    :return: Nagios Message
    """
    shelvefilename = path + cellname + '.dbm'
    try:
        perffile = shelve.open(shelvefilename, flag='r')
    except IOError as error:
        return UNKNOWN, error.message
    except anydbm.error as error:
        return UNKNOWN, error.message
    serverfullname = '.'.join((nodename, servername))
    if serverfullname in perffile:
        appsrv = perffile[serverfullname]
        if metric == 'WebContainer':
            return appsrv.querywebcontainer(warning, critical)
        if metric == 'WebContainerThreadHung':
            return appsrv.querywebcontainerhungthreads(warning, critical)
        elif metric == 'ORB':
            return appsrv.queryorb(warning, critical)
        elif metric == 'DBConnectionPoolPercentUsed':
            return appsrv.querydbconnpoolpercentused(jndiname, warning, critical)
        elif metric == 'DBConnectionPoolUseTime':
            if jndiname is not None:
                return appsrv.querydbconnpoolusetime(jndiname, warning, critical)
            else:
                return UNKNOWN, 'Please set datasource JNDI name using -j JndiName'
        elif metric == 'DBConnectionPoolWaitTime':
            if jndiname is not None:
                return appsrv.querydbconnpoolwaittime(jndiname, warning, critical)
            else:
                return UNKNOWN, 'Please set datasource JNDI name using -j JndiName'
        elif metric == 'DBConnectionPoolWaitingThreadCount':
            if jndiname is not None:
                return appsrv.querydbconnpoolwaitingthreadcount(jndiname, warning, critical)
            else:
                return UNKNOWN, 'Please set datasource JNDI name using -j JndiName'
        elif metric == 'WebAuthenticationTime':
            return appsrv.querysecauthen(warning, critical)
        elif metric == 'WebAuthorizationTime':
            return appsrv.querysecauthor(warning, critical)
        elif metric == 'Heap':
            return appsrv.queryheapusage(warning, critical)
        elif metric == 'LiveSessions':
            return appsrv.querylivesessions()
        elif metric == 'SIBDestinations':
            if destination is not None:
                return appsrv.querysibdestination(destination, warning, critical)
            else:
                return UNKNOWN, 'Please set destination Name using -d DestName'
    else:
        return UNKNOWN, 'Not available statistics for server ' + serverfullname


def show(alertstatus, alertmessage):
    """Print Nagios Msg and exit with appropriate Return Code"""
    if alertstatus == OK:
        print 'OK - %s' % alertmessage
        sys.exit(OK)
    elif alertstatus == WARNING:
        print 'WARNING - %s' % alertmessage
        sys.exit(WARNING)
    elif alertstatus == CRITICAL:
        print 'CRITICAL - %s' % alertmessage
        sys.exit(CRITICAL)
    else:
        print 'UNKNOWN - %s' % alertmessage
        sys.exit(UNKNOWN)


if __name__ == '__main__':

    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3

    startingpath = ''
    # Assume the Plugin/Nagios Server runs in Linux OS
    if 'Linux' == platform.system():
        startingpath = '/tmp/'

    arguments = parsecmdargs()
    if arguments.command_name == 'retrieve':
        # Perfservlet Data Collector Operation
        status, message = retrieveperfxml(path=startingpath, cellname=arguments.CellName, ip=arguments.IPAddress,
                                          port=arguments.Port, httpprotocol=arguments.HttpProtocol,
                                          ignorecert=arguments.ignorecert,
                                          username=arguments.Username, password=arguments.Password)
        if status == OK:
            parseperfxml(path=startingpath, cellname=arguments.CellName)
        show(status, message)
    elif arguments.command_name == 'show':
        # Nagios Check Perfservlet Data stored in Python selve file
        status, message = queryperfdata(startingpath, arguments.CellName, arguments.NodeName, arguments.ServerName,
                                        arguments.Metric, arguments.Warning, arguments.Critical,
                                        destination=arguments.Destination, jndiname=arguments.JndiName)
        show(status, message)
