<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:atom="http://www.w3.org/2005/Atom"
>
    <xsl:template match="/atom:feed">
        <html>
            <head>
                <title><xsl:value-of select="atom:title"/></title>
                <style>
                    body { font-family: Arial, sans-serif; }
                    h1 { color: #2E8B57; }
                    .item { border-bottom: 1px solid #ccc; padding: 10px; }
                    .item-title { font-size: 1.2em; font-weight: bold; }
                    .item-description { margin-top: 5px; }
                </style>
            </head>
            <body>
                <h1><xsl:value-of select="atom:title"/></h1>
                <p><xsl:value-of select="atom:subtitle"/></p>
                <div class="items">
                    <xsl:apply-templates select="atom:entry"/>
                </div>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="atom:entry">
        <div class="item">
            <div class="item-title">
                <a href="{atom:link/@href}"><xsl:value-of select="atom:title"/></a>
            </div>
            <div class="item-description">
                <xsl:value-of select="atom:summary"/>
            </div>
        </div>
    </xsl:template>
</xsl:stylesheet>
