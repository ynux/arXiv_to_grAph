# arXiv_to_grAph

a project to visualize metadata from https://arxiv.org/. Just for the fun of it.

we can get xml data:

wget "http://export.arxiv.org/api/query?search_query=cat:math.SG+AND+au:eliashberg&max_results=80" -O eliashberg.xml

pip install https://github.com/hay/xml2json/zipball/master

2.5 years later, another attempt.

There are interesting projects out there by now, like:

https://github.com/ranihorev/arxiv-network-graph

http://www.arxiv-sanity.com/

ipython: http://betatim.github.io/posts/analysing-the-arxiv/

unclear if interesting:

https://github.com/eitanrich/arxiv-hot-topics

https://www.kaggle.com/neelshah18/arxivdataset

	
on a Mac with default python 2, do:

```
pip3 install virtualenv
virtualenv -p python3 env
source env/bin/activate
python3 
```

This will create one big (to giant, depending on your query) json document. To have one json line = one paper, do e.g. 
```
cat arxiv_cat_math_SG_AND_au_eliashberg_20190814-172937.json | jq -c '.[]'  > arxiv_cat_math_SG_AND_au_eliashberg_20190814-172937_lines.json
```
From here, pump it into elasticsearch, or spark, or whatever your choice of json store might be.


