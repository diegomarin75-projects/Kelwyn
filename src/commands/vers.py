#Import libraries
import debug

#Command metadatap
def Get():
  return {
    "name":"vers",
    "description":"Print current shell version",
    "options":[],
    "examples":[
      {"command":"vers"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    print(Config["version"])
  except Exception as Ex:
    print("Error printing version:",Ex)
    return False
  return True