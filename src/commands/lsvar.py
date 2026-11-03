#Import libraries
import os
import debug
import fnmatch

#Command metadatap
def Get():
  return {
    "name":"get",
    "description":"List environment variables",
    "options":[
      {"type":"positional","name":"Filter","index":1,"mandatory":False,"display":"<filter>", "description":"Wildcard pattern filter"}
    ],
    "examples":[
      {"command":"lsvar"},
      {"command":"lsvar *PYTHON*"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    if Options.Filter==None:
      Filter="*"
    else:
      Filter=Options.Filter
    Vars=[{"name":Key,"value":Value} for Key,Value in os.environ.items() if fnmatch.fnmatch(Key,Filter)]
    MaxLength=max([len(Var["name"]) for Var in Vars])
    for Var in Vars:
      Name=Var["name"]
      Value=Var["value"]
      print(f"{Name.ljust(MaxLength)} : {Value}")
    return True
  except Exception as Ex:
    print("Error reading environment variables:",Ex)
    return False