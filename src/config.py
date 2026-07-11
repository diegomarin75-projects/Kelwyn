#Import libraries
import json

#Module-level configuration object
_Config={}

# ----------------------------------------------------------------------------------
# Load a JSON configuration file that tolerates // comments and multiline strings.
# Args:
#   FilePath (str): Path to the JSON configuration file.
# Returns:
#   tuple[bool,str,dict | None]: Success flag,diagnostic message,and parsed JSON object.
# ----------------------------------------------------------------------------------------------------------------------
def JsonFileParser(FilePath):

  # ----------------------------------------------------------------------------------------------------------------------
  # Replaces new lines inside strings as \n (as standard JSON requires).
  # ----------------------------------------------------------------------------------------------------------------------
  def FixMultilineJson(Content):
    Output=[]
    StringMode=False
    EscapeMode=False
    for Char in Content:
      if StringMode:
        if EscapeMode:
          Output.append(Char)
          EscapeMode=False
        elif Char=="\\":
          Output.append(Char)
          EscapeMode=True
        elif Char=='"':
          Output.append(Char)
          StringMode=False
        elif Char=="\n":
          Output.append("\\n")
        else:
          Output.append(Char)
      else:
        if Char=='"':
          Output.append(Char)
          StringMode=True
        else:
          Output.append(Char)
    return "".join(Output)

  #Load JSON file
  #(comment lines are replaced with empty lines to preserve line numbering for error messages)
  try:
    FileHnd=open(FilePath,"r",encoding="utf-8")
    FileContent=FileHnd.read()
    FileHnd.close()
    FileContent="\n".join([(Line if Line.strip().startswith("//")==False else "") for Line in FileContent.split("\n")])
    FileContent=FixMultilineJson(FileContent)
    JsonObj=json.loads(FileContent)
  except Exception as Ex:
    Message=f"Exception reading configuration file ({FilePath}): {str(Ex)}"
    return False,Message,None

  #Return result
  return True,"",JsonObj

# ---------------------------------------------------------------------------
# Load configuration file into module-level global config object
# Args:
# - FilePath (string): Path to config file
# Returns:
# - bool: Status
# - string: Error message on failure or empty string on success
# ---------------------------------------------------------------------------
def Load(FilePath):
  global _Config
  Status,Message,ConfigObj=JsonFileParser(FilePath)
  if Status==False:
    return False,Message
  _Config=ConfigObj
  return True,""

# ---------------------------------------------------------------------------
# Get module-level configuration object
# Returns:
# - dict: Configuration dictionary
# ---------------------------------------------------------------------------
def Get():
  return _Config

