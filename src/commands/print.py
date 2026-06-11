#Import libraries
import os
import debug

#Command metadatap
def Get():
  return {
    "name":"print",
    "description":"Prints text to the console (escaped & with new line at end)\n(interpret escape sequences and adds a newline at the end by default)",
    "options":[
      {"type":"positional","name":"Text","index":1,"mandatory":False,"display":"<text>", "description":"Text to write to the console"},
      {"type":"flag","name":"NoEscape","regex":r"^--no-escape$","display":"--no-escape", "description":"Does not interpret escape sequences (all the ones supported by Python's unicode_escape decoding)"},
      {"type":"flag","name":"NoNewLine","regex":r"^--no-newln$","display":"--no-newln", "description":"Does not adds a newline at the end of the text"},
    ],
    "examples":[
      {"command":"print HelloWorld!", "description":"Writes 'HelloWorld!' to the console"},
      {"command":"print \"Hello, world!\"", "description":"Writes 'Hello, world!' to the console"},
      {"command":"print --no-escape \"Line1\\nLine2\"", "description":"Writes 'Line1\\nLine2' without interpreting the escape sequence"},
      {"command":"print --no-newln \"Hello, world!\"", "description":"Writes 'Hello, world!' without adding a newline at the end"},
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    if Options.Text is None:
      Text=""
    else:
      Text=Options.Text
    if Options.NoEscape==False:
      Text=Text.encode().decode('unicode_escape')
    print(Text,end="",flush=True)
    if Options.NoNewLine==False:
      print()
  except Exception as Ex:
    print("Error writing to console:",Ex)
    return False
  return True