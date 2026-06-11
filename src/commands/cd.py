#Import libraries
import os
import debug

#Command metadatap
def Get():
  return {
    "name":"cd",
    "description":"Change current working directory",
    "options":[
      {"type":"positional","name":"DirPath","index":1,"mandatory":True,"display":"<path>", "description":"Path to change to (use '..' for parent directory and '~' for home directory)"},
    ],
    "examples":[
      {"command":"cd c:\\users\\user\\documents", "description":"Change to the documents directory"},
      {"command":"cd /home/user/documents", "description":"Change to the documents directory"},
      {"command":"cd ..", "description":"Change to the parent directory"},
      {"command":"cd ~", "description":"Change to the home directory"}
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    os.chdir(Options.DirPath)
  except Exception as e:
    print("Error changing directory:",e)
    return False
  return True