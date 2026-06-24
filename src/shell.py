#Import libraries
import sys
import ansi
import const
import terminal
import prompt
import history
import utils
import completer
import dispatcher
import debug

# ---------------------------------------------------------------------------
# Shell class
# ---------------------------------------------------------------------------
class Shell:

  # -------------------------------------------------------------------------
  # Constructor
  # Args:
  # - SkipInit (bool): If True, skip loading the init script
  # - InitCommand (string): Command to execute at startup before showing prompt
  # - InitScript (string): Path to init script to execute at startup (not implemented yet)
  # - CommandsFolder (string): Path to folder containing command modules
  # - CompletersFolder (string): Path to folder containing completer modules
  # - WhippetsFolder (string): Path to the folder containing whippet modules
  # - HistoryFile (string): Path to command history file
  # - MaxHistoryCommands (int): Maximum number of history entries to keep
  # - NoTruncate (bool): No truncation of history file
  # - Config (dict): JSON Configuration file
  # Returns: None
  # -------------------------------------------------------------------------
  def __init__(self,Command,SkipInit,InitCommand,InitScript,CommandsFolder,CompletersFolder,WhippetsFolder,HistoryFile,MaxHistoryCommands,NoTruncate,Config):
    self.Config=Config
    self.Command=Command
    self.SkipInit=SkipInit
    self.InitCommand=InitCommand
    self.InitScript=InitScript
    self.Prompt=prompt.PromptBuilder(WhippetsFolder,Config)
    self.History=history.ShellHistory(HistoryFile,MaxHistoryCommands,NoTruncate,Config)
    self.Dispatcher=dispatcher.CommandDispatcher(CommandsFolder,Config)
    self.Completer=completer.TabCompleter(CompletersFolder,Config)

  # -------------------------------------------------------------------------
  # Move by word to the left (Ctrl+Left) or right (Ctrl+Right)
  # Args:
  # - Direction (string): "LEFT" or "RIGHT"
  # - CommandBuffer (string): Current command buffer
  # - CursorOffset (int): Current cursor offset
  # Returns:
  # - int: New cursor offset after moving by word
  # -------------------------------------------------------------------------
  def MoveCursorByWord(self,Direction,CommandBuffer,CursorOffset):
    NewOffset=CursorOffset
    if Direction=="RIGHT":
      while NewOffset<len(CommandBuffer) and CommandBuffer[NewOffset]==" ":
        NewOffset+=1
      if NewOffset<len(CommandBuffer) and (CommandBuffer[NewOffset].isalnum() or CommandBuffer[NewOffset] in "_-"):
        while NewOffset<len(CommandBuffer) and (CommandBuffer[NewOffset].isalnum() or CommandBuffer[NewOffset] in "_-"):
          NewOffset+=1
      elif NewOffset<len(CommandBuffer) and not (CommandBuffer[NewOffset].isalnum() or CommandBuffer[NewOffset] in "_-"):
        while NewOffset<len(CommandBuffer) and not (CommandBuffer[NewOffset].isalnum() or CommandBuffer[NewOffset] in "_-"):
          NewOffset+=1
    elif Direction=="LEFT":
      while NewOffset>0 and CommandBuffer[NewOffset-1]==" ":
        NewOffset-=1
      if NewOffset>0 and (CommandBuffer[NewOffset-1].isalnum() or CommandBuffer[NewOffset-1] in "_-"):
        while NewOffset>0 and (CommandBuffer[NewOffset-1].isalnum() or CommandBuffer[NewOffset-1] in "_-"):
          NewOffset-=1
      elif NewOffset>0 and not (CommandBuffer[NewOffset-1].isalnum() or CommandBuffer[NewOffset-1] in "_-"):
        while NewOffset>0 and not (CommandBuffer[NewOffset-1].isalnum() or CommandBuffer[NewOffset-1] in "_-"):
          NewOffset-=1
    return NewOffset

  # -------------------------------------------------------------------------
  # Run the interactive shell main loop until the user exits
  # Args: None
  # Returns: None
  # -------------------------------------------------------------------------
  def Run(self):

    #Initialization
    CommandBuffer=""
    PrevCommandBuffer=""
    CursorOffset=0
    PrevCursorOffset=0
    HistoryIndex=-1
    GhostSuggestion=""
    GhostIndex=0
    PrevGhostIndex=0
    SelectionBegin=None
    SelectionEnd=None
    InputChars=""
    NextKey=None

    #Get options from configuration
    CommandBoxMaximunHeightPercent=self.Config.get("command_box_maximun_height_percent",const.DEFAULT_BOX_MAX_HEIGHT_PERCENT)
    CommandBoxItemForegroundColor=self.Config.get("command_box_item_foreground_color",const.DEFAULT_FOREGROUND_COLOR)
    CommandBoxItemHighlightColor=self.Config.get("command_box_item_highlight_color",const.DEFAULT_FOREGROUND_COLOR)
    CommandBoxItemBackgroundColor=self.Config.get("command_box_item_background_color",const.DEFAULT_BACKGROUND_COLOR)
    CommandBoxStatusForegroundColor=self.Config.get("command_box_status_foreground_color",const.DEFAULT_FOREGROUND_COLOR)
    CommandBoxStatusBackgroundColor=self.Config.get("command_box_status_background_color",const.DEFAULT_BACKGROUND_COLOR)
    ErrorMessageColor=self.Config.get("error_message_color",const.DEFAULT_BOX_MAX_HEIGHT_PERCENT)
    GhostSuggestionColor=self.Config.get("ghost_suggestion_color",const.DEFAULT_BOX_MAX_HEIGHT_PERCENT)
    SelectionForegroundColor=self.Config.get("selection_foreground_color",const.DEFAULT_BACKGROUND_COLOR)
    SelectionBackgroundColor=self.Config.get("selection_background_color",const.DEFAULT_FOREGROUND_COLOR)
    SelectionColorSequence=ansi.SetFgColor(SelectionForegroundColor)+ansi.SetBkColor(SelectionBackgroundColor)

    #Calculate maximun command box height
    CommandBoxHeight=int(CommandBoxMaximunHeightPercent*terminal.GetTerminalSize()[0]/100)
    CommandBoxHeight=(terminal.GetTerminalSize()[0]-2 if CommandBoxHeight>terminal.GetTerminalSize()[0]-2 else CommandBoxHeight)

    #Init command execution
    if self.InitCommand!=None:
      Result=self.Dispatcher.ExecuteCommand(self.InitCommand)
      if Result.Event==dispatcher.DispatcherResult.TERMINATE:
        return
    
    #Initial script execution
    if self.InitScript!=None:
      InitFile=self.InitScript
    elif self.SkipInit==False:
      InitFile=["clear","banner","wellcome"]
    else:
      InitFile=None
    if InitFile!=None:
      Result=self.Dispatcher.ExecuteScript(InitFile)
      if Result.Event!=dispatcher.DispatcherResult.OK:
        terminal.Write(ansi.SetFgColor(ErrorMessageColor)+f"Init error: {Result.Output}"+ansi.ResetColor()+"\n")
    
    #Execution for single command
    if self.Command!=None:
      Result=self.Dispatcher.ExecuteCommand(self.Command)
      return

    #Write initial prompt
    terminal.Write(self.Prompt.Get())

    #Main shell loop
    while True:

      #Read key (loops until a non-printable key is encountered, storing printable characters in InputChars)
      if NextKey!=None:
        Key=NextKey
        NextKey=None
      else:
        Key=terminal.ReadKey()
        if Key.IsPrintable():
          InputChars=Key.Char
        while terminal.IsKeyboardHit():
          Key=terminal.ReadKey()
          if Key.IsPrintable():
            InputChars+=Key.Char
          else:
            NextKey=Key
            Key=terminal.KeyEvent()
            break

      #Debug log
      debug.Get().Send("·"*120, Raw=True)
      debug.Get().Send(f"Key event: Code={Key.Code()} Char={Key.Char!r} InputChars={InputChars!r}")

      #Clear selection and rewrite command line if key is not a selection relevant key
      if Key.Code() not in ["SHIFT+LEFT","SHIFT+RIGHT","CTRL+SHIFT+LEFT","CTRL+SHIFT+RIGHT","SHIFT+HOME","SHIFT+END","CTRL+C","DELETE","BACKSPACE"] \
      and len(InputChars)==0 and SelectionBegin!=None:
        debug.Get().Send("Clearing selection")
        terminal.MoveCursorLinear(-CursorOffset)
        terminal.Write(CommandBuffer+" "*(len(GhostSuggestion)), Restore=True)
        terminal.MoveCursorLinear(+CursorOffset)
        SelectionBegin=None
        SelectionEnd=None
      
      #Up arrow: Previous command in history
      if Key.Code()=="UP":
        if HistoryIndex==-1:
          HistoryIndex=len(self.History.GetCommands())-1
        elif HistoryIndex>0:
          HistoryIndex-=1
        if HistoryIndex>=0 and HistoryIndex<len(self.History.GetCommands()):
          PrevCommandBuffer=CommandBuffer
          terminal.MoveCursorLinear(-CursorOffset)
          terminal.Write(" "*(len(PrevCommandBuffer)+len(GhostSuggestion)), Restore=True)
          CommandBuffer=self.History.GetCommands()[HistoryIndex]
          terminal.Write(CommandBuffer)
          CursorOffset=len(CommandBuffer)
          GhostSuggestion=""
          GhostIndex=0
          PrevGhostIndex=0

      #Down arrow: Next command in history
      elif Key.Code()=="DOWN":
        if HistoryIndex>=0:
          HistoryIndex+=1
          PrevCommandBuffer=CommandBuffer
          if HistoryIndex<len(self.History.GetCommands()):
            CommandBuffer=self.History.GetCommands()[HistoryIndex]
          else:
            CommandBuffer=""
            HistoryIndex=-1
          terminal.MoveCursorLinear(-CursorOffset)
          terminal.Write(" "*(len(PrevCommandBuffer)+len(GhostSuggestion)), Restore=True)
          terminal.Write(CommandBuffer)
          CursorOffset=len(CommandBuffer)
          GhostSuggestion=""
          GhostIndex=0
          PrevGhostIndex=0

      #Left arrow
      elif Key.Code()=="LEFT":
        if CursorOffset>0:
          terminal.MoveCursorLinear(-1)
          CursorOffset-=1
      
      #Right arrow
      elif Key.Code()=="RIGHT":
        if CursorOffset==len(CommandBuffer):
          if len(GhostSuggestion)!=0:
            CommandBuffer+=GhostSuggestion
            terminal.Write(GhostSuggestion)
            CursorOffset+=len(GhostSuggestion)
            GhostSuggestion=""
        elif CursorOffset<len(CommandBuffer):
          terminal.MoveCursorLinear(+1)
          CursorOffset+=1
      
      #Alt+Right: Open suggestion selector by prefix match if cursor is at end of buffer and ghost suggestion exists
      elif Key.Code()=="ALT+RIGHT":
        if CursorOffset==len(CommandBuffer) and len(GhostSuggestion)!=0:
          Suggestions=self.History.GetAllGhostSuggestions(CommandBuffer,SearchMode="prefix")
          if Suggestions!=None:
            if len(CommandBuffer)!=0 and CursorOffset==len(CommandBuffer) and len(GhostSuggestion)!=0:
              terminal.Write(" "*(len(GhostSuggestion)), Restore=True)
            Options=[{"text":Cmd,"color":CommandBoxItemForegroundColor} for Cmd in Suggestions]
            SelectedIndex=utils.SelectOption(Options,CommandBoxHeight,CommandBoxItemHighlightColor,CommandBoxItemBackgroundColor,"auto",f"Command prefix search by: '{CommandBuffer}'",CommandBoxStatusForegroundColor,CommandBoxStatusBackgroundColor)
            if SelectedIndex!=None:
              terminal.MoveCursorLinear(-CursorOffset)
              CommandBuffer=Suggestions[SelectedIndex]
              terminal.Write(Suggestions[SelectedIndex])
              CursorOffset=len(Suggestions[SelectedIndex])
              GhostSuggestion=""
              GhostIndex=0
            else:
              terminal.Write(ansi.SetFgColor(GhostSuggestionColor)+GhostSuggestion+ansi.ResetColor(), Restore=True)
      
      #Crtl+Alt+Right: Open suggestion selector by wildcard pattern match
      elif Key.Code()=="CTRL+ALT+RIGHT":
        Suggestions=self.History.GetAllGhostSuggestions(CommandBuffer,SearchMode="pattern")
        if Suggestions!=None:
          if len(CommandBuffer)!=0 and CursorOffset==len(CommandBuffer) and len(GhostSuggestion)!=0:
            terminal.Write(" "*(len(GhostSuggestion)), Restore=True)
          Options=[{"text":Cmd,"color":CommandBoxItemForegroundColor} for Cmd in Suggestions]
          SelectedIndex=utils.SelectOption(Options,CommandBoxHeight,CommandBoxItemHighlightColor,CommandBoxItemBackgroundColor,"auto",f"Command pattern search by: '{CommandBuffer}'",CommandBoxStatusForegroundColor,CommandBoxStatusBackgroundColor)
          if SelectedIndex!=None:
            terminal.MoveCursorLinear(-CursorOffset)
            CommandBuffer=Suggestions[SelectedIndex]
            terminal.Write(Suggestions[SelectedIndex])
            CursorOffset=len(Suggestions[SelectedIndex])
            GhostSuggestion=""
            GhostIndex=0
          elif len(CommandBuffer)!=0 and CursorOffset==len(CommandBuffer) and len(GhostSuggestion)!=0:
            terminal.Write(ansi.SetFgColor(GhostSuggestionColor)+GhostSuggestion+ansi.ResetColor(), Restore=True)
      
      #Ctrl+Left arrow: Move cursor left by word
      elif Key.Code()=="CTRL+LEFT":
        if CursorOffset>0:
          NewOffset=self.MoveCursorByWord("LEFT",CommandBuffer,CursorOffset)
          terminal.MoveCursorLinear(NewOffset-CursorOffset)
          CursorOffset=NewOffset
      
      #Ctrl+Right arrow: Move cursor right by word
      elif Key.Code()=="CTRL+RIGHT":
        if CursorOffset<len(CommandBuffer):
          NewOffset=self.MoveCursorByWord("RIGHT",CommandBuffer,CursorOffset)
          terminal.MoveCursorLinear(NewOffset-CursorOffset)
          CursorOffset=NewOffset
      
      #Tab completion
      elif Key.Code()=="TAB":
        if len(CommandBuffer)!=0:
          debug.Get().Send("Triggering tab completion for buffer: "+CommandBuffer)
          Completed=self.Completer.Complete(CommandBuffer,CursorOffset)
          if Completed!=None:
            terminal.MoveCursorLinear(-CursorOffset)
            terminal.Write(" "*(len(CommandBuffer)),Restore=True)
            CommandBuffer=Completed
            terminal.Write(Completed)
            CursorOffset=len(Completed)

      #Home
      elif Key.Code()=="HOME":
        terminal.MoveCursorLinear(-CursorOffset)
        CursorOffset=0
      
      #End
      elif Key.Code()=="END":
        terminal.MoveCursorLinear(len(CommandBuffer)-CursorOffset)
        CursorOffset=len(CommandBuffer)
      
      #Shift+Left arrow: Select character backwards (is selection is active, expands or shrinks selection by moving cursor left)
      elif Key.Code()=="SHIFT+LEFT":
        if CursorOffset>0:
          if SelectionBegin==None or (SelectionBegin!=None and SelectionBegin>=SelectionEnd):
            if SelectionBegin==None:
              SelectionBegin=CursorOffset
            terminal.MoveCursorLinear(-1)
            terminal.Write(SelectionColorSequence+CommandBuffer[CursorOffset-1]+ansi.ResetColor(), Restore=True)
            CursorOffset-=1
            SelectionEnd=CursorOffset
          elif SelectionBegin!=None and SelectionBegin<SelectionEnd:
            terminal.MoveCursorLinear(-1)
            terminal.Write(CommandBuffer[CursorOffset-1], Restore=True)
            CursorOffset-=1
            SelectionEnd=CursorOffset

      #Shift+Right arrow: Select character forwards
      elif Key.Code()=="SHIFT+RIGHT":
        if CursorOffset<len(CommandBuffer):
          if SelectionBegin==None or (SelectionBegin!=None and SelectionBegin<=SelectionEnd):
            if SelectionBegin==None:
              SelectionBegin=CursorOffset
            terminal.Write(SelectionColorSequence+CommandBuffer[CursorOffset]+ansi.ResetColor(), Restore=True)
            terminal.MoveCursorLinear(+1)
            CursorOffset+=1
            SelectionEnd=CursorOffset
          elif SelectionBegin!=None and SelectionBegin>SelectionEnd:
            terminal.Write(CommandBuffer[CursorOffset], Restore=True)
            terminal.MoveCursorLinear(+1)
            CursorOffset+=1
            SelectionEnd=CursorOffset
      
      #Ctrl+Shift+Left arrow: Select word backwards
      elif Key.Code()=="CTRL+SHIFT+LEFT":
        if CursorOffset>0:
          NewOffset=self.MoveCursorByWord("LEFT",CommandBuffer,CursorOffset)
          if SelectionBegin==None or (SelectionBegin!=None and SelectionBegin>=SelectionEnd):
            if SelectionBegin==None:
              SelectionBegin=CursorOffset
            terminal.MoveCursorLinear(NewOffset-CursorOffset)
            terminal.Write(SelectionColorSequence+CommandBuffer[NewOffset:CursorOffset]+ansi.ResetColor(), Restore=True)
            CursorOffset=NewOffset
            SelectionEnd=CursorOffset
          elif SelectionBegin!=None and SelectionBegin<SelectionEnd:
            if NewOffset<SelectionBegin:
              NewOffset=SelectionBegin
            terminal.MoveCursorLinear(NewOffset-CursorOffset)
            terminal.Write(CommandBuffer[NewOffset:CursorOffset], Restore=True)
            CursorOffset=NewOffset
            SelectionEnd=CursorOffset
      
      #Ctrl+Shift+Right arrow: Select word forwards
      elif Key.Code()=="CTRL+SHIFT+RIGHT":
        if CursorOffset<len(CommandBuffer):
          NewOffset=self.MoveCursorByWord("RIGHT",CommandBuffer,CursorOffset)
          if SelectionBegin==None or (SelectionBegin!=None and SelectionBegin<=SelectionEnd):
            if SelectionBegin==None:
              SelectionBegin=CursorOffset
            terminal.Write(SelectionColorSequence+CommandBuffer[CursorOffset:NewOffset]+ansi.ResetColor(), Restore=True)
            terminal.MoveCursorLinear(NewOffset-CursorOffset)
            CursorOffset=NewOffset
            SelectionEnd=CursorOffset
          elif SelectionBegin!=None and SelectionBegin>SelectionEnd:
            if NewOffset>SelectionBegin:
              NewOffset=SelectionBegin
            terminal.Write(CommandBuffer[CursorOffset:NewOffset], Restore=True)
            terminal.MoveCursorLinear(NewOffset-CursorOffset)
            CursorOffset=NewOffset
            SelectionEnd=CursorOffset

      #Shoft+Home: Select to beginning of line
      elif Key.Code()=="SHIFT+HOME":
        if CursorOffset>0:
          if SelectionBegin==None or (SelectionBegin!=None and SelectionBegin>=SelectionEnd):
            if SelectionBegin==None:
              SelectionBegin=CursorOffset
            terminal.MoveCursorLinear(-CursorOffset)
            terminal.Write(SelectionColorSequence+CommandBuffer[:CursorOffset]+ansi.ResetColor(), Restore=True)
            CursorOffset=0
            SelectionEnd=0
          elif SelectionBegin!=None and SelectionBegin<SelectionEnd:
            terminal.MoveCursorLinear(-(SelectionEnd-SelectionBegin))
            terminal.Write(CommandBuffer[SelectionBegin:SelectionEnd],Restore=True)
            terminal.MoveCursorLinear(-SelectionBegin)
            terminal.Write(SelectionColorSequence+CommandBuffer[:SelectionBegin]+ansi.ResetColor(), Restore=True)
            CursorOffset=0
            SelectionEnd=0
      
      #Shift+End: Select to end of line
      elif Key.Code()=="SHIFT+END":
        if CursorOffset<len(CommandBuffer):
          if SelectionBegin==None or (SelectionBegin!=None and SelectionBegin<=SelectionEnd):
            if SelectionBegin==None:
              SelectionBegin=CursorOffset
            terminal.Write(SelectionColorSequence+CommandBuffer[CursorOffset:]+ansi.ResetColor(), Restore=True)
            terminal.MoveCursorLinear(len(CommandBuffer)-CursorOffset)
            CursorOffset=len(CommandBuffer)
            SelectionEnd=len(CommandBuffer)
          elif SelectionBegin!=None and SelectionBegin>SelectionEnd:
            terminal.Write(CommandBuffer[SelectionEnd:SelectionBegin])
            terminal.Write(SelectionColorSequence+CommandBuffer[SelectionBegin:]+ansi.ResetColor())
            CursorOffset=len(CommandBuffer)
            SelectionEnd=len(CommandBuffer)
      
      #Alt+Up arrow: Previous ghost suggestion
      elif Key.Code()=="ALT+UP":
        GhostIndex-=1
      
      #Alt+Down arrow: Next ghost suggestion
      elif Key.Code()=="ALT+DOWN":
        GhostIndex+=1
      
      #Backspace (deletes character before cursor position, or current selection)
      elif Key.Code()=="BACKSPACE":
        if SelectionBegin!=None:
          Start=min(SelectionBegin,SelectionEnd)
          End=max(SelectionBegin,SelectionEnd)
          CommandBuffer=CommandBuffer[:Start]+CommandBuffer[End:]
          terminal.MoveCursorLinear(-CursorOffset)
          terminal.Write(CommandBuffer+" "*len(GhostSuggestion)+" "*(End-Start), Restore=True)
          CursorOffset=Start
          terminal.MoveCursorLinear(CursorOffset)
          SelectionBegin=None
          SelectionEnd=None
        elif CursorOffset>0:
          CommandBuffer=CommandBuffer[:CursorOffset-1]+CommandBuffer[CursorOffset:]
          terminal.MoveCursorLinear(-1)
          terminal.Write(CommandBuffer[CursorOffset-1:]+" ")
          terminal.MoveCursorLinear(CursorOffset-len(CommandBuffer)-2)
          CursorOffset-=1
      
      #Delete (deletes character at cursor position, or current selection)
      elif Key.Code()=="DELETE":
        if SelectionBegin!=None:
          Start=min(SelectionBegin,SelectionEnd)
          End=max(SelectionBegin,SelectionEnd)
          CommandBuffer=CommandBuffer[:Start]+CommandBuffer[End:]
          terminal.MoveCursorLinear(-CursorOffset)
          terminal.Write(CommandBuffer+" "*len(GhostSuggestion)+" "*(End-Start), Restore=True)
          CursorOffset=Start
          terminal.MoveCursorLinear(CursorOffset)
          SelectionBegin=None
          SelectionEnd=None
        elif CursorOffset<len(CommandBuffer):
          CommandBuffer=CommandBuffer[:CursorOffset]+CommandBuffer[CursorOffset+1:]
          terminal.Write(CommandBuffer[CursorOffset:]+" ")
          terminal.MoveCursorLinear(CursorOffset-len(CommandBuffer)-1)
      
      #Escape: Clear command buffer and move cursor to prompt position
      elif Key.Code()=="ESCAPE":
        debug.Get().Send("Escape key pressed: clearing command buffer")
        terminal.MoveCursorLinear(-CursorOffset)
        terminal.Write(" "*(len(CommandBuffer)+len(GhostSuggestion)), Restore=True)
        CursorOffset=0
        CommandBuffer=""
        HistoryIndex=-1
        GhostSuggestion=""
        GhostIndex=0
        PrevGhostIndex=0

      #Ctrl-C: Copy selection to clipboard if selection exists
      elif Key.Code()=="CTRL+C":
        
        #If selection exists, copy to clipboard and clear selection
        if SelectionBegin!=None:
          
          #Copy selected text to clipboard
          Start=min(SelectionBegin,SelectionEnd)
          End=max(SelectionBegin,SelectionEnd)
          SelectedText=CommandBuffer[Start:End]
          terminal.ClipboardCopy(SelectedText)
          debug.Get().Send(f"Copied selection to clipboard: {SelectedText!r}")

          #Clear selection
          terminal.MoveCursorLinear(-CursorOffset)
          terminal.Write(CommandBuffer+" "*(len(GhostSuggestion)), Restore=True)
          terminal.MoveCursorLinear(+CursorOffset)
          SelectionBegin=None
          SelectionEnd=None
      
      #Ctrl-D: Terminate shell
      elif Key.Code()=="CTRL+D":
        terminal.Write("\n")
        break
      
      #Enter
      elif Key.Code()=="RETURN":
        
        #Move cursor to end of line
        terminal.MoveCursorLinear(len(CommandBuffer)-CursorOffset)
        CursorOffset=len(CommandBuffer)
        
        #Clear ghost suggestion from terminal
        terminal.Write(" "*(len(GhostSuggestion)), Restore=True)
        GhostSuggestion=""
        GhostIndex=0
        terminal.Write("\n")
        
        #Execute command
        Result=self.Dispatcher.ExecuteCommand(CommandBuffer)
        if Result.Event==dispatcher.DispatcherResult.TERMINATE:
          break
        if Result.Event==dispatcher.DispatcherResult.DISPATCHER_ERROR:
          terminal.Write(ansi.SetFgColor(ErrorMessageColor)+f"Error: {Result.Output}"+ansi.ResetColor()+"\n")
        
        #Store command in history
        self.History.Store(CommandBuffer)
        
        #Write extra line if current cursor position is not the beginning of a new line
        if terminal.GetCursorPos()[1]!=1:
          terminal.Write("\n")
        
        #Reset command buffer and state
        CommandBuffer=""
        terminal.Write(self.Prompt.Get())
        CursorOffset=0
        HistoryIndex=-1
      
      #Printable character: Insert into command buffer (no overwrite) and update terminal
      #(Clear selection if enabled)
      elif len(InputChars)!=0:
        if SelectionBegin!=None:
          Start=min(SelectionBegin,SelectionEnd)
          End=max(SelectionBegin,SelectionEnd)
          CommandBuffer=CommandBuffer[:Start]+CommandBuffer[End:]
          terminal.MoveCursorLinear(-CursorOffset)
          terminal.Write(CommandBuffer+" "*len(GhostSuggestion)+" "*(End-Start), Restore=True)
          CursorOffset=Start
          terminal.MoveCursorLinear(CursorOffset)
          SelectionBegin=None
          SelectionEnd=None
        CommandBuffer=CommandBuffer[:CursorOffset]+InputChars+CommandBuffer[CursorOffset:]
        terminal.Write(InputChars+CommandBuffer[CursorOffset+len(InputChars):])
        terminal.MoveCursorLinear(CursorOffset+len(InputChars)-len(CommandBuffer))
        CursorOffset+=len(InputChars)
        InputChars=""
      
      #Update ghost suggestion on command buffer change only if cursor is at the end of the buffer
      GhostSuggestionClear=False
      if len(CommandBuffer)!=0 and CursorOffset==len(CommandBuffer) and (CommandBuffer!=PrevCommandBuffer or PrevCursorOffset!=CursorOffset or PrevGhostIndex!=GhostIndex):
        GhostSelected=self.History.GetGhostSuggestion(CommandBuffer,GhostIndex)
        if GhostSelected!=None:
          if len(GhostSuggestion)!=0:
            ExtraSpace=1 if Key.Code()=="BACKSPACE" else 0
            terminal.Write(" "*(len(GhostSuggestion)+ExtraSpace), Restore=True)
          terminal.Write(ansi.SetFgColor(GhostSuggestionColor)+GhostSelected+ansi.ResetColor(), Restore=True)
          GhostSuggestion=GhostSelected
          debug.Get().Send("Ghost suggestion updated: "+GhostSuggestion)
        elif len(GhostSuggestion)!=0:
          GhostSuggestionClear=True
          debug.Get().Send("Ghost suggestion clear mode 1")
      elif len(GhostSuggestion)!=0 and (CursorOffset!=len(CommandBuffer) or len(CommandBuffer)==0):
        GhostSuggestionClear=True
        debug.Get().Send("Ghost suggestion clear mode 2")
      if GhostSuggestionClear==True:
        debug.Get().Send("Ghost suggestion clear triggered")
        ExtraSpace=1 if Key.Code()=="BACKSPACE" else 0
        terminal.MoveCursorLinear(len(CommandBuffer)+ExtraSpace-CursorOffset)
        terminal.Write(" "*(len(GhostSuggestion)), Restore=True)
        terminal.MoveCursorLinear(-(len(CommandBuffer)+ExtraSpace-CursorOffset))
        GhostSuggestion=""
        GhostIndex=0
      
      #Save previous command buffer
      PrevCommandBuffer=CommandBuffer
      PrevCursorOffset=CursorOffset
      PrevGhostIndex=GhostIndex
