#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import HTMLParser
from lxml import html
import cssutils
from cssutils.css import CSSImportRule, CSSStyleRule
import re

class CssInclude(object):

    RE_QVGA_SIZE = re.compile(r'(width|height)(\s*:\s*|=)([\"\']*)(\d+)([\"\']*)(px|)', re.I)

    RE_XML_DECLARATION = re.compile(r'^<\?xml\s[^>]+?\?>\s*')

    RE_DOCTYPE = re.compile(r'^<\!DOCTYPE\s[^>]+?>\s*')

    RE_ESCAPE = re.compile(r'&(#\d+|amp|lt|gt|quot|apos|nbsp);')

    RE_UNESCAPE = re.compile(r'HTMLESCAPE(#\d+|amp|lt|gt|quot|apos|nbsp)::::::::')

    def __init__(self, base_dir='./', agent=None, is_vga=False):
        self.base_dir = base_dir
        self.agent = agent
        self.is_vga = is_vga

    def setBaseDir(self, dir):
        self.base_dir = dir

    def setVga(self):
        self.is_vga = True

    def setAgentDocomo(self):
        self.agent = 'docomo'

    def setAgentSoftBank(self):
        self.agent = 'softbank'

    def setAgentSoftBankVga(self):
        self.agent = 'softbank'
        self.is_vga = True

    def setAgentAu(self):
        self.agent = 'au'


    def apply(self, document):
        """
        document をインライン化する
        """

        # XML宣言が消えてしまうので一時退避
        declaration = ''
        m = self.RE_XML_DECLARATION.match(document)
        if m:
            declaration = m.group(0)
            document = document[len(declaration):]

        # doctypeも消えてしまうので一時退避
        doctype = ''
        m = self.RE_DOCTYPE.match(document)
        if m:
            doctype = m.group(0)
            document = document[len(doctype):]

        # 文字列参照エスケープを一時退避
        document = self.RE_ESCAPE.sub(r'HTMLESCAPE\1::::::::', document)

        if isinstance(document,str):
            document = unicode(document,'utf-8','ignore')
        
        self.dom_xpath = html.fromstring(document)

        css_rules = self._loadCSS()

        add_style = []

        for selectorText, styles in css_rules.iteritems():
            if selectorText.find(':') != -1:
                add_style += [ selectorText + '{' + style.name + ':' + style.value + ';}' for style in styles]
                continue

            nodes = self.dom_xpath.cssselect(selectorText)
            for node in nodes:
                for style in styles:
                    style_text = self._changeCss(node.tag, style)

                    if 'style' in node.attrib:
                        if node.attrib['style'][-1] != ';':
                            node.attrib['style'] += ';'
                        node.attrib['style'] += style_text
                    else:
                        node.attrib['style'] = style_text

        for node in self.dom_xpath.xpath('//*'):
            if 'class' in node.attrib:
                del node.attrib['class']

        # 擬似クラスの追加
        if add_style:
            new_style = '\n'.join(add_style)
            new_style = '<style type="text/css">\n' + new_style + '\n</style>'

            head = self.dom_xpath.xpath('//head')
            head[0].addnext(html.fromstring(new_style))

        result = HTMLParser.HTMLParser().unescape(html.tostring(self.dom_xpath, encoding='utf-8'))
        
        # 一時退避させたものを復元
        result = self.RE_UNESCAPE.sub(r'&\1;', result)
        if doctype:
            result = doctype + result
        if declaration:
            result = declaration + result

        if self.agent and self.is_vga:
            result = self.RE_QVGA_SIZE.sub(self._qvga_width_double, result)

        return result


    def _qvga_width_double(self, m):
        """
        qvgaはwidthとheightを２倍にする
        """
        width = int(m.group(4))
        return '%s%s%s%s%s%s' % (m.group(1), m.group(2), m.group(3), width * 2, m.group(5), m.group(6))


    def _loadCSS(self):
        """
        htmlにあるCSSと追加CSSを読み込む
        """
        nodes = self.dom_xpath.xpath(r'//link[@rel="stylesheet" or @type="text/css"] | //style[@type="text/css"]')
        css_rules = {}
        for node in nodes:
            # link だった場合はファイル読み込み
            if node.tag == 'link' and 'href' in node.attrib:
                if not os.path.exists(self.base_dir + node.attrib['href']):
                        continue
                css_string = open(self.base_dir + node.attrib['href']).read()

            # style の場合はそのまま読み込む
            elif node.tag == 'style':
                css_string = node.text

            _css_rules = self._loadCSSRule(css_string)
            self._updateDict(css_rules, _css_rules)

            # 読み込んだら html から削除
            p = node.getparent()
            if p is not None:
                p.remove(node)

        return css_rules


    def _loadCSSRule(self, css_string):
        sheet = cssutils.parseString(css_string)
        css_rules = {}
        for rule in sheet:
            # importの場合はファイルを読み込む
            if isinstance(rule, CSSImportRule):
                if os.path.exists(self.base_dir + rule.href):
                    _css_rules = self._loadCSSRule(open(self.base_dir + rule.href).read())
                    self._updateDict(css_rules, _css_rules)

            # styleの場合は適応するstyleのリストに追加
            elif isinstance(rule, CSSStyleRule):
                for selector in rule.selectorList:
                    style = css_rules.get(selector.selectorText, [])
                    style += rule.style
                    css_rules[selector.selectorText] = style

        return css_rules


    def _updateDict(self, parent, child):
        for k, v in child.iteritems():
            tmp = parent.get(k, [])
            tmp += v
            parent[k] = tmp


    def _changeCss(self, tag, style):
        """
        キャリア対応 css 書き換え
        """
        if not self.agent:
            return style.name + ':' + style.value + ';'

        if tag == 'hr' and self.agent in ('docomo', 'softbank'):
            if style.name == 'text-align':
                style.name = 'float'
            elif style.name == 'color':
                style.name = 'border-color'

        elif tag == 'img' and self.agent in ('docomo', 'softbank'):
            if style.name == 'text-align':
                style.name = 'float'
                if style.value == 'center':
                    style.value = 'none'

        else:
            if style.name == 'font-size':
                if style.value == '10px':
                    if self.agent in ('docomo', 'ezweb'):
                        style.value = 'xx-small'
                    elif self.agent == 'softbank':
                        if not self.is_vga:
                            style.value = 'x-small'
                        else:
                            style.value = 'medium'
                elif style.value == '16px':
                    if self.agent == 'softbank' and self.is_vga:
                        style.value = 'large'
                    else:
                        style.value = 'medium'

        return style.name + ':' + style.value + ';'


if __name__ == '__main__':
    sample_html = open('testdata/sample.html').read()
    css_include = CssInclude(agent='docomo', is_vga=True)
    output_html = css_include.apply(sample_html)

    print output_html


