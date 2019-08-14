"""
Brutally simplified version of https://github.com/karpathy/arxiv-sanity-preserver fetch_paper.py
Queries arxiv API and downloads papers to a new json file.
"""

import os
import time
import random
import argparse
import urllib.request
import feedparser
import json

def parse_arxiv_url(url):
  """ 
  examples is http://arxiv.org/abs/1512.08756v2
  we want to extract the raw id and the version
  """
  ix = url.rfind('/')
  idversion = url[ix+1:] # extract just the id (and the version)
  parts = idversion.split('v')
  assert len(parts) == 2, 'error parsing url ' + url
  return parts[0], int(parts[1])

if __name__ == "__main__":

  # parse input arguments
  parser = argparse.ArgumentParser()
  parser.add_argument('--search-query', type=str,
                      default='cat:math.SG+AND+au:eliashberg',
                      help='query used for arxiv API. See http://arxiv.org/help/api/user-manual#detailed_examples')
  parser.add_argument('--start-index', type=int, default=0, help='0 = most recent API result')
  parser.add_argument('--max-index', type=int, default=10000, help='upper bound on paper index we will fetch')
  parser.add_argument('--results-per-iteration', type=int, default=100, help='passed to arxiv API')
  parser.add_argument('--wait-time', type=float, default=5.0, help='lets be gentle to arxiv API (in number of seconds)')
  args = parser.parse_args()

  # filename with time, query
  timestr = time.strftime("%Y%m%d-%H%M%S")
  # replace problematic characters
  sq_goodname = "".join([ x if (x.isalnum() or x in "_-") else "_" for x in args.search_query])
  jsonfile = 'arxiv_' + sq_goodname + '_' + timestr + '.json'

  # misc hardcoded variables
  base_url = 'http://export.arxiv.org/api/query?' # base api query url
  print('Searching arXiv for {}'.format(args.search_query))

  # Create file
  try:
    jf = open(jsonfile, 'w+')
  except Exception as e:
    print('error creating json file %s:', jsonfile)
    print(e)

  # -----------------------------------------------------------------------------
  # main loop : parse and enrich 
  
  db = {}
  num_added_total = 0
  for i in range(args.start_index, args.max_index, args.results_per_iteration):

    print("Results {} - {}".format(i,i+args.results_per_iteration))
    query = 'search_query=%s&sortBy=lastUpdatedDate&start=%i&max_results=%i' % (args.search_query,
                                                         i, args.results_per_iteration)
    with urllib.request.urlopen(base_url+query) as url:
      response = url.read()
    parse = feedparser.parse(response)
    num_added = 0
    for e in parse.entries:

      # extract just the raw arxiv id and version for this paper
      rawid, version = parse_arxiv_url(e['id'])
      e['_rawid'] = rawid
      e['_version'] = version

      # add to our database
      db[rawid] = e
      print('Updated {} added {}'.format(e['updated'].encode('utf-8'), e['title'].encode('utf-8')))
      num_added += 1
      num_added_total += 1

    # print some information
    print('Added {} papers'.format(num_added))

    if len(parse.entries) == 0:
      print('Received no results from arxiv. Check query, or you may a a victim of rate limiting? Exiting.')
      print(response)
      break

    if num_added < args.results_per_iteration:
      print('I found only {} papers in the last batch, assuming that this is all. Exiting.'.format(num_added))
      break
    else:
      print('Sleeping for {} seconds'.format(args.wait_time))
      time.sleep(args.wait_time + random.uniform(0, 3))

  # save the database before we quit, if we found anything new
  if num_added_total > 0:
    print('Saving {} papers to {}'.format(len(db), jsonfile))
    json.dump(db, jf)
  jf.close()

