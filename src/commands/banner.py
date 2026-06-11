#Import libraries
import os
import terminal
import const
import debug

#Command metadatap
def Get():
  return {
    "name":"banner",
    "description":"Displays a banner with the shell name and version",
    "options":[],
    "examples":[
      {"command":"banner"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    terminal.Write(const.ASCII_BANNER.replace("<version>",const.VERSION)+"\n")
  except Exception as Ex:
    print("Error printing banner:",Ex)
    return False
  return True