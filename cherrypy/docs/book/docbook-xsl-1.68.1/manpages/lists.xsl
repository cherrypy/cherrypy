<?xml version='1.0'?>
<!-- vim:set sts=2 shiftwidth=2 syntax=sgml: -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version='1.0'>

<xsl:template match="para[ancestor::listitem or ancestor::step]|
	             simpara[ancestor::listitem or ancestor::step]|
		     remark[ancestor::listitem or ancestor::step]">
  <xsl:for-each select="node()">
    <xsl:choose>
      <xsl:when test="self::literallayout|self::screen|self::programlisting|
		      self::itemizedlist|self::orderedlist|self::variablelist|
		      self::simplelist">
        <xsl:text>&#10;</xsl:text>
        <xsl:apply-templates select="."/>
      </xsl:when>
      <xsl:when test="self::text()">
	<xsl:if test="starts-with(translate(.,'&#10;',' '), ' ') and
		      preceding-sibling::node()[name(.)!='']">
	  <xsl:text> </xsl:text>
	</xsl:if>
        <xsl:variable name="content">
	  <xsl:apply-templates select="."/>
	</xsl:variable>
	<xsl:value-of select="normalize-space($content)"/>
	<xsl:if
        test="translate(substring(., string-length(.), 1),'&#10;',' ') = ' '
	      and following-sibling::node()[name(.)!='']">
	  <xsl:text> </xsl:text>
	</xsl:if>
      </xsl:when>
      <xsl:otherwise>
        <xsl:variable name="content">
          <xsl:apply-templates select="."/>
        </xsl:variable>
        <xsl:value-of select="normalize-space($content)"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:for-each>
  <xsl:text>&#10;</xsl:text>

  <xsl:if test="following-sibling::para or
	  following-sibling::simpara or
	  following-sibling::remark">
    <!-- Make sure multiple paragraphs within a list item don't -->
    <!-- merge together.                                        -->
    <xsl:text>&#10;</xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="varlistentry|glossentry">
  <xsl:text>&#10;.TP&#10;</xsl:text>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="variablelist[ancestor::listitem or ancestor::step]|
	             glosslist[ancestor::listitem or ancestor::step]">
  <xsl:text>&#10;.RS&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>&#10;.RE&#10;.IP&#10;</xsl:text>
</xsl:template>

<xsl:template match="varlistentry/term|glossterm">
  <xsl:variable name="content">
    <xsl:apply-templates/>
  </xsl:variable>
  <xsl:value-of select="normalize-space($content)"/>
  <xsl:text>, </xsl:text>
</xsl:template>

<xsl:template
     match="varlistentry/term[position()=last()]|glossterm[position()=last()]"
     priority="2">
  <xsl:variable name="content">
    <xsl:apply-templates/>
  </xsl:variable>
  <xsl:value-of select="normalize-space($content)"/>
</xsl:template>

<xsl:template match="varlistentry/listitem|glossdef">
  <xsl:text>&#10;</xsl:text>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="itemizedlist/listitem">
  <xsl:text>\(bu&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:if test="following-sibling::listitem">
    <xsl:text>.TP&#10;</xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="orderedlist/listitem|procedure/step">
  <xsl:number format="1."/>
  <xsl:text>&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:if test="position()!=last()">
    <xsl:text>.TP&#10;</xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="itemizedlist|orderedlist|procedure">
  <xsl:text>&#10;.TP 3&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>.LP&#10;</xsl:text>
</xsl:template>

<xsl:template match="itemizedlist[ancestor::listitem or ancestor::step]|
	             orderedlist[ancestor::listitem or ancestor::step]|
		     procedure[ancestor::listitem or ancestor::step]">
  <xsl:text>&#10;.RS&#10;.TP 3&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>.LP&#10;.RE&#10;.IP&#10;</xsl:text>
</xsl:template>

<!-- simplelist -->

<xsl:template match="simplelist[@type='inline']">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="simplelist[@type='inline']/member">
  <xsl:apply-templates/>
  <xsl:text>, </xsl:text>
</xsl:template>

<xsl:template match="simplelist[@type='inline']/member[position()=last()]"
	      priority="2">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="simplelist[@type='vert' and @columns='1']">
  <xsl:text>&#10;.IP&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>.LP&#10;</xsl:text>
</xsl:template>

<xsl:template match="simplelist[@type='vert' and @columns='1']/member">
  <xsl:apply-templates/>
  <xsl:text>&#10;&#10;</xsl:text>
</xsl:template>

</xsl:stylesheet>
