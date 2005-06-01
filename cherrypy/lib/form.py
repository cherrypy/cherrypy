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
Simple form handling module.
"""

from cherrypy import cpg
import defaultformmask

class FormField:
    def __init__(self, label, name, typ, mask=None, mandatory=0, size=15, optionList=[], defaultValue='', defaultMessage='', validate=None):
        self.isField=1
        self.label=label
        self.name=name
        self.typ=typ
        if not mask: self.mask=defaultformmask.defaultMask
        else: self.mask=mask
        self.mandatory=mandatory
        self.size=size
        self.optionList=optionList
        self.defaultValue=defaultValue
        self.defaultMessage=defaultMessage
        self.validate=validate
        self.errorMessage=""
    def render(self, leaveValues):
        if leaveValues:
            if self.typ!='submit':
                if cpg.request.paramMap.has_key(self.name): self.currentValue=cpg.request.paramMap[self.name]
                else: self.currentValue=""
            else: self.currentValue=self.defaultValue
        else:
            self.currentValue=self.defaultValue
            self.errorMessage=self.defaultMessage
        return self.mask(self)

class FormSeparator:
    def __init__(self, label, mask):
        self.isField=0
        self.label=label
        self.mask=mask
    def render(self, dummy):
        return self.mask(self.label)

class Form:
    method="post"
    enctype=""
    def formView(self, leaveValues=0):
        if self.enctype: enctypeTag='enctype="%s"'%self.enctype
        else: enctypeTag=""
        res='<form method="%s" %s action="postForm">'%(self.method, enctypeTag)
        for field in self.fieldList:
            res+=field.render(leaveValues)
        return res+"</form>"
    def validateFields(self):
        # Should be subclassed
        # Update field's errorMessage value to set an error
        pass
    def validateForm(self):
        # Reset errorMesage for each field
        for field in self.fieldList:
            if field.isField: field.errorMessage=""

        # Validate mandatory fields
        for field in self.fieldList:
            if field.isField and field.mandatory and (not cpg.request.paramMap.has_key(field.name) or not cpg.request.paramMap[field.name]): field.errorMessage="Missing"

        # Validate fields one by one
        for field in self.fieldList:
            if field.isField and field.validate and not field.errorMessage:
                if cpg.request.paramMap.has_key(field.name): value=cpg.request.paramMap[field.name]
                else: value=""
                field.errorMessage=field.validate(value)

        # Validate all fields together (ie: check that passwords match)
        self.validateFields()
        for field in self.fieldList:
            if field.isField and field.errorMessage: return 0
        return 1
    def setFieldErrorMessage(self, fieldName, errorMessage):
        for field in self.fieldList:
            if field.isField and field.name==fieldName: field.errorMessage=errorMessage
    def getFieldOptionList(self, fieldName):
        for field in self.fieldList:
            if field.isField and field.name==fieldName: return field.optionList
    def getFieldDefaultValue(self, fieldName):
        for field in self.fieldList:
            if field.isField and field.name==fieldName: return field.defaultValue
    def setFieldDefaultValue(self, fieldName, defaultValue):
        for field in self.fieldList:
            if field.isField and field.name==fieldName: field.defaultValue=defaultValue

    def getFieldNameList(self, exceptList=[]):
        fieldNameList=[]
        for field in self.fieldList:
            if field.isField and field.name and field.name not in exceptList: fieldNameList.append(field.name)
        return fieldNameList


