<?xml version='1.0'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:fo="http://www.w3.org/1999/XSL/Format"
  xmlns:xi='http://www.w3.org/2001/XInclude'
  xmlns:exsl="http://exslt.org/common"
  version='1.0'>
  <xsl:include href="html.xsl"/>
  <xsl:param name="generate.toc">
    book      toc
    appendix  toc
  </xsl:param>
  <xsl:param name="base.dir" select="''"/>
  <xsl:param name="suppress.navigation">1</xsl:param>  
</xsl:stylesheet>