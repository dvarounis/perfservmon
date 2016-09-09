#perfservmon

*Perfservmon* is  a *Nagios Plugin* for *IBM Websphere Application Server(WAS)* using the perfservlet web application that comes with each WAS 
installation.

##Prerequisites

1. Install in one WAS server of your WebSphere Cell the PerfServletApp.ear located in `<WAS_ROOT>/installableApps`, i.e. in `/opt/IBM/WebSphere/AppServer/installableApps` in a Unix System.

2. At least Python version 2.7 at the Nagios host

The plugin is tested to work with WAS version 8.5

##Installation

1. Copy the `perfservmon.py` file in `$USER1$` path, which is the plugins path. You will propably find the value of this variable in Nagios `resource.cfg` file.

2. Add the following lines in Nagios `command.cfg` file:

```
#Check_perfservlet commands

define command{
        command_name    check_perfserv_retriever
        command_line    $USER1$/perfservmon.py -C $ARG1$ retrieve -N $ARG2$ -P $ARG3$
        }

define command{
        command_name    check_perfserv_show
        command_line    $USER1$/perfservmon.py -C $ARG1$ show -n $ARG2$ -s $ARG3$ -M $ARG4$ -c $ARG5$ -w $ARG6$
        }

define command{
        command_name    check_perfserv_show_sib
        command_line    $USER1$/perfservmon.py -C $ARG1$ show -n $ARG2$ -s $ARG3$ -M SIBDestinations -d $ARG4$ -c $ARG5$ -w $ARG6$
        }
```

