"""Default mask for the form.py module"""

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
