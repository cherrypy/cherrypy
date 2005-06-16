<?xml version='1.0'?>
<!-- vim:set sts=2 shiftwidth=2 syntax=sgml: -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version='1.0'>

<xsl:template match="synopfragment">
<xsl:text>&#10;.PP&#10;</xsl:text>
<xsl:apply-templates/>
</xsl:template>
<!--
  there's a bug were an <arg> that's not inside a <group> isn't made bold
-->

<xsl:template match="group|arg">
  <xsl:variable name="choice" select="@choice"/>
  <xsl:variable name="rep" select="@rep"/>
  <xsl:variable name="sepchar">
    <xsl:choose>
      <xsl:when test="ancestor-or-self::*/@sepchar">
        <xsl:value-of select="ancestor-or-self::*/@sepchar"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text> </xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:variable>
  <xsl:if test="position()>1"><xsl:value-of select="$sepchar"/></xsl:if>
  <xsl:choose>
    <xsl:when test="$choice='plain'">
      <!-- do nothing -->
    </xsl:when>
    <xsl:when test="$choice='req'">
      <xsl:value-of select="$arg.choice.req.open.str"/>
    </xsl:when>
    <xsl:when test="$choice='opt'">
      <xsl:value-of select="$arg.choice.opt.open.str"/>
    </xsl:when>
    <xsl:otherwise>
      <xsl:value-of select="$arg.choice.def.open.str"/>
    </xsl:otherwise>
  </xsl:choose>
  <xsl:variable name="arg">
    <xsl:apply-templates/>
  </xsl:variable>
  <xsl:choose>
    <xsl:when test="local-name(.) = 'arg' and not(ancestor::arg)">
      <!-- Prevent breaking up an argument by wrapping it -->
      <xsl:call-template name="replace-string">
        <xsl:with-param name="content" select="normalize-space($arg)"/>
        <xsl:with-param name="replace" select="' '"/>
        <xsl:with-param name="with" select="'\ '"/>
      </xsl:call-template>
    </xsl:when>
    <xsl:otherwise>
      <xsl:value-of select="normalize-space($arg)"/>
    </xsl:otherwise>
  </xsl:choose>
  <xsl:choose>
    <xsl:when test="$rep='repeat'">
      <xsl:value-of select="$arg.rep.repeat.str"/>
    </xsl:when>
    <xsl:when test="$rep='norepeat'">
      <xsl:value-of select="$arg.rep.norepeat.str"/>
    </xsl:when>
    <xsl:otherwise>
      <xsl:value-of select="$arg.rep.def.str"/>
    </xsl:otherwise>
  </xsl:choose>
  <xsl:choose>
    <xsl:when test="$choice='plain'">
      <xsl:if test='arg'>
      <xsl:value-of select="$arg.choice.plain.close.str"/>
      </xsl:if>
    </xsl:when>
    <xsl:when test="$choice='req'">
      <xsl:value-of select="$arg.choice.req.close.str"/>
    </xsl:when>
    <xsl:when test="$choice='opt'">
      <xsl:value-of select="$arg.choice.opt.close.str"/>
    </xsl:when>
    <xsl:otherwise>
      <xsl:value-of select="$arg.choice.def.close.str"/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match="group/arg">
  <xsl:if test="position()>1">
    <xsl:value-of select="$arg.or.sep"/>
  </xsl:if>
  <!-- Don't use the 'bold' named template here since there may be -->
  <!-- child elements that require different markup (such as       -->
  <!-- <replaceable>).                                             -->
  <xsl:text>\fB</xsl:text>
  <xsl:variable name="arg">
    <xsl:apply-templates/>
  </xsl:variable>
  <xsl:call-template name="replace-string">
    <xsl:with-param name="content" select="normalize-space($arg)"/>
    <xsl:with-param name="replace" select="' '"/>
    <xsl:with-param name="with" select="'\ '"/>
  </xsl:call-template>
  <xsl:text>\fR</xsl:text>
</xsl:template>

<xsl:template match="command">
  <xsl:apply-templates mode="bold" select="."/>
</xsl:template>

<xsl:template match="function[not(ancestor::command)]">
  <xsl:apply-templates mode="bold" select="."/>
</xsl:template>

<xsl:template match="parameter[not(ancestor::command)]">
  <xsl:apply-templates mode="italic" select="."/>
</xsl:template>

<xsl:template match="sbr">
  <xsl:text>&#10;.br&#10;</xsl:text>
</xsl:template>


<xsl:template match="cmdsynopsis">
  <xsl:text>.ad l&#10;.hy 0&#10;</xsl:text>
  <xsl:text>.HP </xsl:text>
  <xsl:value-of select="string-length (normalize-space (command)) + 1"/>
  <xsl:text>&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>&#10;.ad&#10;.hy&#10;</xsl:text>
</xsl:template>

<xsl:template match="synopsis">
  <xsl:text>&#10;.nf&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>&#10;.fi&#10;</xsl:text>
</xsl:template>

<xsl:template match="void">
  <xsl:text>void</xsl:text>
</xsl:template>

<xsl:template match="varargs">
  <xsl:text>...</xsl:text>
</xsl:template>

<xsl:template match="funcsynopsisinfo">
  <xsl:text>&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>&#10;.sp&#10;</xsl:text>
</xsl:template>

<!-- disable hyphenation, and use left-aligned filling for the duration
     of the synopsis, so that line breaks only occur between 
     separate paramdefs. -->
<xsl:template match="funcsynopsis">
  <xsl:text>.ad l&#10;.hy 0&#10;</xsl:text>
  <xsl:apply-templates/>
  <xsl:text>.ad&#10;.hy&#10;</xsl:text>
</xsl:template>

<!-- TODO: Handle K&R-style parameter lists
           Comment that used to go with the paramdef template, which
	   is now obsolete and thus deleted
-->


<!-- replaces all spaces within the funcdef/paramdef with non-breaking
     spaces -->
<xsl:template match="paramdef|funcdef">
  <xsl:variable name="rcontent">
    <xsl:apply-templates select="*|./*|text()"/>
  </xsl:variable>
  <xsl:variable name="content">
    <xsl:value-of select="normalize-space($rcontent)"/>
  </xsl:variable>
  <xsl:call-template name="replace-string">
    <xsl:with-param name="content" select="$content"/>
    <xsl:with-param name="replace" select="' '"/>
    <xsl:with-param name="with" select="'\ '"/>
  </xsl:call-template>
  <xsl:if test="local-name(.) = 'paramdef' and 
	  (following-sibling::paramdef or following-sibling::varargs)">
    <xsl:text>, </xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="funcprototype">
  <xsl:variable name="funcprototype">
    <xsl:apply-templates select="funcdef"/>
  </xsl:variable>
  <xsl:text>.HP </xsl:text>
  <xsl:value-of select="string-length (normalize-space ($funcprototype)) - 5"/>
  <xsl:text>&#10;</xsl:text>
  <xsl:value-of select="normalize-space ($funcprototype)"/>
  <xsl:text>\ (</xsl:text>
  <xsl:apply-templates select="void|paramdef|varargs"/>
  <xsl:text>);&#10;</xsl:text>
</xsl:template>

</xsl:stylesheet>
