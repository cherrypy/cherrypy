"""Simple form handling module."""

import warnings
warnings.warn("cherrypy.lib.form is deprecated and might disappear in future versions of CherryPy", DeprecationWarning, stacklevel = 2)

import cherrypy
import defaultformmask


class FormField:
    
    def __init__(self, label, name, typ, mask=None, mandatory=0, size='15',
                 optionList=[], defaultValue='', defaultMessage='', validate=None):
        self.isField = 1
        self.label = label
        self.name = name
        self.typ = typ
        if mask is None:
            self.mask = defaultformmask.defaultMask
        else:
            self.mask = mask
        self.mandatory = mandatory
        self.size = size
        self.optionList = optionList
        self.defaultValue = defaultValue
        self.defaultMessage = defaultMessage
        self.validate = validate
        self.errorMessage = ""
    
    def render(self, leaveValues):
        if leaveValues:
            if self.typ !='submit':
                self.currentValue = cherrypy.request.params.get(self.name, "")
            else:
                self.currentValue = self.defaultValue
        else:
            self.currentValue = self.defaultValue
            self.errorMessage = self.defaultMessage
        return self.mask(self)


class FormSeparator:
    
    def __init__(self, label, mask):
        self.isField = 0
        self.label = label
        self.mask = mask
    
    def render(self, dummy):
        return self.mask(self.label)


class Form:
    
    method = "post"
    enctype = ""

    def __init__(self, action = "postForm", method = "post", enctype = "", header = defaultformmask.defaultHeader, footer = defaultformmask.defaultFooter, headerLabel = "", footerLabel = ""):
        self.action = action
        self.method = method
        self.enctype = enctype
        self.header = header
        self.footer = footer
        self.headerLabel = headerLabel
        self.footerLabel = footerLabel

    def formView(self, leaveValues=0):
        if self.enctype:
            enctypeTag = 'enctype="%s"' % self.enctype
        else:
            enctypeTag = ""
        
        res = ['<form method="%s" %s action="%s">'
               % (self.method, enctypeTag, self.action)]
        res.append(self.header(self.headerLabel))

        for field in self.fieldList:
            res.append(field.render(leaveValues))

        res.append(self.footer(self.footerLabel))
        res.append("</form>")
        
        return "".join(res)
    
    def validateFields(self):
        # Should be subclassed
        # Update field's errorMessage value to set an error
        pass
    
    def validateForm(self):
        # Reset errorMesage for each field
        for field in self.fieldList:
            if field.isField:
                field.errorMessage = ""
        
        # Validate mandatory fields
        for field in self.fieldList:
            if (field.isField and field.mandatory
                and not cherrypy.request.params.get(field.name)):
                field.errorMessage = "Missing"
        
        # Validate fields one by one
        for field in self.fieldList:
            if field.isField and field.validate and not field.errorMessage:
                value = cherrypy.request.params.get(field.name, "")
                field.errorMessage = field.validate(value)

        # Validate all fields together (ie: check that passwords match)
        self.validateFields()
        for field in self.fieldList:
            if field.isField and field.errorMessage:
                return 0
        return 1
    
    def setFieldErrorMessage(self, fieldName, errorMessage):
        for field in self.fieldList:
            if field.isField and field.name == fieldName:
                field.errorMessage = errorMessage
    
    def getFieldOptionList(self, fieldName):
        for field in self.fieldList:
            if field.isField and field.name == fieldName:
                return field.optionList
    
    def getFieldDefaultValue(self, fieldName):
        for field in self.fieldList:
            if field.isField and field.name == fieldName:
                return field.defaultValue
    
    def setFieldDefaultValue(self, fieldName, defaultValue):
        for field in self.fieldList:
            if field.isField and field.name == fieldName:
                field.defaultValue = defaultValue
    
    def getFieldNameList(self, exceptList=[]):
        fieldNameList = []
        for field in self.fieldList:
            if field.isField and field.name and field.name not in exceptList:
                fieldNameList.append(field.name)
        return fieldNameList


