#Import libraries
import os
import const
import utils
import debug

#Selection routine
def Selector():
  return [
    {"type":"path","regex":r'^cd\s+@token$',"completer":lambda Token,Config: Completer(Token,Config,DirsOnly=True)},
    {"type":"fallback","regex":None,"completer":Completer}
  ]

#Completer routine
def Completer(Token,Config,DirsOnly=False):

  #Get colors
  DirColor=Config.get("global_dir_color",const.DEFAULT_FOREGROUND_COLOR)
  FileColor=Config.get("global_file_color",const.DEFAULT_FOREGROUND_COLOR)

  #Init result
  Options=[]

  #Get directory and partial name
  if os.path.dirname(Token) in ["","."]:
    CurrentDir=True
    Dir="."
  else:
    CurrentDir=False
    Dir=os.path.dirname(Token)
  PartialName=os.path.basename(Token)

  #Directory always end with os.sep
  if Dir.endswith(os.sep)==False:
    Dir+=os.sep

  #List directory and filter by partial name
  try:
    
    #Get entries in directory
    Entries=os.listdir(Dir)
    debug.Get().Send(f"Token: {Token!r}, Dir: {Dir!r}, PartialName: {PartialName!r}, Entries: {Entries!r}")

    #Filter entries by partial name and add os.sep at the end if it's a directory
    if DirsOnly==True:
      Completions=[Dir+Entry+os.sep for Entry in Entries if Entry.startswith(PartialName) and os.path.isdir(os.path.join(Dir,Entry))]
    else:
      Completions=[Dir+Entry+os.sep if os.path.isdir(os.path.join(Dir,Entry)) else Dir+Entry for Entry in Entries if Entry.startswith(PartialName)]
    debug.Get().Send(f"Completions: {Completions!r}")

    #Filter out inaccessible paths (e.g. due to permissions)
    Completions=[Comp for Comp in Completions if utils.IsAccessible(Comp,QuickMode=True)]
    
    #Remove .\ or ./ at beginning of completions for better display
    Completions=[Comp[2:] if Comp.startswith("."+os.sep) else Comp for Comp in Completions]

    #Sort directories first, then files, and ignore case
    Completions.sort(key=lambda x: (not os.path.isdir(x), x.lower()))

    #Buid options
    Options=[{"text":Opt[len(Dir):] if CurrentDir==False and len(Dir)<len(Opt) else Opt,"value":Opt,"color":DirColor if Opt.endswith(os.sep) else FileColor} for Opt in Completions]

  #Exception handling (e.g. directory not found)
  except Exception as e:
    debug.Get().Send(f"Exception in FileOrPathCompleter: {str(e)}")
  
  #Return Options
  return Options