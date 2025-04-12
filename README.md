# moisture-sensor-server
A project by Joshua Corrao & Nicholas Wendt

## Objective
MSS is meant to be a lightweight webserver deployed through docker in a lightweight environment such as a raspberry pi. 

## The hardware
Based around the esp32-s3 xiao from Seeed Studio, but project could be adapted to other boards. 
### Parts list
 - 3d printed case - 

### TODOs:
 - parts list
 - upload case stls and instructions. 
 - 

## The server
Fast api on postgress with SqlAlchemy in between. Alembic used for db migrations. 
###
Included MCU code is provided. Deployed onto the xiao board with circuitpython 9.xx

### TODOs:
- Clean up alembic with a nice squash now that this is 1.0-ish

## The frontend
Repo name: moisture-sensor-ui

It's not meant to be pretty. Just get things moving. 

## Other relevant Things
### Kicad board designgs
Forthcomming... 
