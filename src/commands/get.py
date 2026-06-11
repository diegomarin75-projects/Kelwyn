#Import libraries
import os
import debug

#Command metadatap
def Get():
  return {
    "name":"get",
    "description":"Get environment variable",
    "options":[
      {"type":"option","name":"Name","mandatory":False,"regex":r"^--name$","display":"--name <name>", "description":"Environment variable name to get"}
    ],
    "examples":[
      {"command":"get --name PATH"},
      {"command":"get --name JAVA_HOME"}
    ]
  }

#Execute command
def Execute(Options,Config):
  if Options.Name==None:
    print("Error: --name option is required")
    return False
  try:
    Value=os.environ.get(Options.Name)
    if Value==None:
      print(f"Environment variable {Options.Name} not found")
      return False
    else:
      print(Value)
      return True
  except Exception as Ex:
    print("Error getting environment variable:",Ex)
    return False