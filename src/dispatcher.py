  # ---------------------------------------------------------------------------------------------------------------------
# dispatcher.py: Command dispatcher
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import os
import re
import io
import sys
import const
import shutil
import debug
import utils
import parser
import evaluator
import subprocess
import threading
import terminal
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

# ---------------------------------------------------------------------------------------------------------------------
# Command options class
# ---------------------------------------------------------------------------------------------------------------------
class CommandOptions:
  def __str__(self):
    return f"CommandOptions({self.__dict__})"

# ---------------------------------------------------------------------------------------------------------------------
# Dispatcher result class
# ---------------------------------------------------------------------------------------------------------------------
class DispatcherResult:
  
  #Result events
  OK               = 0
  TERMINATE        = 1
  RESTART          = 2
  DISPATCHER_ERROR = 3
  COMMAND_ERROR    = 4
  EXTERNAL_ERROR   = 5
  
  #Constructor class
  def __init__(self,Event=None,RetCode=None,Output=None):
    self.Event=Event
    self.RetCode=RetCode
    self.Output=Output
  
  #Static methods to create result objects for each event type
  @staticmethod
  def Ok(Output=None):
    return DispatcherResult(Event=DispatcherResult.OK,Output=Output)
  @staticmethod
  def Terminate():
    return DispatcherResult(Event=DispatcherResult.TERMINATE)
  @staticmethod
  def Restart():
    return DispatcherResult(Event=DispatcherResult.RESTART)
  @staticmethod
  def DispatcherError(Output):
    OutputLn=(Output.strip("\n") if Output!=None else "Unknown dispatcher error")
    return DispatcherResult(Event=DispatcherResult.DISPATCHER_ERROR,Output=OutputLn)
  @staticmethod
  def CommandError(Output=None):
    return DispatcherResult(Event=DispatcherResult.COMMAND_ERROR,Output=Output)
  @staticmethod
  def ExternalError(RetCode,Output=None):
    return DispatcherResult(Event=DispatcherResult.EXTERNAL_ERROR,RetCode=RetCode,Output=Output)
  def __str__(self):
    EventName={ \
      DispatcherResult.OK:"OK", \
      DispatcherResult.TERMINATE:"TERMINATE", \
      DispatcherResult.DISPATCHER_ERROR:"DISPATCHER_ERROR", \
      DispatcherResult.COMMAND_ERROR:"COMMAND_ERROR", \
      DispatcherResult.EXTERNAL_ERROR:"EXTERNAL_ERROR" \
    }.get(self.Event,self.Event)
    return f"DispatcherResult(Event={EventName},RetCode={self.RetCode},Output={self.Output})"

# ---------------------------------------------------------------------------------------------------------------------
# Command dispatcher class
# ---------------------------------------------------------------------------------------------------------------------
class CommandDispatcher:
  
  # -------------------------------------------------------------------------------------------------------------------
  # Constructor
  # Args:
  # - CommandsFolder (string): Path to folder containing command modules
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  def __init__(self,CommandsFolder,Config):

    #Load parser
    self.Config=Config
    self.Parser=parser.CommandParser(Config)
    self.Evaluator=evaluator.Evaluator(Config)

    #Load command modules on commands folder
    self.CommandDir={}
    for PythonFile in Path(CommandsFolder).glob("*.py"):
      Module=utils.LoadPythonModule(PythonFile)
      if Module!=None:
        CommandGet=(Module.Get if hasattr(Module,"Get") else None)
        CommandExecute=(Module.Execute if hasattr(Module,"Execute") else None)
        self.CommandDir[PythonFile.stem]={"get":CommandGet,"execute":CommandExecute}
    debug.Get().Send(f"Loaded command modules: {list(self.CommandDir.keys())}")

  # -------------------------------------------------------------------------------------------------------------------
  # Parse command options
  # Args:
  # - OptionDef (list): List of option definitions (from command metadata)
  # - Tokens (list): List of tokens parsed from the command string
  # Returns:
  # - bool: True if options were parsed successfully, False otherwise
  # - string: Error message if parsing failed, empty string otherwise
  # - CommandOptions: Object with parsed options as attributes, or None if parsing failed
  # -------------------------------------------------------------------------------------------------------------------
  def ParseOptions(self,OptionDef,Tokens):
    
    #Init variables
    Options=CommandOptions()
    PositionIndex=1

    #Initialize options with default values
    for Opt in OptionDef:
      if Opt["type"]=="flag":
        setattr(Options,Opt["name"],False)
      elif Opt["type"]=="option":
        setattr(Options,Opt["name"],None)
      elif Opt["type"]=="positional":
        setattr(Options,Opt["name"],None)

    #Parse tokens
    Index=0
    while Index<len(Tokens):
      if Index==0:
        Index+=1
        continue
      if Tokens[Index]["type"]!="string":
        Message=f"Unexpected token '{Tokens[Index]['value']}' at position {Index}"
        return False,Message,None
      OptionRead=None
      for Opt in OptionDef:
        if Opt["type"]=="flag" and re.match(Opt["regex"],Tokens[Index]["value"]):
          setattr(Options,Opt["name"],True)
          OptionRead=Opt["type"]
        elif Opt["type"]=="option" and re.match(Opt["regex"],Tokens[Index]["value"]):
          if len(Tokens)<=Index+1:
            Message=f"Option {Opt['display']} requires a value"
            return False,Message,None
          elif Tokens[Index+1]["type"]!="string":
            Message=f"Option {Opt['display']} requires a value of type string"
            return False,Message,None
          else:
            setattr(Options,Opt["name"],Tokens[Index+1]["value"])
            OptionRead=Opt["type"]
            break
      if OptionRead=="flag":
        Index+=1
      elif OptionRead=="option":
        Index+=2
      else:
        for Opt in OptionDef:
          if Index<len(Tokens) and Opt["type"]=="positional" and PositionIndex==Opt["index"]:
            setattr(Options,Opt["name"],Tokens[Index]["value"])
            PositionIndex+=1
            Index+=1
            OptionRead=Opt["type"]
            break
      if OptionRead==None:
        Message=f"Unexpected option: {Tokens[Index]['value']}"
        return False,Message,None
    
    #Error if mandatory positional options are not provided
    for Opt in OptionDef:
      if Opt["type"]=="positional" and Opt["mandatory"]==True and getattr(Options,Opt["name"])==None:
        Message=f"Missing required option: {Opt['display']} ({Opt['description']})"
        return False,Message,None
    
    #Return options object
    return True,"",Options

  # -------------------------------------------------------------------------------------------------------------------
  # Print command list and description
  # -------------------------------------------------------------------------------------------------------------------
  def PrintCommandList(self):
    MaxCmdLength=max([len(Cmd) for Cmd in self.CommandDir.keys()]) if len(self.CommandDir)>0 else 0
    Output="Available commands:\n"
    for Cmd in self.CommandDir.keys():
      Description=self.CommandDir[Cmd]['get']()['description'].split("\n")[0] if self.CommandDir[Cmd]['get']!=None else "No description available"
      Output+=f"{Cmd.ljust(MaxCmdLength)} : {Description}\n"
    Output+=f"{"exit".ljust(MaxCmdLength)} : Exit the shell\n"
    Output+=f"{"init".ljust(MaxCmdLength)} : Restart the shell\n"
    Output+="Use 'help <command>' or '<command> --help' for more information on command usage"
    return Output
  
  # -------------------------------------------------------------------------------------------------------------------
  # Print command help
  # Args:
  # - Tool (string): Command name to print help for
  # Returns:
  # - bool: True if help was printed successfully, False otherwise
  # - string: Produced output if help was printed successfully, error message otherwise
  # -------------------------------------------------------------------------------------------------------------------
  def PrintHelp(self,Tool):

    #Print help for exit command
    if Tool=="exit":
      Output="exit - Exit the shell\n\nUsage:\n  exit"
      return True,Output
    
    #Print help for init command
    if Tool=="init":
      Output="init - Restart the shell\n\nUsage:\n  init"
      return True,Output
    
    #Check if command exists and has Get() function
    if Tool not in self.CommandDir:
      Output=f"Command '{Tool}' is not implemented"
      return False,Output
    if self.CommandDir[Tool]["get"]==None:
      Output=f"No help defined for command '{Tool}'"
      return False,Output

    #Get command metadata
    CommandMetaData=self.CommandDir[Tool]["get"]()

    #Initialize help output with command name and description
    Output=f"{CommandMetaData['name']} - {CommandMetaData['description']}\n\n"

    #Print command usage
    Usage=f"{CommandMetaData['name']}"
    for Opt in CommandMetaData["options"]:
      if Opt["type"]=="flag":
        Usage+=f" [{Opt['display']}]"
      elif Opt["type"]=="positional":
        if Opt["mandatory"]==True:
          Usage+=f" {Opt['display']}"
        else:
          Usage+=f" [{Opt['display']}]"
    Output+=f"Usage:\n  {Usage}\n\n"
    
    #Print command options
    Options=""
    MaxOptionLength=max([len(Opt["display"]) for Opt in CommandMetaData["options"]]) if len(CommandMetaData["options"])>0 else 0
    for Opt in CommandMetaData["options"]:
      if Opt["type"]=="flag":
        Options+=f"  {Opt['display'].ljust(MaxOptionLength)} : {Opt['description']}\n"
      elif Opt["type"]=="positional":
        Options+=f"  {Opt['display'].ljust(MaxOptionLength)} : {Opt['description']}\n"
    if Options!="":
      Output+=f"Options:\n{Options}\n"

    #Print command examples
    if "examples" in CommandMetaData and len(CommandMetaData["examples"])>0:
      Examples=""
      MaxExampleLength=max([len(Ex["command"]) for Ex in CommandMetaData["examples"]]) if len(CommandMetaData["examples"])>0 else 0
      for Ex in CommandMetaData["examples"]:
        Examples+=f"  {Ex['command'].ljust(MaxExampleLength)}"+(f" : {Ex['description']}" if "description" in Ex else "")+"\n"
      Output+=f"Examples:\n{Examples}"
    
    #Return help output
    return True,Output

  # ---------------------------------------------------------------------------
  # Replace aliases in command line
  # Args:
  # - Cmd (string): Command line to process
  # - MultiCmd (bool): True to replace multi-command aliases, False to replace single-command aliases
  # ---------------------------------------------------------------------------
  def ReplaceAliases(self,Command,MultiCmd):
    Cmd=Command.strip()
    while True:
      FoundAlias=False
      for Alias in self.Config["aliases"]:
        if self.Config["aliases"][Alias]["enabled"]==True and Cmd.startswith(Alias) \
        and ((MultiCmd==True and self.Config["aliases"][Alias]["command"].find(";")!=-1) \
        or   (MultiCmd==False and self.Config["aliases"][Alias]["command"].find(";")==-1)):
          if self.Config["aliases"][Alias]["command"].find("<<line>>")!=-1:
            Cmd=self.Config["aliases"][Alias]["command"].replace("<<line>>",Cmd[len(Alias):].strip())
          else:
            Cmd=self.Config["aliases"][Alias]["command"]+Cmd[len(Alias):]
          FoundAlias=True
          break
      if FoundAlias==False:
        break
    return Cmd

  # ---------------------------------------------------------------------------
  # Execute a command and return its output and return code
  # Args:
  # - Command (string or list): Command to execute as a string in shell mode or list or string in program mode
  # - Shell (bool, default True): Execute comand in shell mode (True) or program mode (False)
  # - Capture (string, default None): Whether to capture and return command output (1=stdout, 2=stderr, all=both, None=No capture)
  # - Detached (bool, default False): Whether to launch process as detached
  # Returns:
  # - boolean: True=Process executed, False=Exception
  # - int: Command return code
  # - string: Command output when Capture is not None, Process Pid when Detached is True, else None
  # ---------------------------------------------------------------------------
  def ExecProcess(self,Command,Shell=True,Capture=None,Detached=False):
    debug.Get().Send(f"Execute process call: {Command} Shell={Shell} Capture={Capture} Detached={Detached}")
    try:
      if Capture=="1":
        Proc=subprocess.Popen(Command,shell=Shell,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding="utf-8")
        Output=Proc.communicate()[0]
        ReturnCode=Proc.returncode
        Status=True
      elif Capture=="2":
        Proc=subprocess.Popen(Command,shell=Shell,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,encoding="utf-8")
        Output=Proc.communicate()[1]
        ReturnCode=Proc.returncode
        Status=True
      elif Capture=="all":
        Proc=subprocess.Popen(Command,shell=Shell,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8")
        Output=Proc.communicate()[0]
        ReturnCode=Proc.returncode
        Status=True
      elif Detached==True:
        Proc=subprocess.Popen(Command,shell=Shell,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,start_new_session=True)
        Output=str(Proc.pid)
        ReturnCode=None
        Status=True
      else:
        Proc=subprocess.Popen(Command,shell=Shell,encoding="utf-8")
        Proc.wait()
        Output=None
        ReturnCode=Proc.returncode
        Status=True
    except KeyboardInterrupt:
      Output="Command execution interrupted by user"
      ReturnCode=None
      Status=False
    except Exception as Ex:
      Output=f"Command execution exception: {Ex}"
      ReturnCode=None
      Status=False
    debug.Get().Send(f"Execute process result: Status={Status} ReturnCode={ReturnCode} Output='{Output.replace("\n","\\n") if Output!=None else Output}'")
    return Status,ReturnCode,Output

  # -------------------------------------------------------------------------------------------------------------------
  # Executes a command
  # Args:
  # - Command (string): Command to execute
  # - GetOutput (boolean, default False): Get command output (True) or not (False)
  # Returns:
  # - DispatcherResult: Result of command execution
  # -------------------------------------------------------------------------------------------------------------------
  def ExecuteCommand(self,Command,GetOutput=False):

    #Debug message
    debug.Get().Send(f"Executing command: {Command} (GetOutput={GetOutput})")
    
    #Get command
    Cmd=Command.strip()
    
    #Detect command execution in background
    if Cmd.endswith(" &"):
      if GetOutput==True:
        Message=f"Cannot launch process in background and get output at the same time ({Command})"
        return DispatcherResult.DispatcherError(Message)
      Cmd=Cmd[:-2].strip()
      Background=True
    else:
      Background=False

    #Find python command and main file for background execution
    if Background==True:
      PythonProgram=shutil.which("python")
      if PythonProgram==None:
        Message=f"Python command is not found (required for launching file redirection in background)"
        return DispatcherResult.DispatcherError(Message)
      MainFile=str(Path(os.path.abspath(self.Config["main_file_path"])).parent/(const.APP_NAME.lower()+".py"))
    else:
      PythonProgram=None

    #Replace in command all environment variables like {{name}} with their value from environment
    #Vaiables not found in environment are not replaced and are left as they are in the command string
    Index=0
    while True:
      FoundPos=Cmd.find("{{",Index)
      if FoundPos==-1:
        break
      EndPos=Cmd.find("}}",FoundPos)
      if EndPos==-1:
        break
      VarName=Cmd[FoundPos+2:EndPos]
      if VarName in os.environ:
        VarValue=os.environ[VarName]
        Cmd=Cmd[:FoundPos]+VarValue+Cmd[EndPos+2:]
        Index=FoundPos+len(VarValue)
      else:
        Index=EndPos+2
    
    #Replace special placeholders {{SAFECLIPBOARD}} and {{CLIPBOARD}} with clipboard contents
    if "{{SAFECLIPBOARD}}" in Cmd or "{{CLIPBOARD}}" in Cmd:
      try:
        ClipboardContents=terminal.ClipboardGet()
        Cmd=Cmd.replace("{{CLIPBOARD}}",ClipboardContents.replace("\n","\\n").replace("\"","\\\""))
        Cmd=Cmd.replace("{{SAFECLIPBOARD}}",ClipboardContents.replace("\n","").replace("\"","").replace("'",""))
      except Exception as Ex:
        Message=f"Error getting clipboard contents: {Ex}"
        return DispatcherResult.DispatcherError(Message)
    
    #Replace home directory
    Cmd=utils.FilePathDisp2Intr(Cmd,self.Config)

    #Replace single command aliases
    Cmd=self.ReplaceAliases(Cmd,MultiCmd=False)

    #Identify tool by first token
    Tool=Cmd.strip().split(" ")[0] if len(Cmd.strip())>0 else ""

    #Exit command: Terminate shell
    if Tool=="exit" and len(Cmd.strip().split(" "))==1:
      return DispatcherResult.Terminate()
    
    #Restart command: Terminate shell and request restart
    if Tool=="init" and len(Cmd.strip().split(" "))==1:
      return DispatcherResult.Restart()
    
    #Pass-through command execution to system shell when it starts by $
    if Cmd.strip().startswith("$"):
      if Cmd.strip().startswith("$"):
        Cmd=Cmd[1:].strip()
      if Background==False:
        Status,RetCode,Output=self.ExecProcess(Cmd,Capture="all" if GetOutput==True else None)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        elif RetCode==0:
          return DispatcherResult.Ok(Output)
        else:
          return DispatcherResult.ExternalError(RetCode,Output)
      else:
        Status,RetCode,Output=self.ExecProcess(Cmd,Capture=None,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        terminal.Write(f"Process launched in background (pid={Output})")
        return DispatcherResult.Ok()
    
    #Find most inner built-in function calls and execute
    while True:
      Status,Message,CallStart,CallEnd=self.Parser.FindMostInnerCall(Cmd)
      if Status!=parser.PARSER_OK:
        Message=f"Command parse error: {Message}"
        return DispatcherResult.DispatcherError(Message)
      if CallStart!=None and CallEnd!=None:
        InnerCall=Cmd[CallStart:CallEnd+1]
        if InnerCall.startswith("exec"):
          InnerCmd=InnerCall[5:-1]
          Result=self.ExecuteCommand(InnerCmd,GetOutput=True)
          if Result.Event!=DispatcherResult.OK:
            Message=f"Error executing inner command '{InnerCmd}': {Result.Output}"
            return DispatcherResult.DispatcherError(Message)
          Output=Result.Output.replace("\n","\\n").replace("\"","\\\"") if Result.Output!=None else ""
          Cmd=Cmd[:CallStart]+"\""+Output+"\""+Cmd[CallEnd+1:]
        elif InnerCall.startswith("eval"):
          InnerExpr=InnerCall[5:-1]
          Status,Message,EvalResult=self.Evaluator.Evaluate(InnerExpr)
          if Status==False:
            return DispatcherResult.DispatcherError(Message)
          EvalResult=str(EvalResult).replace("\n","\\n").replace("\"","\\\"") if EvalResult!=None else ""
          Cmd=Cmd[:CallStart]+"\""+str(EvalResult)+"\""+Cmd[CallEnd+1:]
        else:
          break
      else:
        break
    
    #Parse command
    Status,Message,Tokens=self.Parser.Parse(Cmd)
    if Status!=parser.PARSER_OK:
      Message=f"Command parse error: {Message}"
      return DispatcherResult.DispatcherError(Message)
    if len(Tokens)==0:
      return DispatcherResult.Ok()
    
    #Help command: Print help for specified command or general help if no command specified
    if Tool=="help" and len(Tokens)==1:
      Output=self.PrintCommandList()
      if GetOutput==True:
        return DispatcherResult.Ok(Output)
      else:
        print(Output)
        return DispatcherResult.Ok()
    elif (Tool=="help" and len(Tokens)==2 and Tokens[1]["type"]=="string") \
     or (len(Tokens)==2 and Tokens[1]["type"]=="string" and Tokens[1]["value"]=="--help" and (Tool in self.CommandDir or Tool in ["exit","init"])):
      if Tool=="help":
        HelpCommand=Tokens[1]["value"]
      else:
        HelpCommand=Tool
      Status,Output=self.PrintHelp(HelpCommand)
      if Status==True:
        if GetOutput==True:
          return DispatcherResult.Ok(Output)
        else:
          print(Output)
          return DispatcherResult.Ok()
      else:
        return DispatcherResult.DispatcherError(Output)
    elif Tool=="help" and len(Tokens)>2:
      Message=f"Help command syntax error"
      return DispatcherResult.DispatcherError(Message)
    
    #Detect redirection operators
    if any(Token["type"]=="symbol" and Token["name"].startswith("redirect_") for Token in Tokens):
      if len([Token for Token in Tokens if Token["type"]=="symbol" and Token["name"].startswith("redirect_")])>1:
        Message=f"Multiple redirection operators are not supported"
        return DispatcherResult.DispatcherError(Message)
      if len(Tokens)<3 \
      or Tokens[-2]["type"]!="symbol" or not Tokens[-2]["name"].startswith("redirect_") \
      or Tokens[-1]["type"]!="string":
        Message=f"Redirection syntax is: <command> <redirection_operator> <file>"
        return DispatcherResult.DispatcherError(Message)
      if GetOutput==True:
        Message=f"Cannot get output of command if file redirection is enabled"
        return DispatcherResult.DispatcherError(Message)
      RedirectionOperator=Tokens[-2]["value"]
      RedirectionPipeMode={"out":"1","err":"2","all":"all"}.get(Tokens[-2]["name"].split("_")[1])
      RedirectionFileMode=Tokens[-2]["name"].split("_")[2]
      RedirectionFilePath=Tokens[-1]["value"]
      Cmd=Cmd[:Tokens[-2]["start"]].strip()
      Tokens=Tokens[:-2]
      debug.Get().Send(f"Redirection detected: PipeMode={RedirectionPipeMode} FileMode={RedirectionFileMode} FilePath={RedirectionFilePath}")
    else:
      RedirectionOperator=None
      RedirectionPipeMode=None
      RedirectionFileMode=None
      RedirectionFilePath=None
    
    #External program execution
    if Tool not in self.CommandDir:

      #Compose program path and arguments
      Program=shutil.which(Tool)
      if Program==None:
        Message=f"External command '{Tool}' is not found or not implemented"
        return DispatcherResult.DispatcherError(Message)
      Args=[Program]+[Token["value"] for Token in Tokens[1:]]
      
      #Launch external program in background without file redirection
      if Background==True and RedirectionOperator==None:
        Status,RetCode,Output=self.ExecProcess(Args,Shell=False,Capture=None,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        terminal.Write(f"Process launched in background (pid={Output})")
        return DispatcherResult.Ok()

      #Launch external program in background with file redirection
      elif Background==True and RedirectionOperator!=None:
        BackgroundCmd=f"{Cmd} {RedirectionOperator} \"{RedirectionFilePath}\""
        BackgroundArgs=[PythonProgram,MainFile,"--config",self.Config["config_file_path"],"--skip-init","--command",BackgroundCmd]
        Status,RetCode,Output=self.ExecProcess(BackgroundArgs,Shell=False,Capture=None,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        terminal.Write(f"Process launched in background (pid={Output})")
        return DispatcherResult.Ok()

      #Launch external program in foreground with file redirection
      elif RedirectionOperator!=None:
        Status,RetCode,Output=self.ExecProcess(Args,Shell=False,Capture=RedirectionPipeMode)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        elif RetCode!=0:
          return DispatcherResult.ExternalError(RetCode)
        try:
          OpenMode={"new":"w","apd":"a"}.get(RedirectionFileMode)
          File=open(RedirectionFilePath,OpenMode,encoding="utf-8")
          File.write(Output)
          File.close()
        except Exception as Ex:
          Message=f"Error writing to file '{RedirectionFilePath}': {Ex}"
          return DispatcherResult.DispatcherError(Message)
        return DispatcherResult.Ok()

      #Launch external program in foreground without file redirection
      else:
        Status,RetCode,Output=self.ExecProcess(Args,Shell=False,Capture="all" if GetOutput==True else None)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        elif RetCode!=0:
          return DispatcherResult.ExternalError(RetCode)
        return DispatcherResult.Ok(Output)
    
    #Check if command module has Get and Execute functions
    if self.CommandDir[Tool]["get"]==None or self.CommandDir[Tool]["execute"]==None:
      Message=f"Command '{Tool}' is missing Get() or Execute() function on module {Tool}.py"
      return DispatcherResult.DispatcherError(Message)
    
    #Parse command options
    CommandMetaData=self.CommandDir[Tool]["get"]()
    Status,Message,CmdOptions=self.ParseOptions(CommandMetaData["options"],Tokens)
    if Status==False:
      Message=f"Command options parse error: {Message}\nExecute '{Tool} --help' for more information on command usage"
      return DispatcherResult.DispatcherError(Message)
    
    #Execute command
    try:
      
      #Execution in output get mode
      if GetOutput==True:
        Buffer=io.StringIO()
        with redirect_stdout(Buffer), redirect_stderr(Buffer):
          Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
          Output=Buffer.getvalue()
        if Status==False:
          return DispatcherResult.CommandError(Output)
        return DispatcherResult.Ok(Output)
      
      #Execute in background without file redirection
      elif Background==True and RedirectionOperator==None:
        BackgroundArgs=[PythonProgram,MainFile,"--config",self.Config["config_file_path"],"--skip-init","--command",Cmd]
        Status,RetCode,Output=self.ExecProcess(BackgroundArgs,Shell=False,Capture=None,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        terminal.Write(f"Process launched in background (pid={Output})")
        return DispatcherResult.Ok()

      #Execute in background with file redirection
      elif Background==True and RedirectionOperator!=None:
        BackgroundCmd=f"{Cmd} {RedirectionOperator} \"{RedirectionFilePath}\""
        BackgroundArgs=[PythonProgram,MainFile,"--config",self.Config["config_file_path"],"--skip-init","--command",BackgroundCmd]
        Status,RetCode,Output=self.ExecProcess(BackgroundArgs,Shell=False,Capture=None,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        terminal.Write(f"Process launched in background (pid={Output})")
        return DispatcherResult.Ok()
      
      #Normal execution with file redirection
      elif RedirectionOperator!=None:
        Buffer=io.StringIO()
        if RedirectionPipeMode=="1":
          with redirect_stdout(Buffer):
            Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
        elif RedirectionPipeMode=="2":
          with redirect_stderr(Buffer):
            Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
        elif RedirectionPipeMode=="all":
          with redirect_stdout(Buffer), redirect_stderr(Buffer):
            Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
        Output=Buffer.getvalue()
        if Status==False:
          return DispatcherResult.CommandError()
        try:
          OpenMode={"new":"w","apd":"a"}.get(RedirectionFileMode)
          File=open(RedirectionFilePath,OpenMode,encoding="utf-8")
          File.write(Output)
          File.close()
        except Exception as Ex:
          Message=f"Error writing to file '{RedirectionFilePath}': {Ex}"
          return DispatcherResult.DispatcherError(Message)
        return DispatcherResult.Ok()
    
      #Normal execution without file redirection
      else:
        Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
        if Status==False:
          return DispatcherResult.CommandError()
        return DispatcherResult.Ok()
    
    #Command execution exception handler
    except Exception as Ex:
      Message=f"Exception executing command: {Ex}"
      return DispatcherResult.DispatcherError(Message)

    #Return error in any other case (should not reach here)
    Message=f"Unknown error executing command '{Tool}'"
    return DispatcherResult.DispatcherError(Message)

  # -------------------------------------------------------------------------------------------------------------------
  # Executes command line, splits command line into commands as previous step
  # Args:
  # - CommandLine (string): Full command line
  # Returns:
  # - DispatcherResult: Result of the last command executed in the sequence, or the first error encountered
  # -------------------------------------------------------------------------------------------------------------------
  def ExecuteCommandLine(self,CommandLine):

    #Replace multi command aliases
    CmdLine=self.ReplaceAliases(CommandLine,MultiCmd=True)

    #Split command line into commands by semicolons, ignoring semicolons inside quotes and parentheses
    Status,Message,Commands=self.Parser.Split(CmdLine)
    if Status==False:
      Message=f"Command line parse error ({Message.lower()})"
      return DispatcherResult.DispatcherError(Message)
    
    #Check command line is empty
    if len(Commands)==0:
      return DispatcherResult.Ok()
    
    #Execute commands
    for Cmd in Commands:
      Result=self.ExecuteCommand(Cmd)
      if Result.Event!=DispatcherResult.OK:
        break
    
    #Return result
    return Result
    
  # -------------------------------------------------------------------------------------------------------------------
  # Executes a sequence of commands on a list of command strings
  # Args:
  # - Commands (list of string): Commands to execute
  # Returns:
  # - DispatcherResult: Result of the last command executed in the sequence, or the first error encountered
  # -------------------------------------------------------------------------------------------------------------------
  def ExecuteScript(self,Script):
    
    #Read command lines
    if isinstance(Script,list):
      Commands=Script
    elif isinstance(Script,str):
      try:
        Commands=open(Script,"r").read().splitlines()
      except Exception as Ex:
        Message=f"Unable to open file {Script}: {str(Ex)}"
        return DispatcherResult.DispatcherError(Message)
    else:
      Message=f"Passed script is not list or string (but {type(Script)})"
      return DispatcherResult.DispatcherError(Message)
    
    #Execute commands
    for Cmd in Commands:
      if Cmd.strip()=="" or Cmd.strip().startswith("#"):
        continue
      Result=self.ExecuteCommandLine(Cmd)
      if Result.Event!=DispatcherResult.OK:
        break
    
    #Return result
    return Result
