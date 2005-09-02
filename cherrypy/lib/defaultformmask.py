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

from xml.sax.saxutils import quoteattr as q


def selected(value):
    """If value is True, return a valid XHTML 'selected' attribute, else ''."""
    if value:
        return ' selected="selected" '
    return ''

def checked(value):
    """If value is True, return a valid XHTML 'checked' attribute, else ''."""
    if value:
        return ' checked="checked" '
    return ''


def defaultMask(field):
    
    res = ["<tr>",
           "<td valign='top'>%s</td>" % field.label]
    
    if field.typ == 'text':
        res.append('<td><input name=%s type="text" value=%s size=%s /></td>'
                   % (q(field.name), q(field.currentValue), q(field.size)))
    elif field.typ == 'forced':
        res.append('<td><input name=%s type="hidden" value=%s />%s</td>'
                   % (q(field.name), q(field.currentValue), field.currentValue))
    elif field.typ == 'password':
        res.append('<td><input name=%s type="password" value=%s /></td>'
                   % (q(field.name), q(field.currentValue)))
    elif field.typ == 'select':
        res.append('<td><select name=%s>' % q(field.name))
        for option in field.optionList:
            if isinstance(option, tuple):
                id, option = option
                sel = selected(field.currentValue in (id, str(id)))
                value = " value=%s" % q(id)
            else:
                sel = selected(option == field.currentValue)
                value = ""
            res.append("    <option%s%s>%s</option>" % (sel, value, option))
        res.append('</select></td>')
    elif field.typ == 'textarea':
        # Size is cols x rows
        if field.size == 15:
            size = "15x15"
        else:
            size = field.size
        cols, rows = size.split('x')
        res.append('<td><textarea name=%s rows="%s" cols="%s">%s</textarea></td>'
                   % (q(field.name), rows, cols, field.currentValue))
    elif field.typ == 'submit':
        res.append('<td><input type="submit" value=%s /></td>' % q(field.name))
    elif field.typ == 'hidden':
        if isinstance(field.currentValue, list):
            vals = field.currentValue
        else:
            vals = [field.currentValue]
        i = '<input name=%s type="hidden" value=%%s />' % q(field.name)
        return [i % q(v) for v in vals]
    elif field.typ in ('checkbox', 'radio'):
        res.append('<td>')
        for option in field.optionList:
            if isinstance(option, tuple):
                val, label = option
            else:
                val, label = option, option
            
            if isinstance(field.currentValue, list):
                c = checked(val in field.currentValue)
            else:
                c = checked(val == field.currentValue)
            
            res.append('<input type="%s" name=%s value=%s %s />&nbsp;&nbsp;%s<br />'
                       % (field.typ, q(field.name), q(val), c, label))
        res.append('</td>')
    
    if field.errorMessage:
        res.append("<td><font color='red'>%s</font></td>" % field.errorMessage)
    else:
        res.append("<td>&nbsp;</td>")
    
    res.append("</tr>")
    return "\n".join(res)

def hiddenMask(field):
    if isinstance(field.currentValue, list):
        currentValue = field.currentValue
    else:
        currentValue = [field.currentValue]
    return "\n".join(['<input name=%s type="hidden" value=%s />' %
                      (q(field.name), q(value)) for value in currentValue])

def defaultHeader(label):
    return "<table>"

def defaultFooter(label):
    return "</table>"

def echoMask(label):
    return label
