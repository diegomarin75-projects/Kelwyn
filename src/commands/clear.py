#Import libraries
import os
import terminal
import debug

#Command metadatap
def Get():
  return {
    "name":"clear",
    "description":"Clear console screen",
    "options":[],
    "examples":[
      {"command":"clear"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    terminal.ClearScreen()
  except Exception as Ex:
    print("Error clearing console:",Ex)
    return False
  return True