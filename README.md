#perfservmon

*Perfservmon* is  a *Nagios Plugin* for *IBM Websphere Application Server(WAS)* using the perfservlet web application that comes with each WAS 
installation.

The plugin can monitor the following WAS metrics of a WebSphere Cell:

- Heap Usage
- Web Container Thread Pool Usage
- ORB Thread Pool Usage
- JDBC Connection Pool Usage
- Live HTTP Sessions
- JMS SIB Destination(Queue, Topic) Metrics

##Prerequisites

1. Install in one WAS server of your WebSphere Cell the PerfServletApp.ear located in `<WAS_ROOT>/installableApps`, i.e. in `/opt/IBM/WebSphere/AppServer/installableApps` in a Unix System.

2. At least Python version 2.7 at the Nagios host

The plugin is tested to work with WAS version 8.5.

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

##Usage

#### Define Collector Service 
First add the following service definition at the WAS Server or the DMgr Server(for ND Architecture) Nagios Config file:

```
define service{
        use                             local-service        
        host_name                       <WAS_Host>
        service_description             Collect PerfServlet data from Cell
        check_command                   check_perfserv_retriever!<WAS_Cell_Name>!<PerfServ_hostname>!<PerfServ_Port>
        }
 ```
 Where:
 * WAS_Cell_Name = The name of the Websphere Cell
 * PerfServ_hostname = The IP Address/Hostname of where perfservlet Application runs
 * PerfServ_Port = The Port of where perfservlet Application runs
 
#### Sample Service Definitions for WAS Metrics

* Heap Usage

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS Heap usage
        check_command                   check_perfserv_show!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!Heap!<Critical Percentage>!<Warning Percentage>
        }
```
 
* Web Container Thread Pool

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS WebContainer ThreadPool Usage
        check_command                   check_perfserv_show!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!WebContainer!<Critical Percentage>!<Warning Percentage>
        }
```

* JDBC Connection Pool

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS ConnectionPool Usage
        check_command                   check_perfserv_show!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!DBConnectionPool!<Critical Percentage>!<Warning Percentage>
        }
```

