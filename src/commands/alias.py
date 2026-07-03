#Import libraries
import debug

#Command metadatap
def Get():
  return {
    "name":"alias",
    "description":"Show, set, enable, or disable aliases",
    "options":[
      {"type":"flag","name":"Show","regex":r"^--show$","display":"--show", "description":"Show all defined aliases"},
      {"type":"flag","name":"Disable","regex":r"^--disable$","display":"--disable", "description":"Disable alias <name>"},
      {"type":"flag","name":"Enable","regex":r"^--enable$","display":"--enable", "description":"Enable alias <name>"},
      {"type":"positional","name":"Name","index":1,"mandatory":False,"display":"<name>", "description":"Alias name"},
      {"type":"positional","name":"Value","index":2,"mandatory":False,"display":"<value>", "description":"Alias command value"}
    ],
    "examples":[
      {"command":"alias --show", "description":"Show all aliases (enabled aliases marked as 'enbl', disabled as 'dsbl')"},
      {"command":"alias dir ls -v", "description":"Create alias 'dir'"},
      {"command":"alias dir --disable", "description":"Disable alias 'dir'"},
      {"command":"alias dir --enable", "description":"Enable alias 'dir'"}
    ]
  }

#Execute command
def Execute(Options,Config):
  
  #Exception handling
  try:

    #Show aliases
    if Options.Show==True:
      if Options.Name!=None or Options.Value!=None or Options.Disable==True or Options.Enable==True:
        print("Error: --show cannot be combined with other options")
        return False
      if len(Config["aliases"])==0:
        print("No aliases defined")
        return True
      MaxNameLength=max([len(Name) for Name in Config["aliases"].keys()])
      for Name in sorted(Config["aliases"].keys()):
        AliasDef=Config["aliases"][Name]
        Enabled=AliasDef["enabled"]
        Command=AliasDef["command"]
        Status=("enbl" if Enabled else "dsbl")
        print(f"{Name.ljust(MaxNameLength)} ({Status}) : {Command}")

    #Enable/disable alias
    elif Options.Disable==True or Options.Enable==True:
      if Options.Disable==True and Options.Enable==True:
        print("Error: --disable and --enable cannot be used together")
        return False
      if Options.Name==None:
        print("Error: alias name is required")
        return False
      if Options.Value!=None:
        print("Error: value cannot be provided with --disable/--enable")
        return False
      if Options.Name not in Config["aliases"]:
        print(f"Error: alias '{Options.Name}' not found")
        return False
      Config["aliases"][Options.Name]["enabled"]=(True if Options.Enable==True else False)

    #Set alias <name> <value>
    elif Options.Name!=None and Options.Value!=None:
      Config["aliases"][Options.Name]={"command":Options.Value,"enabled":True}
    
    #Error: invalid combination of options
    else:
      print("Error: invalid combination of options")
      return False

  #Exception handler
  except Exception as Ex:
    print("Error managing alias:",Ex)
    return False
  
  #Return success
  return True