import argparse
import os
import csv

from corpustools.corpus.classes import Word
from corpustools.corpus.io.binary import load_binary
from corpustools.neighdens.neighborhood_density import neighborhood_density
from corpustools.neighdens.neighborhood_density import find_mutation_minpairs


def ensure_query_is_word(query, corpus, sequence_type, trans_delimiter):
    if isinstance(query, Word):
        query_word = query
    else:
        try:
            query_word = corpus.find(query)
        except KeyError:
            if trans_delimiter == '':
                query_word = Word(**{sequence_type: list(query)})
            else:
                query_word = Word(**{sequence_type: query.split(trans_delimiter)})
    return query_word


def main():

    #### Parse command-line arguments
    parser = argparse.ArgumentParser(description = \
             'Phonological CorpusTools: neighborhood density CL interface')
    parser.add_argument('corpus_file_name', help='Name of corpus file')
    parser.add_argument('query', help='Word to query, or name of file including a list of words')
    parser.add_argument('-a', '--algorithm', default= 'edit_distance', help="The algorithm used to determine distance")
    parser.add_argument('-d', '--max_distance', type=int, default = 1, help="Maximum edit distance from the queried word to consider a word a neighbor.")
    parser.add_argument('-s', '--sequence_type', default = 'transcription', help="The name of the tier on which to calculate distance")
    parser.add_argument('-w', '--count_what', default ='type', help="If 'type', count neighbors in terms of their type frequency. If 'token', count neighbors in terms of their token frequency.")
    parser.add_argument('-e', '--trans_delimiter', default='', help="If not empty string, splits the query by this str to make a transcription/spelling list for the query's Word object.")
    parser.add_argument('-m', '--find_mutation_minpairs', action='store_true', help='This flag causes the script not to calculate neighborhood density, but rather to find minimal pairs---see documentation.')
    parser.add_argument('-o', '--outfile', help='Name of output file')

    args = parser.parse_args()

    ####

    corpus = load_binary(args.corpus_file_name)[0]

    if args.find_mutation_minpairs:
        query = ensure_query_is_word(args.query, corpus, args.sequence_type, args.trans_delimiter)
        matches = find_mutation_minpairs(corpus, query, sequence_type=args.sequence_type)
        for match in matches[1]:
            print(match)
        print('Total number of matches: {}'.format(str(matches[0])))
    else:
        try: # read query as a file name
            with open(args.query) as queryfile:
                queries = [line[0] for line in csv.reader(queryfile, delimiter='\t') if len(line) > 0]

                queries = [ensure_query_is_word(q, corpus, args.sequence_type, args.trans_delimiter) for q in queries]
            results = [neighborhood_density(corpus, q, algorithm = args.algorithm, max_distance = args.max_distance, sequence_type = args.sequence_type, count_what=args.count_what) for q in queries]
            if args.outfile:
                with open(args.outfile, 'w') as outfile:
                    for q, r in zip(queries, results):
                        outfile.write('{}\t{}'.format(q, str(r[0])) + ''.join(['\t{}'.format(str(n)) for n in r[1]]) + '\n')
            else:
                raise Exception('In order to use a file of queries as input, you must provide an output file name using the option -o.')


        except FileNotFoundError: # read query as a single word
            query = ensure_query_is_word(args.query, corpus, args.sequence_type, args.trans_delimiter)
            result = neighborhood_density(corpus, query, algorithm = args.algorithm, max_distance = args.max_distance, sequence_type = args.sequence_type, count_what=args.count_what)

            if args.outfile:
                with open(args.outfile, 'w') as outfile:
                    outfile.write('{}\t{}'.format(query, str(result[0])) + ''.join(['\t{}'.format(str(n)) for n in result[1]]))
            else:
                print('No output file name provided.')
                print('The neighborhood density of the given form is {}. For a list of neighbors, please provide an output file name.'.format(str(result[0])))


if __name__ == '__main__':
    main()
