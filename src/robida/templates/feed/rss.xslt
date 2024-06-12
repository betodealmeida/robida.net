<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.1" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="html"/>
    <xsl:template match="/rss/channel">
        <html>
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title><xsl:value-of select="title"/></title>
                {% for link in links %}
                <link rel="{{ link.rel }}" href="{{ url_for(link.endpoint, _external=True) }}"/>
                {% endfor %}
                <link rel="stylesheet" href="{{ url_for('static', filename='css/simple.min.css') }}"/>
                <link rel="stylesheet" href="{{ url_for('static', filename='css/custom.css') }}"/>
                <script>
                    <![CDATA[
                        /*
                         * Firefox doesn't support `disable-output-escaping="yes"`,
                         * so we need to unescape the HTML content manually.
                         *
                         * See this bug ticket from 2001 (!): https://bugzilla.mozilla.org/show_bug.cgi?id=98168
                         */
                        function isFirefox() {
                            return navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
                        }

                        function unescapeHTML(escapedHTML) {
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = escapedHTML;
                            return tempDiv.textContent || tempDiv.innerText || "";
                        }

                        addEventListener("DOMContentLoaded", function() {
                            if (isFirefox()) {
                                const divElements = document.querySelectorAll('div.e-content');
                                divElements.forEach(div => {
                                    const escapedHTML = div.innerHTML;
                                    const unescapedHTML = unescapeHTML(escapedHTML);
                                    div.innerHTML = unescapedHTML;
                                });
                            }
                        });
                    ]]>
                </script>
            </head>
            <body>
                <header>
                    <h1>{{ title|default(config.SITE_NAME) }}</h1>
                </header>

                <main>
                    <div class="h-feed">
                        <h1 class="p-name">
                            <a>
                                <xsl:attribute name="href">
                                    <xsl:value-of select="link"/>
                                </xsl:attribute>
                                <xsl:value-of select="title"/>
                            </a>
                        </h1>

                        <p class="p-summary"><xsl:value-of select="description"/></p>

                        <xsl:apply-templates select="item"/>
                    </div>
                </main>

                <footer>
                    <p>
                        <a
                            class="copyright"
                            href="https://creativecommons.org/licenses/by-sa/4.0/"
                            title="CC BY-SA 4.0"
                        >
                            <img src="/static/img/cc.svg" alt="CC"/>
                            <img src="/static/img/by.svg" alt="BY"/>
                            <img src="/static/img/sa.svg" alt="SA"/>
                        </a>
                        2024
                        <a href="https://github.com/betodealmeida/robida.net/">robida.net</a>
                    </p>
                </footer>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="item">
        <article class="h-entry">
            <xsl:if test="title">
                <h1 class="p-name"><xsl:value-of select="title"/></h1>
            </xsl:if>

            <div class="e-content">
                <xsl:value-of select="description" disable-output-escaping="yes"/>
            </div>

            <footer>
                <p>
                    <time class="dt-published">
                        <xsl:attribute name="datetime">
                            <xsl:value-of select="pubDate"/>
                        </xsl:attribute>
                        <xsl:value-of select="pubDate"/>
                    </time>
                </p>
            </footer>
        </article>
    </xsl:template>
</xsl:stylesheet>
