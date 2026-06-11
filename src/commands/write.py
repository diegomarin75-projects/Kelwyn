#Import libraries
import os
import debug

#Command metadatap
def Get():
  return {
    "name":"write",
    "description":"Writes raw text to the console (not escaped & not new line at end)\n(does not interpret escape sequences or add a newline at the end by default)",
    "options":[
      {"type":"positional","name":"Text","index":1,"mandatory":False,"display":"<text>", "description":"Text to write to the console"},
      {"type":"flag","name":"Escape","regex":r"^--escape$","display":"--escape", "description":"Interprets escape sequences (all the ones supported by Python's unicode_escape decoding)"},
      {"type":"flag","name":"NewLine","regex":r"^--newln$","display":"--newln", "description":"Adds a newline at the end of the text"},
    ],
    "examples":[
      {"command":"write HelloWorld!", "description":"Writes 'HelloWorld!' to the console"},
      {"command":"write \"Hello, world!\"", "description":"Writes 'Hello, world!' to the console"},
      {"command":"write --escape \"Line1\\nLine2\"", "description":"Writes 'Line1' and 'Line2' on separate lines"},
      {"command":"write --escape \"Tab\\tSeparated\"", "description":"Writes 'Tab Separated' with a tab space between the words"},
    ]
  }

#Execute command
def Execute(Options,Config):
  try:
    if Options.Text is None:
      Text=""
    else:
      Text=Options.Text
    if Options.Escape:
      Text=Text.encode().decode('unicode_escape')
    print(Text,end="",flush=True)
    if Options.NewLine:
      print()
  except Exception as Ex:
    print("Error writing to console:",Ex)
    return False
  return True