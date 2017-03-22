# arXiv_to_grAph

a project to visualize metadata from https://arxiv.org/. Just for the fun of it.

we can get xml data:

wget "http://export.arxiv.org/api/query?search_query=cat:math.SG+AND+au:eliashberg&max_results=80" -O eliashberg.xml

pip install https://github.com/hay/xml2json/zipball/master
