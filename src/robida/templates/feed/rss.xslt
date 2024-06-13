<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    version="1.1"
    xmlns:extensions="https://robida.net/rss/extensions"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
>
    <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/rss/channel">
        <html>
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title><xsl:value-of select="extensions:title"/></title>
                {% for link in links %}
                <link rel="{{ link.rel }}" href="{{ url_for(link.endpoint, _external=True) }}"/>
                {% endfor %}
                <link rel="stylesheet" href="{{ url_for('static', filename='css/pico.fluid.classless.min.css') }}"/>
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
                                const divElements = document.querySelectorAll('.safe');
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
                    <nav>
                        <ul>
                            <li>
                                <strong>
                                    <a href="{{ url_for('homepage.index') }}">
                                        Home
                                    </a>
                                </strong>
                            </li>
                        </ul>
                        <ul>
                            <li><a href="{{ url_for('feed.index') }}">Feed</a></li>
                            <li><a href="{{ url_for('feed.entry', uuid='8bf10ece-be18-4b96-af91-04e5c2a931ad') }}">About</a></li>
                            <li><a href="https://github.com/betodealmeida/robida.net/">Source</a></li>
                        </ul>
                    </nav>
                </header>

                <main>
                    <div class="h-feed">
                        <hgroup>
                            <h1 class="p-name">
                                <a href="{link}"><xsl:value-of select="title"/></a>
                            </h1>
                            <p class="p-summary"><xsl:value-of select="description"/></p>
                        </hgroup>

                        <xsl:apply-templates select="item"/>
                    </div>
                </main>

                <footer>
                    <p>
                        <form role="search" method="GET" action="/search">
                            <input name="q" type="search"/>
                            <input type="submit" value="Search"/>
                        </form>
                    </p>
                    <p style="text-align: center;">
                        🍃
                        <a
                            class="copyright"
                            href="https://creativecommons.org/licenses/by-sa/4.0/"
                            title="CC BY-SA 4.0"
                        >
                            <img src="/static/img/cc.svg" alt="CC" style="height: 1.0em;"/>
                            <img src="/static/img/by.svg" alt="BY" style="height: 1.0em;"/>
                            <img src="/static/img/sa.svg" alt="SA" style="height: 1.0em;"/>
                        </a>
                        2024
                        <a href="https://github.com/betodealmeida/robida.net/">robida.net</a>
                        🍃
                    </p>
                </footer>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="item">
        <article class="h-entry">
            <xsl:choose>
                <xsl:when test="title">
                    <!-- article -->
                    <header>
                        <hgroup>
                            <h1 class="p-name"><xsl:value-of select="title"/></h1>
                            <xsl:if test="extensions:summary">
                                <p class="p-summary"><xsl:value-of select="extensions:summary"/></p>
                            </xsl:if>
                        </hgroup>
                    </header>

                    <div class="e-content safe">
                        <xsl:value-of select="description" disable-output-escaping="yes"/>
                    </div>
                </xsl:when>
                <xsl:otherwise>
                    <!-- note -->
                    <p class="p-content e-content">
                        <xsl:value-of select="description"/>
                    </p>
                </xsl:otherwise>
            </xsl:choose>

            <footer>
                <p>
                    <span class="safe">
                        <xsl:value-of select="extensions:type_emoji" disable-output-escaping="yes"/>
                    </span>
                    <xsl:apply-templates select="extensions:author"/>
                    @
                    <a href="{link}" class="u-url">
                        <time class="dt-published" datetime="{extensions:last_modified_at}">
                            <xsl:value-of select="pubDate"/>
                        </time>
                        ⚓
                    </a>
                </p>
            </footer>
        </article>
    </xsl:template>

    <xsl:template match="extensions:author">
        Published by <a class="h-card" href="{extensions:url}">
            <xsl:value-of select="extensions:name"/>
        </a>
    </xsl:template>
</xsl:stylesheet>
