#Import libraries
import os
import utils
import const
import debug

#Selection routine
def Selector():

  #Return list of regexes and completers
  return [

      # checkout / switch
      {"type":"git_branch1","regex":r'^git\s+checkout(?:\s+(?:-b|-B|--orphan|--track|-t|--detach|-d))?\s+@token$',"completer":Completer},
      {"type":"git_branch2","regex":r'^git\s+switch(?:\s+(?:-c|-C|--create|--force-create|--track|-t|--detach))?\s+@token$',"completer":Completer},

      # merge / rebase
      {"type":"git_branch3","regex":r'^git\s+merge\s+@token$',"completer":Completer},
      {"type":"git_branch4","regex":r'^git\s+rebase(?:\s+--onto\s+\S+)?\s+@token$',"completer":Completer},

      # diff / log / show
      {"type":"git_branch5","regex":r'^git\s+diff\s+@token$',"completer":Completer},
      {"type":"git_branch6","regex":r'^git\s+log\s+@token$',"completer":Completer},
      {"type":"git_branch7","regex":r'^git\s+show\s+@token$',"completer":Completer},

      # reset / restore
      {"type":"git_branch8","regex":r'^git\s+reset\s+@token$',"completer":Completer},
      {"type":"git_branch9","regex":r'^git\s+restore(?:\s+--source)?\s+@token$',"completer":Completer},

      # branch management
      {"type":"git_branch10","regex":r'^git\s+branch(?:\s+(?:-d|-D|-m|-M|-c|-C))?\s+@token$',"completer":Completer},

      # push / pull / fetch
      {"type":"git_branch11","regex":r'^git\s+push(?:\s+\S+)?\s+@token$',"completer":Completer},
      {"type":"git_branch12","regex":r'^git\s+pull(?:\s+\S+)?\s+@token$',"completer":Completer},
      {"type":"git_branch13","regex":r'^git\s+fetch(?:\s+\S+)?\s+@token$',"completer":Completer},

      # cherry-pick
      {"type":"git_branch14","regex":r'^git\s+cherry-pick\s+@token$',"completer":Completer},

      # worktree
      {"type":"git_branch15","regex":r'^git\s+worktree\s+add(?:\s+\S+)?\s+@token$',"completer":Completer},

      # rev-parse / rev-list
      {"type":"git_branch16","regex":r'^git\s+rev-parse\s+@token$',"completer":Completer},
      {"type":"git_branch17","regex":r'^git\s+rev-list\s+@token$',"completer":Completer},

  ]

#Completer routine
def Completer(Token,Config):
  
  #Get colors
  CompleterGitBranchColor=Config.get("completer_git_branch_color",const.DEFAULT_FOREGROUND_COLOR)

  #Init result
  Options=[]

  #Get git branches
  try:
    RetCode,Output=utils.Exec("git for-each-ref refs --format=%(refname:short)",Timeout=5)
    if RetCode!=0:
      debug.Get().Send(f"Git for-each-ref failed with code {RetCode} and output: {Output.replace('\n',' ')!r}")
      return []
    debug.Get().Send(f"Git for-each-ref result: {Output.replace("\n"," ")!r}")
    Branches=list(set([Line.strip().replace("origin/","") for Line in Output.strip("\n").split("\n")]))
    Completions=[Branch for Branch in Branches if Branch.startswith(Token)]
    Options=[{"text":Opt,"value":Opt,"color":CompleterGitBranchColor} for Opt in Completions]
  except Exception as e:
    debug.Get().Send(f"Exception in GitBranchCompleter: {str(e)}")
  
  #Return options
  return Options
    

      