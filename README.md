perfservmon
===========
*Perfservmon* is  a *Nagios Plugin* for *IBM Websphere Application Server(WAS)* using the perfservlet web application that comes with each WAS 
installation.

Prerequisites
-------------
1. Install in one WAS server of your WebSphere Cell the PerfServletApp.ear located in `<WAS_ROOT>/installableApps`, i.e. in `/opt/IBM/WebSphere/AppServer/installableApps` in a Unix System.

2. At least Python version 2.7 at the Nagios host

The plugin is tested to work with WAS version 8.5
