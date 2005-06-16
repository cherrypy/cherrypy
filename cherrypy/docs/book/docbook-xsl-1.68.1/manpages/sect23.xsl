<?xml version='1.0'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version='1.0'>

<xsl:template match="refsect2">
  <xsl:text>&#10;.Sh "</xsl:text>
  <xsl:value-of select="substring-before(title[1],' ')"/>
  <xsl:text>"&#10;</xsl:text>
  <xsl:apply-templates/>
</xsl:template>
<xsl:template match="refsect2/title"></xsl:template>
<xsl:template match="refsect2/programlisting"></xsl:template>

<xsl:template match="funcsynopsis">
  <xsl:text>&#10;.BI "</xsl:text>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="funcsynopsis/funcprototype">
  <xsl:apply-templates/>
  <xsl:text> );&#10;.br&#10;</xsl:text>
</xsl:template>

<xsl:template match="funcsynopsis/funcprototype/funcdef">
  <xsl:apply-templates/>
  <xsl:value-of select="function"/>
  <xsl:text> (</xsl:text>
</xsl:template>
<xsl:template match="funcsynopsis/funcprototype/funcdef/function"></xsl:template>

<xsl:template match="funcsynopsis/funcprototype/paramdef">
  <xsl:apply-templates/>
  <xsl:text>" </xsl:text>
  <xsl:value-of select="parameter"/>
  <xsl:choose>
  <xsl:when test="following-sibling::paramdef">
    <xsl:text> ", </xsl:text>
  </xsl:when>
  </xsl:choose>
</xsl:template>
<xsl:template match="funcsynopsis/funcprototype/paramdef/parameter"></xsl:template>

<xsl:template match="refsect2/informaltable/tgroup/tbody/row">
  <xsl:text>.Ip "\(bu \s-1</xsl:text>
  <xsl:value-of select="entry[1]/parameter[1]"/>
  <xsl:text>\s0 \- </xsl:text>
  <xsl:value-of select="normalize-space(entry[2])"/>
  <xsl:text>"&#10;</xsl:text>
</xsl:template>

<xsl:template match="refsect1">
  <xsl:text>&#10;.SH "</xsl:text>
  <xsl:value-of select="translate(title[1],'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')"/>
  <xsl:text>"&#10;</xsl:text>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="refsynopsisdiv">
  <xsl:text>&#10;.SH "</xsl:text>
  <xsl:value-of select="translate(title[1],'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')"/>
  <xsl:text>"&#10;</xsl:text>
  <xsl:apply-templates/>
</xsl:template>
<xsl:template match="refsynopsisdiv/title"></xsl:template>

<xsl:template match="refsect1/title"></xsl:template>

<xsl:template match="para">
     <xsl:text>.PP&#10;</xsl:text>
     <xsl:apply-templates/>
</xsl:template>

<xsl:template match="*"><xsl:apply-templates/></xsl:template>

<xsl:template match="refentry">
  <xsl:text>." DO NOT MODIFY THIS FILE!
.de Sh \" Subsection
.br
.if t .Sp
.ne 5
.PP
\fB\\$1\fR
.PP
..
.de Sp \" Vertical space (when we can't use .PP)
.if t .sp .5v
.if n .sp
..
.de Ip \" List item
.br
.ie \\n(.$>=3 .ne \\$3
.el .ne 3
.IP "\\$1" \\$2
..
.TH "</xsl:text>
  <xsl:value-of select="refmeta/refentrytitle[1]"/>
  <xsl:text>" </xsl:text>
  <xsl:value-of select="refmeta/manvolnum[1]"/>
  <xsl:text> "</xsl:text>
  <xsl:value-of select="@revision"/>
  <xsl:text>"&#10;</xsl:text>
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="refmeta"></xsl:template>

<xsl:template match="refnamediv">
  <xsl:text>.SH NAME&#10;</xsl:text>
  <xsl:value-of select="refname"/>
  <xsl:text> \- </xsl:text>
  <xsl:value-of select="refpurpose"/>
</xsl:template>

<xsl:template match="refentry/refentrytitle"></xsl:template>
<xsl:template match="article/articleinfo/*"></xsl:template>

<xsl:template match="term/option">
  <xsl:text>\fB</xsl:text><xsl:apply-templates/><xsl:text>\fR</xsl:text>
</xsl:template>

<xsl:template match="varlistentry">
  <xsl:text>&#10;.TP&#10;</xsl:text>
<xsl:apply-templates select="./term"/>
<xsl:apply-templates select="./listitem"/>
</xsl:template>

<xsl:template match="varlistentry/listitem/para">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="filename">
  <xsl:text>&#10;.FN </xsl:text><xsl:apply-templates/>
</xsl:template>

<xsl:template match="userinput">
  <xsl:text>&#10;.IP&#10;.B </xsl:text><xsl:apply-templates/>
</xsl:template>

<xsl:template match="envar">
  <xsl:text>\fB</xsl:text><xsl:apply-templates/><xsl:text>\fR</xsl:text>
</xsl:template>

<xsl:template match="filename">
  <xsl:text>\fI</xsl:text><xsl:apply-templates/><xsl:text>\fR</xsl:text>
</xsl:template>

</xsl:stylesheet>
