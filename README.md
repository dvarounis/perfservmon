# Perfservmon


*Perfservmon* is  a *Nagios Plugin* for *IBM Websphere Application Server(WAS)* using the perfservlet web application that comes with each WAS 
installation.

The plugin can monitor the following WAS metrics of a WebSphere Cell:

- Web authentication time
- Web authorization time
- Heap Usage
- Web Container Thread Pool Usage
- Web Container Declared Threads Hung
- ORB Thread Pool Usage
- JDBC Data Source Connection Pool Usage
- JDBC Data Source Connection Pool Use Time
- JDBC Data Source Connection Pool Wait Time
- JDBC Data Source Connection Pool Waiting Threads
- Live HTTP Sessions
- JMS SIB Destination(Queue, Topic) Metrics

## Prerequisites

1. **Perfservlet App**
    Install the PerfServletApp.ear in one WAS server of your WebSphere Cell.
    This is located in `<WAS_ROOT>/installableApps`, i.e. this would be in `/opt/IBM/WebSphere/AppServer/installableApps` in a Unix System.
2. **Python version 2.7** installed at the Nagios host

The plugin is tested to work with WAS version 8.5. Here's a [script to install perfServlet](https://docs.google.com/document/d/1Y83R0zgeb-ns1zIb_eCzB23ajzjmVphChCxOim56hjw/edit#bookmark=id.mgnntqet769o)

## Setup

1. Copy the `perfservmon.py` file in `$USER1$` path, which is the plugins path. You will propably find the value of this variable in Nagios `resource.cfg` file (usually this is a `libexec` directory).

2. Add the following lines in Nagios `command.cfg` file:

```
#Check_perfservlet commands
#The -H -u -p parameters are optional
#depending on whether you use https and/or Basic Auth credentials to access the perfservlet

define command{
        command_name    check_perfserv_retriever
        command_line    $USER1$/perfservmon.py -C $ARG1$ retrieve -N $ARG2$ -P $ARG3$ -H $ARG4$ -u $ARG5$ -p $ARG6$
        }

define command{
        command_name    check_perfserv_show
        command_line    $USER1$/perfservmon.py -C $ARG1$ show -n $ARG2$ -s $ARG3$ -M $ARG4$ -c $ARG5$ -w $ARG6$
        }

define command{
        command_name    check_perfserv_show_dcp
        command_line    $USER1$/perfservmon.py -C $ARG1$ show -n $ARG2$ -s $ARG3$ -M DBConnectionPoolPercentUsed -j $ARG4$ -c $ARG5$ -w $ARG6$
        }

define command{
        command_name    check_perfserv_show_sib
        command_line    $USER1$/perfservmon.py -C $ARG1$ show -n $ARG2$ -s $ARG3$ -M SIBDestinations -d $ARG4$ -c $ARG5$ -w $ARG6$
        }
```

## Usage

#### Define Collector Service 
Before defining a service using check_perfserv_show it is required to add the following service definition at the WAS Server or the DMgr Server(for ND Architecture) Nagios Config file:

```
define service{
        use                             local-service        
        host_name                       <WAS_Host>
        service_description             Collect PerfServlet data from Cell
        check_command                   check_perfserv_retriever!<WAS_Cell_Name>!<PerfServ_hostname>!<PerfServ_Port>![http|https]!userid!passwd![--ignorecert]
        }
 ```
 Where:
 * WAS_Cell_Name = The name of the Websphere Cell
 * PerfServ_hostname = The IP Address/Hostname of where perfservlet Application runs
 * PerfServ_Port = The Port of where perfservlet Application runs
 
 Optionally set the HTTP protocol(http or https) and/or the Basic Authentication credentials for accessing the PerfServlet Application.
 In the case of an https connection you may use (although not recommended) the --ignorecert option to ignore any TLS certificate issues. 
 
 This is the check that collects all the relevant perfserv data of all nodes/servers from perfservlet and stores them localy as a Python selve file.
 
 In case you want, for example, to change the check interval of the above service so that all WAS data are refreshed more frequently you may add the following lines in Nagios template.cfg:
  
``` 
define service{
        name                            collector-service           ; The name of this service template
        use                             local-service         ; Inherit default values from the local-service definition
        max_check_attempts              2                       ; Re-check the service up to 2 times in order to determine its final (hard) state
        normal_check_interval           3                       ; Check the service every 3 minutes under normal conditions
        retry_check_interval            1                       ; Re-check the service every minute until a hard state can be determined
        register                        0                       ; DONT REGISTER THIS DEFINITION - ITS NOT A REAL SERVICE, JUST A TEMPLATE!
        }
 ```

Then the collector service definition should be like the following:

```
define service{
        use                             collector-service        
        host_name                       <WAS_Host>
        service_description             Collect PerfServlet data from Cell
        check_command                   check_perfserv_retriever!<WAS_Cell_Name>!<PerfServ_hostname>!<PerfServ_Port>![http|https]!userid!passwd
        }
 ```
 
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

* JDBC Connection Pools

Shows all the available connection pools of the WAS Server and show an alert when any of them exceeds the percentage limits.

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS ConnectionPool Usage
        check_command                   check_perfserv_show!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!DBConnectionPoolPercentUsed!<Critical Percentage>!<Warning Percentage>
        }
```

Shows a specific connection pool of the WAS Server (specified with <JNDI_name>) and show an alert when its usage exceeds the percentage limits.

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS ConnectionPool JNDI_name Usage
        check_command                   check_perfserv_show_dcp!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!<JNDI_name>!<Critical Percentage>!<Warning Percentage>
        }
```

* Total Live HTTP Sessions

Shows the Total Live HTTP Sessions together with the individual(per Module HTTP Sessions). Show an alert when the Total Sessions exceed the limits.  

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS Http Live Sessions
        check_command                   check_perfserv_show!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!LiveSessions!<Critical No of Sessions>!<Warning No of Sessions>
        }
```

* ORB Thread Pool Usage

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             WAS ORB ThreadPool Usage
        check_command                   check_perfserv_show!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!ORB!<Critical Percentage>!<Warning Percentage>
        }
```

* JMS SIB Destinations (Queue, Topic)

```
define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             My Topic Space
        check_command                   check_perfserv_show_sib!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!<MyTopicSpaceName>!<No_Messages_Critical>!<No_Messages_Warning>
        }

define service{
        use                             local-service
        host_name                       <WAS_Host>
        service_description             My Exception Destination
        check_command                   check_perfserv_show_sib!<WAS_Cell_Name>!<WAS_Node_Name>!<WAS_server_name>!_SYSTEM.Exception.Destination.<WAS_Node_Name>.<WAS_server_name>-<SIBus_Name>!<No_Messages_Critical>!<No_Messages_Warning>
        }
```
