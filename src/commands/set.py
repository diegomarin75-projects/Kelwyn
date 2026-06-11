#Import libraries
import os
import debug

#Command metadatap
def Get():
  return {
    "name":"set",
    "description":"Set environment variable",
    "options":[
      {"type":"positional","name":"Name","index":1,"mandatory":True,"display":"<name>", "description":"Environment variable name to set"},
      {"type":"positional","name":"Value","index":2,"mandatory":True,"display":"<value>", "description":"Value to set the environment variable to"}
    ],
    "examples":[
      {"command":"set PATH C:\\Windows\\System32", "description":"Set the PATH environment variable to C:\\Windows\\System32"},
      {"command":"set JAVA_HOME C:\\Program Files\\Java\\jdk-11.0.10", "description":"Set the JAVA_HOME environment variable to C:\\Program Files\\Java\\jdk-11.0.10"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    os.environ[Options.Name] = Options.Value
  except Exception as Ex:
    print("Error setting environment variable:",Ex)
    return False
  return True