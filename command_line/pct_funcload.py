import argparse
import os
import csv

from corpustools.corpus.io import load_binary
from corpustools.funcload.functional_load import *

#### Script-specific functions

def check_bool(string):
    if string == 'False':
        return False
    else:
        return True

def read_segment_or_pairs(spfile):
    return spfile.read().strip()


def main():

    #### Parse command-line arguments
    parser = argparse.ArgumentParser(description = \
             'Phonological CorpusTools: functional load CL interface')
    parser.add_argument('corpus_file_name', help='Name of corpus file')
    parser.add_argument('pairs_file_name_or_segment', help='Name of file with segment pairs (or target segment if relative_fl is True)')
    parser.add_argument('-a', '--algorithm', default='minpair', help='Algorithm to use for calculating functional load: "minpair" for minimal pair count or "deltah" for change in entropy. Defaults to minpair.')
    parser.add_argument('-f', '--frequency_cutoff', type=float, default=0, help='Minimum frequency of words to consider as possible minimal pairs or contributing to lexicon entropy.')
    parser.add_argument('-r', '--relative_count', type=check_bool, default=True, help='For minimal pair FL: whether or not to divide the number of minimal pairs by the number of possible minimal pairs (words with either segment).')
    parser.add_argument('-d', '--distinguish_homophones', type=check_bool, default=False, help="For minimal pair FL: if False, then you'll count sock~shock (sock=clothing) and sock~shock (sock=punch) as just one minimal pair; but if True, you'll overcount alternative spellings of the same word, e.g. axel~actual and axle~actual. False is the value used by Wedel et al.")
    parser.add_argument('-t', '--type_or_token', default='token', help='For change in entropy FL: specifies whether entropy is based on type or token frequency.')
    parser.add_argument('-e', '--relative_fl', type=check_bool, default=False, help="If True, instead of reading the ")
    parser.add_argument('-o', '--outfile', help='Name of output file')

    args = parser.parse_args()

    ####

    corpus = load_binary(args.corpus_file_name)[0]

    if args.relative_fl != True:
        try:
            with open(args.pairs_file_name_or_segment) as segpairs_or_segment_file:
                segpairs_or_segment = [line for line in csv.reader(segpairs_or_segment_file, delimiter='\t') if len(line) > 0]
        except FileNotFoundError:
            raise FileNotFoundError("Did not find the segment pairs file even though 'relative_fl' is set to false. If calculating the relative FL of a single segement, please set 'relative_fl' to True. Otherwise, specify correct filename.")
    else:
        segpairs_or_segment = args.pairs_file_name_or_segment

    if args.algorithm == 'minpair':
        result = minpair_fl(corpus, segpairs_or_segment, frequency_cutoff=args.frequency_cutoff, relative_count=bool(args.relative_count), distinguish_homophones=args.distinguish_homophones)
    elif args.algorithm == 'deltah':
        result = deltah_fl(corpus, segpairs_or_segment, frequency_cutoff=args.frequency_cutoff, type_or_token=args.type_or_token)
    else:
        raise Exception('-a / --algorithm must be set to either \'minpair\' or \'deltah\'.')

    if args.outfile:
        with open(args.outfile, 'w') as outfile:
            outfile.write(str(result)) # TODO: develop output file structure
    else:
        print('No output file name provided.')
        print('The functional load of the given inputs is {}.'.format(str(result)))


if __name__ == '__main__':
    main()