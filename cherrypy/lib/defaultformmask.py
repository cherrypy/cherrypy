"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
Default mask for the form.py module
"""

def defaultMask(field):
    res="<tr><td valign=top>%s</td>"%field.label
    if field.typ=='text':
        res+='<td><input name="%s" type=text value="%s" size=%s></td>'%(field.name, field.currentValue, field.size)
    elif field.typ=='forced':
        res+='<td><input name="%s" type=hidden value="%s">%s</td>'%(field.name, field.currentValue, field.currentValue)
    elif field.typ=='password':
        res+='<td><input name="%s" type=password value="%s"></td>'%(field.name, field.currentValue)
    elif field.typ=='select':
        res+='<td><select name="%s">'%field.name
        for option in field.optionList:
            if type(option)==type(()):
                optionId, optionLabel=option
                if optionId==field.currentValue or str(optionId)==field.currentValue: res+="<option selected value=%s>%s</option>"%(optionId, optionLabel)
                else: res+="<option value=%s>%s</option>"%(optionId, optionLabel)
            else:
                if option==field.currentValue: res+="<option selected>%s</option>"%option
                else: res+="<option>%s</option>"%option
        res+='</select></td>'
    elif field.typ=='textarea':
        # Size is colsxrows
        if field.size==15: size="15x15"
        else: size=field.size
        cols, rows=size.split('x')
        res+='<td><textarea name="%s" rows="%s" cols="%s">%s</textarea></td>'%(field.name, rows, cols, field.currentValue)
    elif field.typ=='submit':
        res+='<td><input type=submit value="%s"></td>'%field.name
    elif field.typ=='hidden':
        if type(field.currentValue)==type([]): currentValue=field.currentValue
        else: currentValue=[field.currentValue]
        res=""
        for value in currentValue:
            res+='<input name="%s" type=hidden value="%s">'%(field.name, value)
        return res
    elif field.typ=='checkbox' or field.typ=='radio':
        res+='<td>'
        # print "##### currentValue:", field.currentValue # TBC
        for option in field.optionList:
            if type(option)==type(()): optionValue, optionLabel=option
            else: optionValue, optionLabel=option, option
            res+='<input type="%s" name="%s" value="%s"'%(field.typ, field.name, optionValue)
            if type(field.currentValue)==type([]):
                if optionValue in field.currentValue: res+=' checked'
            else:
                if optionValue==field.currentValue: res+=' checked'
            res+='>&nbsp;&nbsp;%s<br>'%optionLabel
        res+='</td>'
    if field.errorMessage:
        res+="<td><font color=red>%s</font></td>"%field.errorMessage
    else:
        res+="<td>&nbsp;</td>"
    return res+"</tr>"
def hiddenMask(field):
        if type(field.currentValue)==type([]): currentValue=field.currentValue
        else: currentValue=[field.currentValue]
        res=""
        for value in currentValue:
            res+='<input name="%s" type=hidden value="%s">'%(field.name, value)
        return res
def defaultHeader(label):
    return "<table>"
def defaultFooter(label):
    return "</table>"
def echoMask(label):
    return label
