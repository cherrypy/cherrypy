<?xml version='1.0'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version='1.0'
                xmlns="http://www.w3.org/TR/xhtml1/transitional"
                exclude-result-prefixes="#default">

  <xsl:import href="../docbook-xsl-1.68.1/htmlhelp/htmlhelp.xsl"/>
  <xsl:include href="html.xsl"/>
  <xsl:param name="base.dir" select="''"/>
  <xsl:param name="htmlhelp.chm" select="'cherrypy.chm'"/>
  <!-- Code from http://lists.oasis-open.org/archives/docbook-apps/200102/msg00058.html -->
  <xsl:param name="use.id.as.filename" select="1"/>
  
  <xsl:param name="generate.index" select="0"/>
  <xsl:variable name="toc.section.depth">2</xsl:variable>

  <xsl:param name="generate.toc">
    book      toc
    appendix  toc
   </xsl:param>
  
  <xsl:param name="suppress.navigation">0</xsl:param>  
 
  <xsl:param name="htmlhelp.show.advanced.search" select="0"/>
  <xsl:param name="htmlhelp.use.hhk" select="1"/>
  <xsl:param name="htmlhelp.hhp.tail">style.css</xsl:param>
  <xsl:param name="htmlhelp.hhp.window" select="'The CherryPy Manual'"/>  
</xsl:stylesheet>
