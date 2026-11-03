#Import libraries
import os
import terminal
import const
import debug
import importlib

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
    ConstModule=importlib.import_module("const")
    AsciiBanner=getattr(ConstModule,Config["ascii_banner"])
    terminal.Write(AsciiBanner.replace("<version>",Config["version"])+"\n")
  except Exception as Ex:
    print("Error printing banner:",Ex)
    return False
  return True