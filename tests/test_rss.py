import pytest

from src.monitor.rss import parse_feed

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>PETR4 sobe com petroleo</title>
      <link>https://example/1</link>
      <description><![CDATA[<p>Noticia &amp; analise</p>]]></description>
      <pubDate>Mon, 16 Nov 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>CDB rende mais</title>
      <link>https://example/2</link>
      <description>Texto simples</description>
    </item>
  </channel>
</rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>ETF de renda fixa</title>
    <link href="https://example/3" />
    <summary>Resumo do ETF</summary>
    <updated>2026-11-16T12:00:00Z</updated>
  </entry>
</feed>"""


def test_parse_rss_com_html_e_data():
    items = parse_feed(RSS)

    assert len(items) == 2
    assert items[0].title == "PETR4 sobe com petroleo"
    assert items[0].summary == "Noticia & analise"
    assert items[0].published_at is not None
    assert items[1].published_at is None


def test_parse_atom_com_link_em_atributo():
    items = parse_feed(ATOM)

    assert len(items) == 1
    assert items[0].link == "https://example/3"
    assert items[0].summary == "Resumo do ETF"
    assert items[0].published_at is not None


def test_feed_invalido_levanta_erro():
    with pytest.raises(ValueError):
        parse_feed(b"isto nao e xml")
