# ---------------------------------------------------------------------------------------------------------------------
# parser.py: Command parser
# ---------------------------------------------------------------------------------------------------------------------

# class CommandParser
# - Parse(command): Parses a command string and returns a list of tokens.

# ---------------------------------------------------------------------------------------------------------------------
# Import libraries
# ---------------------------------------------------------------------------------------------------------------------
import debug

# ---------------------------------------------------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------------------------------------------------

#Built in functions
BUILTIN_FUNCTIONS=["eval","exec"]

#Parser errors
PARSER_OK=0
PARSER_ERROR_UNMATCHED_PARENTHESIS=1
PARSER_ERROR_OPEN_QUOTED_STRING=2

# ---------------------------------------------------------------------------------------------------------------------
# Command parser class
# ---------------------------------------------------------------------------------------------------------------------
class CommandParser:
  
  # -------------------------------------------------------------------------------------------------------------------
  # Constructor
  # Args: 
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------------------------------------------------
  def __init__(self,Config):
    self.Config=Config
  
  # -------------------------------------------------------------------------------------------------------------------
  # Find the matching closing parenthesis in a command string, handling nested parentheses and quoted strings
  # Args:
  # - Command (string): Full command string to search
  # - AbsStartPos (int): Position of the opening parenthesis to match
  # Returns:
  # - int: Index of the matching closing parenthesis, or -1 if not found, or -2 if there is an open quoted string
  # -------------------------------------------------------------------------------------------------------------------
  def _FindEndingParenthesis(self,Command,AbsStartPos):
    Index=AbsStartPos
    ParenthesisLevel=0
    QuotedStringMode=False
    ProcessedChars=0
    while Index<len(Command):
      Char=Command[Index]
      if Char=="\"":
        if QuotedStringMode==False:
          QuotedStringMode=True
          ProcessedChars=1
        else:
          if Index+1<len(Command)-1 and Command[Index+1]=="\"":
            ProcessedChars=2
          else:
            QuotedStringMode=False
            ProcessedChars=1
      elif Char=="(" and QuotedStringMode==False:
        ParenthesisLevel+=1
        ProcessedChars=1
      elif Char==")" and QuotedStringMode==False:
        ParenthesisLevel-=1
        if ParenthesisLevel==0:
          return Index
      else:
        ProcessedChars=1
      Index+=ProcessedChars
    return -2 if QuotedStringMode==True else -1

  # -------------------------------------------------------------------------------------------------------------------
  # Parse a command string into a list of tokens
  # Args:
  # - Command (string): Command string to parse
  # - Start (int): Absolute position in the original command string where this substring starts (used for calculating token positions)
  # Returns:
  # - int: 0 on success, or error code on failure
  # - string: Error message if parsing failed, empty string on success
  # - list: List of token dicts (each with 'type' and 'value' or 'name'/'args' keys), or None on error
  # -------------------------------------------------------------------------------------------------------------------
  def Parse(self,Command,Start=0):
    
    #Init loop
    Tokens=[]
    Index=0
    Token=""
    QuotedStringMode=False
    QuotedToken=False
    AbsStartPos=Start
    ProcessedChars=0
    
    #Loop over chars
    while Index<len(Command):
      
      #Get current char
      Char=Command[Index]
      
      #Double quotes
      if Char=="\"":
        if QuotedStringMode==False:
          QuotedStringMode=True
          QuotedToken=True
          ProcessedChars=1
        else:
          if Index+1<len(Command)-1 and Command[Index+1]=="\"":
            Token+="\""
            ProcessedChars=2
          else:
            QuotedStringMode=False
            ProcessedChars=1
      
      #If current position starts with built-in function, find matching ending parenthesis and make recursive call to parse inner command
      elif any([Command[Index:].startswith(func+"(")==True for func in BUILTIN_FUNCTIONS]):
        FunctionName=Command[Index:Command.find("(",Index)]
        EndIndex=self._FindEndingParenthesis(Command,Index)
        if EndIndex==-1:
          Message=f"Unmatched parenthesis in command at position {Start+Index}"
          return PARSER_ERROR_UNMATCHED_PARENTHESIS,Message,None
        elif EndIndex==-2:
          Message=f"Open quoted string in command at position {Start+Command.rfind('\"')}"
          return PARSER_ERROR_OPEN_QUOTED_STRING,Message,None
        CommandIndex=Index+len(FunctionName)+1
        InnerCommand=Command[CommandIndex:EndIndex]
        RetCode,Message,InnerTokens=self.Parse(InnerCommand,CommandIndex)
        if RetCode!=PARSER_OK:
          return RetCode,Message,None
        AbsEndPos=Start+EndIndex
        Tokens.append({"type":"function","start":AbsStartPos,"end":AbsEndPos,"name":FunctionName,"args":InnerTokens})
        ProcessedChars=EndIndex-Index+1
        AbsStartPos=Start+Index+ProcessedChars+1
      
      #Detect token boundary
      elif Char==" ":
        if QuotedStringMode==True:
          Token+=Char
        else:
          if len(Token)!=0:
            AbsEndPos=Start+Index-1
            RawValue=("\""+Token+"\"" if QuotedToken==True else Token)
            Tokens.append({"type":"string","start":AbsStartPos,"end":AbsEndPos,"value":Token,"raw":RawValue})
            Token=""
            QuotedToken=False
            AbsStartPos=Start+Index+1
        ProcessedChars=1
      
      #Anything else is part of the current token
      else:
        Token+=Char
        ProcessedChars=1
      
      #Increment index and update previous char
      Index+=ProcessedChars
    
    #Append last token if any ate end of the loop
    if len(Token)!=0:
      AbsEndPos=Start+Index-1
      RawValue=("\""+Token+"\"" if QuotedToken==True else Token)
      Tokens.append({"type":"string","start":AbsStartPos,"end":AbsEndPos,"value":Token,"raw":RawValue})
    
    #Error if we ended in quoted string mode
    if QuotedStringMode==True:
      Message="Open quoted string in command"
      return PARSER_ERROR_OPEN_QUOTED_STRING,Message,None
    
    #Return tokenized command
    debug.Get().Send(f"Parser: Command={Command!r} Tokens={Tokens!r}")
    return PARSER_OK,"",Tokens

  # -------------------------------------------------------------------------------------------------------------------
  # Finds most inner built-in function call
  # Args:
  # - Command (string): Command string to parse
  # - Start (int): Absolute position in the original command string where this substring starts (used for calculating token positions)
  # Returns:
  # - int: 0 on success, or error code on failure
  # - string: Error message if parsing failed, empty string on success
  # - int: Starting position of the most inner built-in function call, or None if not found
  # - int: Ending position of the most inner built-in function call, or None if not found
  # -------------------------------------------------------------------------------------------------------------------
  def FindMostInnerCall(self,Command,Start=0):

    #Find built-in function call
    CallStart=-1
    CallEnd=-1
    for FuncName in BUILTIN_FUNCTIONS:
      CallStart=Command.find(FuncName+"(",CallStart+1)
      if CallStart!=-1:
        CallEnd=self._FindEndingParenthesis(Command,CallStart)
        if CallEnd==-1:
          Message=f"Unmatched parenthesis in command at position {Start+CallStart}"
          return PARSER_ERROR_UNMATCHED_PARENTHESIS,Message,None
        elif CallEnd==-2:
          Message=f"Open quoted string in command at position {Start+Command.rfind('\"')}"
          return PARSER_ERROR_OPEN_QUOTED_STRING,Message,None
        else:
          break
    
    #If we have a call, return first the inner one, if not then return current one
    if CallStart>0 and CallEnd>0:
      InnerCommand=Command[CallStart+len(FuncName):CallEnd]
      InnerPos=Start+CallStart+len(FuncName)
      RetCode,Message,InnerCallStart,InnerCallEnd=self.FindMostInnerCall(InnerCommand,InnerPos)
      if RetCode!=PARSER_OK:
        return RetCode,Message,None,None
      if InnerCallStart!=None and InnerCallEnd!=None:
        return PARSER_OK,"",InnerPos+InnerCallStart,InnerPos+InnerCallEnd
      else:
        return PARSER_OK,"",CallStart,CallEnd
    
    #Return no inner call
    return PARSER_OK,"",None,None
