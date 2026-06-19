  # ---------------------------------------------------------------------------------------------------------------------
# dispatcher.py: Command dispatcher
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import os
import re
import io
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
  DISPATCHER_ERROR = 2
  COMMAND_ERROR    = 3
  EXTERNAL_ERROR   = 4
  
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
  def DispatcherError(Output):
    return DispatcherResult(Event=DispatcherResult.DISPATCHER_ERROR,Output=Output.strip("\n"))
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
  # Execute a command and return its output and return code
  # Args:
  # - Command (string or list): Command to execute as a string in shell mode or list or string in program mode
  # - Shell (bool, default True): Execute comand in shell mode (True) or program mode (False)
  # - Redirect (bool, default False): Whether to capture and return command output (stdout and stderr combined)
  # - Detached (bool, default False): Whether to launch process as detached
  # Returns:
  # - boolean: True=Process executed, False=Exception
  # - int: Command return code
  # - string: Command output when Redirect is True, Process Pid when Detached is True, else None
  # ---------------------------------------------------------------------------
  def ExecProcess(self,Command,Shell=True,Redirect=True,Detached=False):
    debug.Get().Send(f"Execute process input: {Command} Shell={Shell} Redirect={Redirect} Detached={Detached}")
    try:
      if Redirect==True:
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
      Output=("Command execution interrupted by user" if Redirect else None)
      ReturnCode=None
      Status=False
    except Exception as Ex:
      Output=f"Command execution exception: {Ex}"
      ReturnCode=None
      Status=False
    debug.Get().Send(f"Execute process output: Status={Status} ReturnCode={ReturnCode} Output='{Output.replace("\n","\\n") if Output!=None else Output}'")
    return Status,ReturnCode,Output

  # -------------------------------------------------------------------------------------------------------------------
  # Executes a command
  # Args:
  # - Command (string): Command to execute
  # - Redirect (bool): Whether to redirect command output to terminal (True) or return it in the DispatcherResult.Output field (False)
  # Returns:
  # - DispatcherResult: Result of command execution
  # -------------------------------------------------------------------------------------------------------------------
  def ExecuteCommand(self,Command,Redirect=False):

    #Debug message
    debug.Get().Send(f"Executing command: {Command} (Redirect={Redirect})")
    
    #Get command
    Cmd=Command.strip()
    
    #Detect command execution in background
    if Cmd.endswith(" &"):
      if Redirect==True:
        Message=f"Cannot launch process in background and redirected at the same time ({Command})"
        return DispatcherResult.DispatcherError(Message)
      Cmd=Cmd[:-2].strip()
      Background=True
    else:
      Background=False

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
    
    #Replace home directory
    Cmd=Cmd.replace("~",self.Config["kelwyn_home"])

    #Identify tool by first token
    Tool=Cmd.strip().split(" ")[0] if len(Cmd.strip())>0 else ""

    #Exit command: Terminate shell
    if Tool=="exit":
      return DispatcherResult.Terminate()
    
    #Pass-through command execution to system when it starts by $ or it is pass through list
    if Cmd.strip().startswith("$") or Tool in self.Config["pass_through_commands"]:
      if Cmd.strip().startswith("$"):
        Cmd=Cmd[1:].strip()
      if Background==False:
        Status,RetCode,Output=self.ExecProcess(Cmd,Redirect=Redirect)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        elif RetCode==0:
          return DispatcherResult.Ok(Output)
        else:
          return DispatcherResult.ExternalError(RetCode,Output)
      else:
        Status,RetCode,Pid=self.ExecProcess(Cmd,Redirect=False,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        else:
          terminal.Write(f"Process launched in backgrpund (pid={Pid})")
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
          Result=self.ExecuteCommand(InnerCmd,Redirect=True)
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
      if Redirect==True:
        return DispatcherResult.Ok(Output)
      else:
        print(Output)
        return DispatcherResult.Ok()
    elif (Tool=="help" and len(Tokens)==2 and Tokens[1]["type"]=="string") \
     or (len(Tokens)==2 and Tokens[1]["type"]=="string" and Tokens[1]["value"]=="--help" and Tool in self.CommandDir):
      if Tool=="help":
        HelpCommand=Tokens[1]["value"]
      else:
        HelpCommand=Tool
      Status,Output=self.PrintHelp(HelpCommand)
      if Status==True:
        if Redirect==True:
          return DispatcherResult.Ok(Output)
        else:
          print(Output)
          return DispatcherResult.Ok()
      else:
        return DispatcherResult.DispatcherError(Output)
    elif Tool=="help" and len(Tokens)>2:
      Message=f"Help command syntax error"
      return DispatcherResult.DispatcherError(Message)
    
    #External program execution
    if Tool not in self.CommandDir:
      Program=shutil.which(Tool)
      if Program==None:
        Message=f"External command '{Tool}' is not found or not implemented"
        return DispatcherResult.DispatcherError(Message)
      Args=[Program]+[Token["value"] for Token in Tokens[1:]]
      if Background==False:
        Status,RetCode,Output=self.ExecProcess(Args,Shell=False,Redirect=Redirect)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        elif RetCode==0:
          return DispatcherResult.Ok(Output)
        else:
          return DispatcherResult.ExternalError(RetCode,Output)
      else:
        Status,RetCode,Pid=self.ExecProcess(Args,Shell=False,Redirect=False,Detached=True)
        if Status==False:
          return DispatcherResult.DispatcherError(Output)
        else:
          terminal.Write(f"Process launched in backgrpund (pid={Pid})")
          return DispatcherResult.Ok()
    
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
      
      #Execution in output redirection mode
      if Redirect==True:
        Buffer=io.StringIO()
        with redirect_stdout(Buffer), redirect_stderr(Buffer):
          Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
          Output=Buffer.getvalue()
        if Status==False:
          return DispatcherResult.CommandError(Output)
        else:
          return DispatcherResult.Ok(Output)
      
      #Execute in background
      elif Background==True:
        BackgroundCmd=f"python {__file__} --config {self.Config["config_file_path"]} --skip-init --command \"{Cmd}\""
        RetCode,Pid=self.ExecProcess(BackgroundCmd,Redirect=False,Detached=True)
        if RetCode==0:
          terminal.Write(f"Process launched in backgrpund (pid={Pid})")
          return DispatcherResult.Ok()
        else:
          return DispatcherResult.DispatcherError(RetCode,Output)
      
      #Normal execution
      else:
        Status=self.CommandDir[Tool]["execute"](CmdOptions,self.Config)
        if Status==False:
          return DispatcherResult.CommandError()
        else:
          return DispatcherResult.Ok()
    
    #Command execution exception handler
    except Exception as Ex:
      Message=f"Exception executing command: {Ex}"
      return DispatcherResult.DispatcherError(Message)

    #Return error in any other case (should not reach here)
    Message=f"Unknown error executing command '{Tool}'"
    return DispatcherResult.DispatcherError(Message)

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
      Result=self.ExecuteCommand(Cmd)
      if Result.Event!=DispatcherResult.OK:
        break
    
    #Return result
    return Result
