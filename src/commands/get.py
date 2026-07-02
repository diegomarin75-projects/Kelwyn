#Import libraries
import os
import debug

#Command metadatap
def Get():
  return {
    "name":"get",
    "description":"Get environment variable",
    "options":[
      {"type":"positional","name":"Name","index":1,"mandatory":True,"display":"<name>", "description":"Environment variable name to get"}
    ],
    "examples":[
      {"command":"get PATH"},
      {"command":"get PYTHONPATH"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    Value=os.environ.get(Options.Name,"")
    print(Value)
    return True
  except Exception as Ex:
    print("Error getting environment variable:",Ex)
    return False