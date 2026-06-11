#Import libraries
import os
import const
import terminal
import debug

#Command metadatap
def Get():
  return {
    "name":"wellcome",
    "description":"Displays wellcome message",
    "options":[],
    "examples":[
      {"command":"wellcome"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    for Line in const.WELCOME_LINES:
      terminal.Write(Line+"\n")
  except Exception as Ex:
    print("Error printing banner:",Ex)
    return False
  return True