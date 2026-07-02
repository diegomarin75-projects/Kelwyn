#Import libraries
import os
import terminal
import debug

#Command metadatap
def Get():
  return {
    "name":"set",
    "description":"Set environment variable",
    "options":[
      {"type":"positional","name":"Name","index":1,"mandatory":True,"display":"<name>", "description":"Environment variable name to set"},
      {"type":"positional","name":"Value","index":2,"mandatory":True,"display":"<value>", "description":"Value to set the environment variable to"},
      {"type":"flag","name":"Insert","regex":r"^--insert$","display":"--insert", "description":"Inserts value at beginning of current variable value, if not present already"},
      {"type":"flag","name":"Append","regex":r"^--append$","display":"--append", "description":"Inserts value at ending of current variable value, if not present already"}
    ],
    "examples":[
      {"command":"set PATH C:\\Windows\\System32", "description":"Set the PATH environment variable to C:\\Windows\\System32"},
      {"command":"set JAVA_HOME C:\\Program Files\\Java\\jdk-11.0.10", "description":"Set the JAVA_HOME environment variable to C:\\Program Files\\Java\\jdk-11.0.10"}
    ]
  }

#Execute command
def Execute(Options,Config):
  
  #Environment variable
  EnvVar=Options.Name.upper()
  
  #Setting of clipboard 
  if EnvVar == "CLIPBOARD":
    
    #Exception handling
    try:

      #Insert mode
      if Options.Insert==True:
        CurrentValue=terminal.ClipboardGet()
        if CurrentValue.find(Options.Value)==-1:
          terminal.ClipboardSet(Options.Value+CurrentValue)
      
      #Append mode
      elif Options.Append==True:
        CurrentValue=terminal.ClipboardGet()
        if CurrentValue.find(Options.Value)==-1:
          terminal.ClipboardSet(CurrentValue+Options.Value)
      
      #Set mode
      else:
        terminal.ClipboardSet(Options.Value)
    
    #Exception handler
    except Exception as Ex:
      print("Error copying into clipboard:",Ex)
      return False
  
  #Setting of environment variables
  else:
    
    #Exception handing
    try:
      
      #Insert mode
      if Options.Insert==True:
        CurrentValue=os.environ.get(EnvVar, "")
        if CurrentValue.find(Options.Value)==-1:
          os.environ[EnvVar]=Options.Value+CurrentValue
      
      #Append mode
      elif Options.Append==True:
        CurrentValue=os.environ.get(EnvVar, "")
        if CurrentValue.find(Options.Value)==-1:
          os.environ[EnvVar]=CurrentValue+Options.Value
      
      #Set mode
      else:
        os.environ[EnvVar] = Options.Value
    
    #Exception handler
    except Exception as Ex:
      print("Error setting environment variable:",Ex)
      return False
  
  #Return success
  return True