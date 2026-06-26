#Import libraries
import os
import fnmatch
import const
import utils
import ansi
import terminal
import debug

#Command metadata
def Get():
  return {
    "name":"ls",
    "description":"List files and directories",
    "options":[
      {"type":"flag","name":"ListRecursive"     ,"regex":r"^-.*r.*$","display":"-r", "description":"Lists subdirectories recursively"},
      {"type":"flag","name":"ListHidden"        ,"regex":r"^-.*h.*$","display":"-h", "description":"Lists hidden files"},
      {"type":"flag","name":"ListForbidden"     ,"regex":r"^-.*f.*$","display":"-f", "description":"Lists forbidden files"},
      {"type":"flag","name":"ListVertical"      ,"regex":r"^-.*v.*$","display":"-v", "description":"Lists files one by one"},
      {"type":"positional","name":"FilePattern","index":1,"mandatory":False,"display":"<pattern>", "description":"File path pattern to match (accepts wildcards like '*' and '?')"},
    ],
    "examples":[
      {"command":"ls", "description":"List current directory"},
      {"command":"ls -r", "description":"List current directory and subdirectories recursively"},
      {"command":"ls -h", "description":"List current directory including hidden files"},
      {"command":"ls -f", "description":"List current directory including forbidden files"},
      {"command":"ls -v", "description":"List current directory one by one"},
      {"command":"ls *.txt", "description":"List all .txt files in current directory"},
      {"command":"ls /path/to/dir/*.log", "description":"List all .log files in specified directory"},
    ]
  }

#Execute command
def Execute(Options,Config):
  
  #Get options from configuration
  LsDirColor=Config.get("global_dir_color",const.DEFAULT_FOREGROUND_COLOR)
  LsFileColor=Config.get("global_file_color",const.DEFAULT_FOREGROUND_COLOR)
  LsErrorColor=Config.get("global_file_error_color",const.DEFAULT_FOREGROUND_COLOR)
  LsHeaderColor=Config.get("global_dir_header_color",const.DEFAULT_FOREGROUND_COLOR)
  
  #Get file patern as path and the pattern part
  if Options.FilePattern==None:
    FilePath=os.getcwd()
    FilePattern="*"
  elif Options.FilePattern==".":
    FilePath=os.getcwd()
    FilePattern="*"
  elif Options.FilePattern=="..":
    FilePath=os.getcwd()+os.sep+".."
    FilePattern="*"
  elif Options.FilePattern.endswith(os.sep) or os.path.isdir(Options.FilePattern):
    FilePath=Options.FilePattern
    FilePattern="*"
  elif Options.FilePattern.startswith(os.sep) and len(Options.FilePattern.split(os.sep))==2:
    FilePath=Options.FilePattern
    FilePattern="*"
  elif Options.FilePattern.startswith(os.sep) and len(Options.FilePattern.split(os.sep))>2:
    FilePath=os.sep.join(Options.FilePattern.split(os.sep)[:-1])
    FilePattern=Options.FilePattern.split(os.sep)[-1]
  elif len(Options.FilePattern.split(os.sep))==1:
    FilePath=os.getcwd()
    FilePattern=Options.FilePattern
  else:
    FilePath=os.sep.join(Options.FilePattern.split(os.sep)[:-1])
    FilePattern=Options.FilePattern.split(os.sep)[-1]
  
  #Not allowed to specify wildcards on path part
  if "*" in FilePath or "?" in FilePath:
    print("Error: Wildcards only allowed in the last part of the file pattern")
    return False
  
  #Get files and directories matching the pattern
  FileList=[]
  NewLine=False
  try:

    #Loop through files and directories
    for FileIndex,(Root,Dirs,Files) in enumerate(os.walk(FilePath)):
      
      #Get list of files and directories matching the pattern and options
      FileList=[]
      for Dir in Dirs:
        ListPath=os.path.join(Root,Dir)+os.sep
        if fnmatch.fnmatch(Dir, FilePattern):
          if Options.ListHidden or not Dir.startswith("."):
            if Options.ListForbidden or utils.IsAccessible(ListPath,QuickMode=True):
              FileList.append(Dir+os.sep)
      for File in Files:
        ListPath=os.path.join(Root,File)
        if fnmatch.fnmatch(File,FilePattern):
          if Options.ListHidden or not File.startswith("."):
            if Options.ListForbidden or utils.IsAccessible(ListPath,QuickMode=True):
              FileList.append(File)
      
      #Continue if no files or directories found
      if len(FileList)==0:
        continue

      #Sort and format file list
      FileList.sort(key=lambda x: "1"+x.lower() if x.endswith(os.sep) else "2"+x.lower())
      MaxLength=max([len(File)+1 for File in FileList])
      TerminalCols=terminal.GetTerminalSize()[1]
      FilesPerLine=max(1,TerminalCols//MaxLength)
      FileWidth=TerminalCols//FilesPerLine
      DisplayList=[File.ljust(FileWidth) for File in FileList]
      DisplayList=[]
      for File in FileList:
        File=File.ljust(FileWidth)
        if terminal.DisplayLength(File)<FileWidth:
          File=File+" "*(FileWidth-terminal.DisplayLength(File))
          File=ansi.SetFgColor(LsErrorColor)+File+ansi.ResetColor()
        elif File.strip().endswith(os.sep):
          File=ansi.SetFgColor(LsDirColor)+File+ansi.ResetColor()
        else:
          File=ansi.SetFgColor(LsFileColor)+File+ansi.ResetColor()
        DisplayList.append(File)

      #Get file metadata when listing vertically
      if Options.ListVertical:
        FileSizes=[]
        for Index,File in enumerate(FileList):
          if File.strip().endswith(os.sep):
            Size=""
          else:
            Size=f"{os.path.getsize(os.path.join(Root,File.strip()))} bytes"
          FileSizes.append(Size)
        MaxSizeLength=max([len(Size) for Size in FileSizes])
        DisplayList=[File.rjust(FileWidth)+FileSizes[Index].rjust(MaxSizeLength) for Index,File in enumerate(DisplayList)]

      #Print directory header if listing recursively
      if Options.ListRecursive and FileIndex>0:
        if Root.startswith(FilePath):
          DirName=Root[len(FilePath):].strip(os.sep)+":"
        else:
          DirName=Root.strip(os.sep)+":"
        print(ansi.SetFgColor(LsHeaderColor)+DirName+ansi.ResetColor())
      
      #Print file list
      NewLine=False
      if Options.ListVertical:
        for File in DisplayList:
          print(f"{File}")
          NewLine=True
      else:
        for Index,File in enumerate(DisplayList):
          print(File, end="",flush=True)
          NewLine=False
          if (Index+1)%FilesPerLine==0:
            print()
            NewLine=True
      
      #Break if not listing recursively
      if not Options.ListRecursive:
        break

      #Separate directories if listing recursively
      if NewLine==False:
        print()
        NewLine=True
      print()
  
  #Exception handling
  except Exception as Ex:
    print(f"Error listing files: {Ex}")
    return False
  
  #New line after listing if not already printed
  if NewLine==False and len(FileList)>0:
    print()

  #Return success
  return True
