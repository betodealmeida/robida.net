<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    version="1.1"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:extensions="https://robida.net/atom/extensions"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
>
    <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
    <xsl:template match="/atom:feed">
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
            <head>
                <meta charset="UTF-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
                <title><xsl:value-of select="extensions:title"/></title>
                {% for link in links %}
                <link rel="{{ link.rel }}" href="{{ url_for(link.endpoint, _external=True) }}"/>
                {% endfor %}
                <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}"/>
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
                                🏡
                                <strong>
                                    <a href="{{ url_for('homepage.index') }}">
                                        Home
                                    </a>
                                </strong>
                            </li>
                        </ul>
                        <ul>
                            <li>📓 <a href="{{ url_for('feed.index') }}">Feed</a></li>
                            <li>💁🏽   <a href="/about">About</a></li>
                            {% if session.me %}
                            <li><strong>{{ session.me }}</strong></li>
                            <li>🔑 <a href="{{ url_for('auth.logout') }}">Logout</a></li>
                            {% else %}
                            <li>🔑 <a href="{{ url_for('auth.login') }}">Login</a></li>
                            {% endif %}
                        </ul>
                    </nav>
                </header>

                <main>
                    <div class="h-feed">
                        <header>
                            <hgroup>
                                <h1 class="p-name">
                                    <a href="{atom:id}"><xsl:value-of select="atom:title"/></a>
                                </h1>
                                <p class="p-summary"><xsl:value-of select="atom:subtitle"/></p>
                            </hgroup>
                        </header>

                        <xsl:apply-templates select="atom:entry"/>
                    </div>

                    <footer class="pagination">
                        <xsl:choose>
                            <xsl:when test="extensions:previous_url">
                                <a href="{extensions:previous_url}">« Previous</a>
                            </xsl:when>
                            <xsl:otherwise>
                                <span/>
                            </xsl:otherwise>
                        </xsl:choose>

                        <xsl:choose>
                            <xsl:when test="extensions:next_url">
                                <a href="{extensions:next_url}">Next »</a>
                            </xsl:when>
                            <xsl:otherwise>
                                <span/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </footer>
                </main>

                <footer>
                    <p>
                        <form role="search" method="GET" action="{{ url_for('search.index') }}">
                            <input
                                name="q"
                                type="search"
                                placeholder="Try: python OR Flask, NEAR(like, entry), vegan AND recipes"
                            />
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

    <xsl:template match="atom:entry">
        <article class="h-entry">
            <xsl:choose>
                <xsl:when test="atom:title">
                    <!-- article -->
                    <header>
                        <hgroup>
                            <h1 class="p-name"><xsl:value-of select="atom:title"/></h1>
                            <xsl:if test="atom:summary">
                                <p class="p-summary"><xsl:value-of select="atom:summary"/></p>
                            </xsl:if>
                        </hgroup>
                    </header>

                    <div class="safe">
                        <xsl:value-of select="atom:content" disable-output-escaping="yes"/>
                    </div>
                </xsl:when>
                <xsl:otherwise>
                    <div class="safe">
                        <xsl:value-of select="atom:content" disable-output-escaping="yes"/>
                    </div>
                </xsl:otherwise>
            </xsl:choose>

            <footer>
                <p>
                    <span class="safe">
                        <xsl:value-of select="extensions:type_emoji" disable-output-escaping="yes"/>
                    </span>
                    <xsl:apply-templates select="atom:author"/>
                    @
                    <a href="{atom:id}" class="u-url">
                        <time class="dt-published" datetime="{atom:updated}">
                            <xsl:value-of select="extensions:updated"/>
                        </time>
                        ⚓
                    </a>

                    <xsl:apply-templates select="atom:category"/>
                </p>
            </footer>
        </article>
    </xsl:template>

    <xsl:template match="atom:category">
        <a href="{@extensions:category_url}" class="p-category">
            <mark><xsl:value-of select="@term"/></mark>
        </a>
    </xsl:template>

    <xsl:template match="atom:author">
        Published by <a class="h-card" href="{atom:uri}">
            <xsl:value-of select="atom:name"/>
        </a>
    </xsl:template>
</xsl:stylesheet>
