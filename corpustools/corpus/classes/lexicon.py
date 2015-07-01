
import re
import random
import collections
import operator
import math
import locale

from corpustools.exceptions import CorpusIntegrityError

class Segment(object):
    """
    Class for segment symbols
    """

    def __init__(self, symbol):
        #None defaults are for word-boundary symbols
        self.symbol = symbol
        self.features = {}

    def specify(self, feature_dict):
        self.features = {k.lower(): v for k,v in feature_dict.items()}

    def minimal_difference(self, other, features):
        for k, v in self.features.items():
            if k in features:
                continue
            if v != other[k]:
                return False
        return True

    def feature_match(self, specification):
        """
        Return true if segment matches specification, false otherwise.
        Specification can be a single feature value '+feature' or a list of
        feature values ['+feature1','-feature2']
        """
        if isinstance(specification,str):
            try:
                if self[specification[1:]]!=specification[0]:
                    return False
            except KeyError:
                return False
        elif isinstance(specification,list):
            for f in specification:
                try:
                    if self[f[1:]]!=f[0]:
                        return False
                except KeyError:
                    return False
        elif isinstance(specification, dict):
            for f,v in specification.items():
                try:
                    if self[f] != v:
                        return False
                except KeyError:
                    return False
        return True

    def __contains__(self, item):
        return item.lower() in self.features

    def __getitem__(self, key):
        return self.features[key.lower()]

    def __setitem__(self, key, value):
        self.features[key.lower()] = value

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.symbol

    def __eq__(self, other):
        """Two segments are considered equal if their symbol attributes match

        """
        if isinstance(other, Segment):
            return self.symbol == other.symbol
        else:
            return self.symbol == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self,other):
        if isinstance(other, Segment):
            return self.symbol < other.symbol
        else:
            return self.symbol < other

    def __le__(self,other):
        return (self.symbol == other.symbol or self.symbol < other.symbol)

    def __ge__(self,other):
        return (self.symbol == other.symbol or self.symbol > other.symbol)

    def __gt__(self,other):
        if isinstance(other, Segment):
            return self.symbol > other.symbol
        else:
            return self.symbol > other

    def __len__(self):
        return len(self.symbol)

class Transcription(object):
    """
    Transcription object, sequence of symbols
    """
    def __init__(self,seg_list):
        self._list = []
        #self._times = []
        self.stress_pattern = {}
        self.boundaries = {}
        cur_group = 0
        cur_tone = None
        if seg_list is not None:
            for i,s in enumerate(seg_list):
                try:
                    self._list.append(s.label)
                    #if s.begin is not None and s.end is not None:
                    #    self._times.append((s.begin,s.end))
                    if s.stress is not None:
                        self.stress_pattern[i] = s.stress
                    if s.tone is not None:
                        if 'tone' not in self.boundaries:
                            self.boundaries['tone'] = {}
                        if s.tone != cur_tone:
                            self.boundaries['tone'][i] = s.tone
                            cur_tone = s.tone
                    if s.group is not None:
                        if 'morpheme' not in self.boundaries:
                            self.boundaries['morpheme'] = []
                        if s.group != cur_group:
                            self.boundaries['morpheme'].append(i)
                            cur_group = s.group
                except AttributeError:
                    if isinstance(s,str):
                        self._list.append(s)
                    elif isinstance(s,dict):
                        try:
                            symbol = s['label']
                        except KeyError:
                            symbol = s['symbol']
                        self._list.append(symbol)
                        #if 'begin' in s and 'end' in s:
                        #    self._times.append((s['begin'],s['end']))
                    elif isinstance(s,list):
                        if len(s) == 3:
                            self._list.append(s[0])
                            #self._times.append((s[1],s[2]))
                        else:
                            raise(NotImplementedError('That format for seg_list is not supported.'))
                    else:
                        raise(NotImplementedError('That format for seg_list is not supported.'))

    def with_word_boundaries(self):
        return ['#'] + self._list + ['#']

    def find_nonmatch(self, environment):
        if not isinstance(environment, EnvironmentFilter):
            return None
        if all(m not in self for m in environment.middle):
            return None
        num_segs = len(environment)

        possibles = zip(*[self.with_word_boundaries()[i:]
                                for i in range(num_segs)])
        envs = []
        lhs_num = environment.lhs_count()
        middle_num = lhs_num
        rhs_num = middle_num + 1
        for i, p in enumerate(possibles):
            if p not in environment and p[middle_num] in environment.middle:
                lhs = p[:lhs_num]
                middle = p[middle_num]
                rhs = p[rhs_num:]
                envs.append(Environment(middle, i + middle_num, lhs, rhs))
        if not envs:
            return None
        return envs

    def find(self, environment):
        if not isinstance(environment, EnvironmentFilter):
            return None
        if all(m not in self for m in environment._middle):
            return None
        num_segs = len(environment)

        possibles = zip(*[self.with_word_boundaries()[i:]
                                for i in range(num_segs)])
        lhs_num = environment.lhs_count()
        middle_num = lhs_num
        rhs_num = middle_num + 1
        envs = []
        for i, p in enumerate(possibles):
            if p in environment:
                lhs = p[:lhs_num]
                middle = p[middle_num]
                rhs = p[rhs_num:]
                envs.append(Environment(middle, i + middle_num, lhs, rhs))
        if not envs:
            return None
        return envs


    def __contains__(self, other):
        if isinstance(other, Segment):
            if other.symbol in self._list:
                return True
        elif isinstance(other, str):
            if other in self._list:
                return True
        return False

    def __setstate__(self, state):
        if 'stress_pattern' not in state:
            state['stress_pattern'] = {}
        if 'boundaries' not in state:
            state['boundaries'] = {}
        self.__dict__.update(state)

    def __hash__(self):
        return hash(str(self))

    def __getitem__(self, key):
        if isinstance(key,int) or isinstance(key,slice):
            return self._list[key]
        raise(KeyError)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        temp_list = []
        for i,s in enumerate(self._list):
            if self.stress_pattern and i in self.stress_pattern:
                s += self.stress_pattern[i]
            if 'tone' in self.boundaries and i in self.boundaries['tone']:
                s += self.boundaries['tone'][i]
            temp_list.append(s)
        if 'morpheme' in self.boundaries:
            beg = 0
            bound_list = []
            for i in self.boundaries['morpheme']:
                bound_list.append('.'.join(temp_list[beg:i]))
            bound_list.append('.'.join(temp_list[i:]))
            return '-'.join(bound_list)
        else:
            return '.'.join(temp_list)

    def __iter__(self):
        for s in self._list:
            yield s

    def __add__(self, other):
        """
        Allow for Transcriptions to be added to get all the segments in each
        """
        if not isinstance(other,Transcription):
            raise(TypeError)
        return self._list + other._list

    def __eq__(self, other):
        if isinstance(other,list):
            if len(other) != len(self):
                return False
            for i,s  in enumerate(self):
                if s != other[i]:
                    return False
            return True
        if not isinstance(other, Transcription):
            return False
        if self._list != other._list:
            return False
        if self.stress_pattern != other.stress_pattern:
            return False
        if self.boundaries != other.boundaries:
            return False
        return True

    def __lt__(self,other):
        if isinstance(other, Transcription):
            return self._list < other._list
        else:
            return self._list < other

    def __le__(self,other):
        if isinstance(other, Transcription):
            return (self._list == other._list or self._list < other._list)
        else:
            return self._list <= other

    def __ge__(self,other):
        if isinstance(other, Transcription):
            return (self._list == other._list or self._list > other._list)
        else:
            return self._list >= other

    def __gt__(self,other):
        if isinstance(other, Transcription):
            return self._list > other._list
        else:
            return self._list > other

    def match_segments(self, segments):
        """
        Returns a matching segments from a list of segments
        """
        match = []
        for s in self:
            if s in segments:
                match.append(s)
        return match

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self._list)

class FeatureMatrix(object):
    """
    An object that stores feature values for segments


    Attributes
    ----------
    name : str
        An informative identifier for the feature matrix

    feature : list of Dictionary
        Dictionaries in the list should contain feature names as keys
        and feature values as values, as well as a special key-value pair
        for the symbol

    """

    def __init__(self, name,feature_entries):
        self.name = name
        self._features = None
        self.possible_values = set()
        self.matrix = {}
        self._default_value = 'n'
        for s in feature_entries:
            if self._features is None:
                self._features = {k for k in s.keys() if k != 'symbol'}
            self.matrix[s['symbol']] = Segment(s['symbol'])
            self.matrix[s['symbol']].specify({k:v for k,v in s.items() if k != 'symbol'})
            self.possible_values.update({v for k,v in s.items() if k != 'symbol'})

        #What are these?
        self.matrix['#'] = Segment('#')
        self.places = collections.OrderedDict()
        self.manners = collections.OrderedDict()
        self.backness = collections.OrderedDict()
        self.height = collections.OrderedDict()
        self.generate_generic_names()

    def generate_generic_names(self):
        if 'consonantal' in self.features:
            self.generate_generic_hayes()
            self.vowel_feature = '+syllabic'
            self.voice_feature = '+voice'
            self.diph_feature = '+diphthong'
            self.rounded_feature = '+round'
        elif 'voc' in self.features:
            self.generate_generic_spe()
            self.vowel_feature = '+voc'
            self.voice_feature = '+voice'
            self.diph_feature = '.high'
            self.rounded_feature = '+round'
        else:
            self.generate_generic()
            self.vowel_feature = []
            self.voice_feature = []
            self.diph_feature = []
            self.rounded_feature = []

    def generate_generic(self):
        self.places['Labial'] = {}
        self.places['Labiodental'] =  {}
        self.places['Dental'] = {}
        self.places['Alveolar'] = {}
        self.places['Alveopalatal'] = {}
        self.places['Palatal'] = {}
        self.places['Velar'] = {}
        self.places['Uvular'] = {}
        self.places['Pharyngeal'] = {}
        self.places['Glottal'] = {}

        self.manners['Stop'] = {}
        self.manners['Nasal'] = {}
        self.manners['Trill'] = {}
        self.manners['Tap'] = {}
        self.manners['Fricative'] = {}
        self.manners['Affricate'] = {}
        self.manners['Approximant'] = {}
        self.manners['Lateral approximant'] = {}

        self.backness['Front'] = {}
        self.backness['Near front'] = {}
        self.backness['Central'] = {}
        self.backness['Near back'] = {}
        self.backness['Back'] = {}

        self.height['Close'] = {}
        self.height['Near close'] = {}
        self.height['Close mid'] = {}
        self.height['Open mid'] = {}
        self.height['Open'] = {}

    def generate_generic_spe(self):
        self.places['Labial'] = {'ant':'+', 'back': '-', 'cor':'-'}
        self.places['Labiodental'] =  {'ant':'+', 'back': '-', 'cor':'-'}
        self.places['Dental'] = {'ant':'+', 'back': '-', 'cor':'+'}
        self.places['Alveolar'] = {'ant':'-', 'back': '-', 'cor':'+', 'high': '-'}
        self.places['Alveopalatal'] = {'ant':'-', 'back': '-', 'cor':'+', 'high': '+'}
        self.places['Palatal'] = {'ant':'-', 'back': '-', 'cor':'-'}
        self.places['Velar'] = {'ant':'-', 'back': '+', 'cor':'-', 'high': '+'}
        self.places['Uvular'] = {'ant':'-', 'back': '+', 'cor':'-', 'high': '-'}
        self.places['Pharyngeal'] = {'low':'+', 'back': '+'}
        self.places['Glottal'] = {'low':'+', 'back': '-'}

        self.manners['Stop'] = {'son': '-','cont':'-','nasal':'-'}
        self.manners['Nasal'] = {'nasal': '+'}
        self.manners['Trill'] = {}
        self.manners['Tap'] = {}
        self.manners['Fricative'] = {'son': '-','cont':'+','nasal':'-'}
        self.manners['Affricate'] = {'del_rel':'+'}
        self.manners['Approximant'] = {'son':'+', 'nasal': '-', 'lat':'-'}
        self.manners['Lateral approximant'] = {'son':'+', 'nasal': '-', 'lat':'+'}

        self.backness['Front'] = {'back':'-', 'tense':'+'}
        self.backness['Near front'] = {'back': '-', 'tense': '-'}
        self.backness['Central'] = {'back': 'n'}
        self.backness['Near back'] = {'back': '+', 'tense':'-'}
        self.backness['Back'] = {'back':'+', 'tense':'+'}

        self.height['Close'] = {'high':'+', 'low':'-', 'tense':'+'}
        self.height['Near close'] = {'high':'+', 'low':'-', 'tense':'-'}
        self.height['Close mid'] = {'high':'-', 'low':'-', 'tense':'+'}
        self.height['Open mid'] = {'high':'-', 'low':'-', 'tense':'-'}
        self.height['Open'] = {'high':'-', 'low':'+'}

    def generate_generic_hayes(self):
        self.places['Labial'] = {'labial': '+', 'coronal':'-'}
        self.places['Labiodental'] = {'labiodental': '+',}
        self.places['Dental'] = {'anterior': '+', 'coronal':'+', 'labial':'-'}
        self.places['Alveolar'] = {}
        self.places['Alveopalatal'] = {'anterior': '-', 'coronal':'+', 'labial':'-'}
        self.places['Palatal'] = {'dorsal': '+', 'coronal':'+', 'labial':'-'}
        self.places['Velar'] = {'dorsal': '+', 'labial':'-'}
        self.places['Uvular'] = {'dorsal': '+', 'back':'+', 'labial':'-'}
        self.places['Pharyngeal'] = {}
        self.places['Glottal'] = {'dorsal': '-', 'coronal':'-', 'labial':'-', 'nasal': '-'}

        self.manners['Stop'] = {'sonorant': '-','continuant':'-','nasal':'-','delayed_release':'-'}
        self.manners['Nasal'] = {'nasal': '+'}
        self.manners['Trill'] = {'trill': '+'}
        self.manners['Tap'] = {'tap': '+'}
        self.manners['Fricative'] = {'sonorant': '-','continuant':'+'}
        self.manners['Affricate'] = {'sonorant': '-', 'continuant':'-','delayed_release':'+'}
        self.manners['Approximant'] = {'sonorant': '+', 'lateral':'-'}
        self.manners['Lateral approximant'] = {'sonorant': '+', 'lateral':'+'}

        self.backness['Front'] = {'front': '+', 'back':'-', 'tense':'+'}
        self.backness['Near front'] = {'front': '+', 'back': '-', 'tense': '-'}
        self.backness['Central'] = {'front': '-', 'back': '-'}
        self.backness['Near back'] = {'front': '-', 'back': '-', 'tense':'-'}
        self.backness['Back'] = {'front':'-', 'back':'+', 'tense':'+'}

        self.height['Close'] = {'high':'+', 'low':'-', 'tense':'+'}
        self.height['Near close'] = {'high':'+', 'low':'-', 'tense':'-'}
        self.height['Close mid'] = {'high':'-', 'low':'-', 'tense':'+'}
        self.height['Open mid'] = {'high':'-', 'low':'-', 'tense':'-'}
        self.height['Open'] = {'high':'-', 'low':'+'}

    def __eq__(self, other):
        if not isinstance(other,FeatureMatrix):
            return False
        if self.matrix == other.matrix:
            return True
        return False

    def features_to_segments(self, feature_description):
        """
        Given a feature description, return the segments in the inventory
        that match that feature description

        Feature descriptions should be either lists, such as
        ['+feature1', '-feature2'] or strings that can be separated into
        lists by ',', such as '+feature1,-feature2'.

        Parameters
        ----------
        feature_description : string or list
            Feature values that specify the segments, see above for format

        Returns
        -------
        list of Segments
            Segments that match the feature description

        """
        segments = []
        if isinstance(feature_description, str):
            feature_description = feature_description.split(',')
        for k,v in self.matrix.items():
            if v.feature_match(feature_description):
                segments.append(k)
        return segments

    def __setstate__(self,state):
        if '_features' not in state:
            state['_features'] = state['features']
        for k,v in state['matrix'].items():
            if not isinstance(v,Segment):
                s = Segment(k)
                s.specify(v)
                state['matrix'][k] = s
            else:
                v.specify(v.features)
        self.__dict__.update(state)

        #Backwards compatability
        if '_default_value' not in state:
            self._default_value = 'n'
        if 'places' not in state:
            self.places = collections.OrderedDict()
            self.manners = collections.OrderedDict()
            self.backness = collections.OrderedDict()
            self.height = collections.OrderedDict()
            self.generate_generic_names()

    def __iter__(self):
        for k in sorted(self.matrix.keys()):
            yield self.matrix[k]

    def validate(self):
        """
        Make sure that all segments in the matrix have all the features.
        If not, add an unspecified value for that feature to them.
        """
        for k,v in self.matrix.items():
            for f in self._features:
                if f not in v:
                    self.matrix[k][f] = self._default_value

    @property
    def default_value(self):
        return self._default_value

    @property
    def features(self):
        """
        Get a list of features that are used in this feature system

        Returns
        -------
        list
            Sorted list of the names of all features in the matrix
        """
        return sorted(list(self._features))

    def add_segment(self,seg,feat_spec):
        """
        Add a segment with a feature specification to the feature system

        Attributes
        ----------
        seg : str
            Segment symbol to add to the feature system

        feat_spec : dictionary
            Dictionary with features as keys and feature values as values

        """

        #Validation
        for f in feat_spec.keys():
            if f not in self._features:
                raise(AttributeError('The segment \'%s\' has a feature \'%s\' that is not defined for this feature matrix' %(seg,f)))
        s = Segment(seg)
        s.specify(feat_spec)
        self.matrix[seg] = s

    def add_feature(self,feature, default = None):
        """
        Add a feature to the feature system

        Attributes
        ----------
        feature : str
            Name of the feature to add to the feature system

        """

        self._features.update({feature})
        if default is None:
            self.validate()
        else:
            for k,v in self.matrix.items():
                for f in self._features:
                    if f not in v:
                        self.matrix[k][f] = default


    def valid_feature_strings(self):
        strings = []
        for v in self.possible_values:
            for f in self.features:
                strings.append(v+f)
        return strings

    def categorize(self, seg):
        if seg == '#':
            return None
        seg_features = seg.features
        if seg.feature_match(self.vowel_feature):
            category = ['Vowel']

            if seg.feature_match(self.diph_feature):
                category.insert(0,'Diphthong')
                return category

            for k,v in self.height.items():
                if seg.feature_match(v):
                    category.append(k)
                    break
            else:
                category.append(None)
            for k,v in self.backness.items():
                if seg.feature_match(v):
                    category.append(k)
                    break
            else:
                category.append(None)

            if seg.feature_match(self.rounded_feature):
                category.append('Rounded')
            else:
                category.append('Unrounded')
        else:
            category = ['Consonant']

            for k,v in self.places.items():
                if seg.feature_match(v):
                    category.append(k)
                    break
            else:
                category.append(None)

            for k,v in self.manners.items():
                if seg.feature_match(v):
                    category.append(k)
                    break
            else:
                category.append(None)

            if seg.feature_match(self.voice_feature):
                category.append('Voiced')
            else:
                category.append('Voiceless')
        return category
    @property
    def segments(self):
        """
        Return a list of segment symbols that are specified in the feature
        system

        Returns
        -------
        list
            List of all the segments with feature specifications
        """
        return list(self.matrix.keys())

    def seg_to_feat_line(self,symbol):
        """
        Get a list of feature values for a given segment in the order
        that features are return in get_feature_list

        Use for display purposes

        Attributes
        ----------
        symbol : str
            Segment symbol to look up

        Returns
        -------
        list
            List of feature values for the symbol, as well as the symbol itself
        """
        featline = [symbol] + [ self.matrix[symbol][feat]
                            for feat in self.features]
        return featline

    def __getitem__(self,item):
        if isinstance(item,str):
            return self.matrix[item]
        elif isinstance(item,tuple):
            return self.matrix[item[0]][item[1]]

    def __delitem__(self,item):
        del self.matrix[item]

    def __contains__(self,item):
        return item in list(self.matrix.keys())

    def __setitem__(self,key,value):
        self.matrix[key] = value

    def __len__(self):
        return len(self.matrix)

class Word(object):
    """An object representing a word in a corpus

    A Corpus object creates Words from information in a user-supplied text file.
    The names of the attributes of a Word are therefore unpredictable.

    Attributes
    ----------
    spelling : str
        A representation of a word that lacks phonological information.

    transcription : list of Segments
        A representation of a word that includes phonological information.

    frequency : float
        Token frequency in a corpus


    """

    _freq_names = ['abs_freq', 'freq_per_mil','sfreq',
        'lowercase_freq', 'log10_freq']

    def __init__(self, **kwargs):

        _corpus = None

        self.transcription = None
        self.spelling = None
        self.frequency = 0
        self.wordtokens = list()
        self.descriptors = ['spelling','transcription', 'frequency']
        for key, value in kwargs.items():
            if isinstance(value, tuple):
                att, value = value
                if att.att_type == 'numeric':
                    try:
                        value = locale.atof(value)
                    except (ValueError, TypeError):
                        value = float('nan')
                elif att.att_type == 'tier':
                    value = Transcription(value)
            else:
                key = key.lower()
                if key in self._freq_names:
                    key = 'frequency'
                if isinstance(value,list):
                    #assume transcription type stuff
                    value = Transcription(value)
                elif key != 'spelling':
                    try:
                        f = float(value)
                        if not math.isnan(f) and not math.isinf(f):
                            value = f
                    except (ValueError, TypeError):
                        pass
                if key not in self.descriptors:
                    self.descriptors.append(key)
            setattr(self, key, value)
        if self.spelling is None and self.transcription is None:
            raise(ValueError('Words must be specified with at least a spelling or a transcription.'))
        if self.spelling is None:
            self.spelling = ''.join(map(str,self.transcription))

    def reverse(self):
        pass

    def __hash__(self):
        return hash((self.spelling,str(self.transcription)))

    def __getstate__(self):
        state = self.__dict__.copy()
        state['wordtokens'] = []
        state['_corpus'] = None
        #for k,v in state.items():
        #    if (k == 'transcription' or k in self.tiers) and v is not None:
        #        state[k] = [x.symbol for x in v] #Only store string symbols
        return state

    def __setstate__(self, state):
        self.transcription = []
        self.spelling = ''
        self.frequency = 0
        if 'wordtokens' not in state:
            state['wordtokens'] = []
        if 'descriptors' not in state:
            state['descriptors'] = ['spelling','transcription', 'frequency']
        if 'frequency' not in state['descriptors']:
            state['descriptors'].append('frequency')
        try:
            tiers = state.pop('tiers')
            for t in tiers:
                state['descriptors'].append(t)
        except KeyError:
            pass
        self.__dict__.update(state)

    def add_abstract_tier(self, tier_name, tier_segments):
        tier = []
        for s in self.transcription:
            for k,v in tier_segments.items():
                if s in v:
                    tier.append(k)
                    break
        setattr(self,tier_name,''.join(tier))

    def add_attribute(self, tier_name, default_value):
        setattr(self,tier_name, default_value)

    def add_tier(self, tier_name, tier_segments):
        """Adds a new tier attribute to a Word instance

        Parameters
        ----------
        tier_name : str
            User-supplied name for the new tier

        tier_features: list of str
            User-supplied list of phonological features values that define
            which segments are included in the tier

        """
        matching_segs = self.transcription.match_segments(tier_segments)
        new_tier = Transcription(matching_segs)
        setattr(self,tier_name,new_tier)
        for wt in self.wordtokens:
            matching_segs = wt.transcription.match_segments(tier_segments)
            new_tier = Transcription(matching_segs)
            setattr(wt,tier_name,new_tier)


    def remove_attribute(self, attribute_name):
        """Deletes a tier attribute from a Word

        Parameters
        ----------
        attribute_name : str
            Name of tier attribute to be deleted.

        Notes
        ----------
        If attribute_name is not a valid attribute, this function does nothing. It
        does not raise an error.

        """
        if attribute_name.startswith('_'):
            return
        try:
            delattr(self, attribute_name)
        except ValueError:
            pass #attribute_name does not exist

    def variants(self, sequence_type = 'transcription'):
        return collections.Counter(getattr(x,sequence_type) for x in self.wordtokens)

    def enumerate_symbols(self,tier_name):
        for pos,seg in enumerate(getattr(self, tier_name)):
            yield pos,seg

    def get_env(self,pos,tier_name):
        """Get details of a particular environment in a Word

        Parameters
        ----------
        pos : int
            A position in the word, so 0<=pos<=len(self)

        Returns
        ----------
        e : Environment
            Environment of the segment at the given position in the word

        """
        tier = getattr(self,tier_name)
        return tier.get_env(pos)

    def __repr__(self):
        return '<Word: \'%s\'>' % self.spelling

    def __str__(self):
        return self.spelling


    def __eq__(self, other):
        if not isinstance(other,Word):
            return False
        if self.spelling != other.spelling:
            return False
        if self.transcription != other.transcription:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.spelling < other.spelling

    def __gt__(self, other):
        return self.spelling > other.spelling

    def __le__(self, other):
        return self.spelling <= other.spelling

    def __ge__(self, other):
        return self.spelling >= other.spelling

class Environment(object):

    def __init__(self, middle, position, lhs = None, rhs = None):
        self.middle = middle
        self.position = position
        self.lhs = lhs
        self.rhs = rhs
        self.lhs_string = None
        self.rhs_string = None
        self.middle_string = None

    def __getitem__(self, key):
        if self.lhs is not None:
            if key < len(self.lhs):
                return self.lhs[key]
            elif key == len(self.lhs):
                return self.middle
            elif self.rhs is not None:
                return self.rhs[key - len(self.lhs) - 1]
            else:
                raise(KeyError('Index out of bounds'))
        else:
            if key == 0:
                return self.middle
            elif self.rhs is not None:
                return self.rhs[key - 1]
            else:
                raise(KeyError('Index out of bounds'))

    def __str__(self):
        elements = []
        if self.lhs_string is not None:
            elements.append(self.lhs_string)
        elif self.lhs is not None:
            elements.append(''.join(self.lhs))
        else:
             elements.append('')
        if self.rhs_string is not None:
            elements.append(self.rhs_string)
        elif self.rhs is not None:
            elements.append(''.join(self.rhs))
        else:
             elements.append('')
        return '_'.join(elements)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash((self.lhs, self.position, self.middle, self.rhs))

    def __eq__(self,other):
        """
        Two Environments are equal if they share a left AND right hand side
        An empty lhs or rhs is an automatic match
        """
        if not isinstance(other,Environment):
            return False

        if other.lhs and other.lhs != self.lhs:
            return False
        if other.rhs and other.rhs != self.rhs:
            return False
        if other.position != self.position:
            return False
        return True

    def __ne__(self,other):
        return not self.__eq__(other)

class EnvironmentFilter(object):
    """

    """
    def __init__(self, middle_segments, lhs = None, rhs = None):
        self.original_middle = middle_segments
        if lhs is not None:
            lhs = tuple(lhs)
        self.lhs = lhs
        if rhs is not None:
            rhs = tuple(rhs)
        self.rhs = rhs

        self.lhs_string = None
        self.rhs_string = None
        self.sanitize()

    @property
    def middle(self):
        return self.original_middle

    @middle.setter
    def middle(self, middle_segments):
        self.original_middle = middle_segments
        self.sanitize()

    def sanitize(self):
        if self.lhs is not None:
            new_lhs = []
            for seg_set in self.lhs:
                if not isinstance(seg_set,frozenset):
                    new_lhs.append(frozenset(seg_set))
                else:
                    new_lhs.append(seg_set)
            self.lhs = tuple(new_lhs)
        if self.rhs is not None:
            new_rhs = []
            for seg_set in self.rhs:
                if not isinstance(seg_set,frozenset):
                    new_rhs.append(frozenset(seg_set))
                else:
                    new_rhs.append(seg_set)
            self.rhs = tuple(new_rhs)
        if not isinstance(self.middle, frozenset):
            self.middle = frozenset(self.middle)
        self._middle = set()
        for m in self.middle:
            if isinstance(m, str):
                self._middle.add(m)
            elif isinstance(m, (list, tuple, set)):
                self._middle.update(m)

    def is_applicable(self, sequence):
        if len(sequence) < len(self):
            return False
        return True

    def compile_re_pattern(self):
        pass

    def lhs_count(self):
        if self.lhs is None:
            return 0
        return len(self.lhs)

    def rhs_count(self):
        if self.rhs is None:
            return 0
        return len(self.rhs)

    def set_lhs(self, lhs):
        self.lhs = lhs
        self.compile_re_pattern()

    def set_rhs(self, rhs):
        self.rhs = rhs
        self.compile_re_pattern()

    def __iter__(self):
        if self.lhs is not None:
            for s in self.lhs:
                yield s
        yield self._middle
        if self.rhs is not None:
            for s in self.rhs:
                yield s

    def __len__(self):
        length = 1
        if self.lhs is not None:
            length += len(self.lhs)
        if self.rhs is not None:
            length += len(self.rhs)
        return length

    def __str__(self):
        elements = []
        if self.lhs_string is not None:
            elements.append(self.lhs_string)
        elif self.lhs is not None:
            elements.append(''.join('{' + ','.join(x) + '}' for x in self.lhs))
        else:
             elements.append('')
        if self.rhs_string is not None:
            elements.append(self.rhs_string)
        elif self.rhs is not None:
            elements.append(''.join('{' + ','.join(x) + '}' for x in self.rhs))
        else:
             elements.append('')
        return '_'.join(elements)

    def __eq__(self, other):
        if not hasattr(other,'lhs'):
            return False
        if not hasattr(other,'rhs'):
            return False
        if self.lhs != other.lhs:
            return False
        if self.rhs != other.rhs:
            return False
        return True

    def __hash__(self):
        return hash((self.rhs, self.lhs))

    def __contains__(self, sequence):
        for i, s in enumerate(self):
            if sequence[i] not in s:
                return False
        return True

class Attribute(object):
    """
    Attributes are for collecting summary information about attributes of
    Words or WordTokens, with different types of attributes allowing for
    different behaviour

    Parameters
    ----------
    name : str
        Python-safe name for using `getattr` and `setattr` on Words and
        WordTokens

    att_type : str
        Either 'spelling', 'tier', 'numeric' or 'factor'

    display_name : str
        Human-readable name of the Attribute, defaults to None

    default_value : object
        Default value for initializing the attribute

    Attributes
    ----------
    name : string
        Python-readable name for the Attribute on Word and WordToken objects

    display_name : string
        Human-readable name for the Attribute

    default_value : object
        Default value for the Attribute.  The type of `default_value` is
        dependent on the attribute type.  Numeric Attributes have a float
        default value.  Factor and Spelling Attributes have a string
        default value.  Tier Attributes have a Transcription default value.

    range : object
        Range of the Attribute, type depends on the attribute type.  Numeric
        Attributes have a tuple of floats for the range for the minimum
        and maximum.  The range for Factor Attributes is a set of all
        factor levels.  The range for Tier Attributes is the set of segments
        in that tier across the corpus.  The range for Spelling Attributes
        is None.
    """
    ATT_TYPES = ['spelling', 'tier', 'numeric', 'factor']
    def __init__(self, name, att_type, display_name = None, default_value = None):
        self.name = name
        self.att_type = att_type
        self._display_name = display_name

        if self.att_type == 'numeric':
            self._range = [0,0]
            if default_value is not None and isinstance(default_value,(int,float)):
                self._default_value = default_value
            else:
                self._default_value = 0
        elif self.att_type == 'factor':
            if default_value is not None and isinstance(default_value,str):
                self._default_value = default_value
            else:
                self._default_value = ''
            if default_value:
                self._range = set([default_value])
            else:
                self._range = set()
        elif self.att_type == 'spelling':
            self._range = None
            if default_value is not None and isinstance(default_value,str):
                self._default_value = default_value
            else:
                self._default_value = ''
        elif self.att_type == 'tier':
            self._range = set()
            self._delim = None
            if default_value is not None and isinstance(default_value,Transcription):
                self._default_value = default_value
            else:
                self._default_value = Transcription(None)

    @property
    def delimiter(self):
        if self.att_type != 'tier':
            return None
        else:
            return self._delim

    @delimiter.setter
    def delimiter(self, value):
        self._delim = value

    @staticmethod
    def guess_type(values, trans_delimiters = None):
        if trans_delimiters is None:
            trans_delimiters = ['.',' ', ';', ',']
        probable_values = {x: 0 for x in Attribute.ATT_TYPES}
        for i,v in enumerate(values):
            try:
                t = float(v)
                probable_values['numeric'] += 1
                continue
            except ValueError:
                for d in trans_delimiters:
                    if d in v:
                        probable_values['tier'] += 1
                        break
                else:
                    if v in [v2 for j,v2 in enumerate(values) if i != j]:
                        probable_values['factor'] += 1
                    else:
                        probable_values['spelling'] += 1
        return max(probable_values.items(), key=operator.itemgetter(1))[0]

    @staticmethod
    def sanitize_name(name):
        """
        Sanitize a display name into a Python-readable attribute name

        Parameters
        ----------
        name : string
            Display name to sanitize

        Returns
        -------
        string
            Sanitized name
        """
        return re.sub('\W','',name.lower())

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return '<Attribute of type {} with name \'{}\'>'.format(self.att_type,self.name)

    def __str__(self):
        return self.display_name

    def __eq__(self,other):
        if isinstance(other,Attribute):
            if self.name == other.name:
                return True
        if isinstance(other,str):
            if self.name == other:
                return True
        return False

    @property
    def display_name(self):
        if self._display_name is not None:
            return self._display_name
        return self.name.title()

    @property
    def default_value(self):
        return self._default_value

    @default_value.setter
    def default_value(self, value):
        self._default_value = value
        self._range = set([value])

    @property
    def range(self):
        return self._range

    def update_range(self,value):
        """
        Update the range of the Attribute with the value specified.
        If the attribute is a Factor, the value is added to the set of levels.
        If the attribute is Numeric, the value expands the minimum and
        maximum values, if applicable.  If the attribute is a Tier, the
        value (a segment) is added to the set of segments allowed. If
        the attribute is Spelling, nothing is done.

        Parameters
        ----------
        value : object
            Value to update range with, the type depends on the attribute
            type
        """
        if value is None:
            return
        if self.att_type == 'numeric':
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    self.att_type = 'spelling'
                    self._range = None
                    return
            if value < self._range[0]:
                self._range[0] = value
            elif value > self._range[1]:
                self._range[1] = value
        elif self.att_type == 'factor':
            self._range.add(value)
            #if len(self._range) > 1000:
            #    self.att_type = 'spelling'
            #    self._range = None
        elif self.att_type == 'tier':
            if isinstance(self._range, list):
                self._range = set(self._range)
            self._range.update([x for x in value])

class Inventory(object):
    """
    Inventories contain information about a Corpus' segmental inventory.
    In many cases, they are similar to FeatureMatrices, but more tailored
    to a specific corpus.  Where a FeatureMatrix would deal in feature
    specifications, inventories will deal primarily in sets of segments.

    Parameters
    ----------

    data : dict, optional
        Mapping from segment symbol to Segment objects

    Attributes
    ----------
    features : list
        List of all features used as specifications for segments
    possible_values : set
        Set of values that segments use for features
    stresses : dict
        Mapping of stress values to segments that bear that stress
    places : dict
        Mapping from place of articulation labels to sets of segments
    manners : dict
        Mapping from manner of articulation labels to sets of segments
    height : dict
        Mapping from vowel height labels to sets of segments
    backness : dict
        Mapping from vowel backness labels to sets of segments
    vowel_feature : str
        Feature value (i.e., '+voc') that separates vowels from consonants
    voice_feature : str
        Feature value (i.e., '+voice') that codes voiced obstruents
    diph_feature : str
        Feature value (i.e., '+diphthong' or '.high') that separates
        diphthongs from monophthongs
    rounded_feature : str
        Feature value (i.e., '+round') that codes rounded vowels
    """
    def __init__(self, data = None):
        if data is None:
            self._data = {'#' : Segment('#')}
        else:
            self._data = data
        self.features = []
        self.possible_values = set()
        self.stresses = collections.defaultdict(set)
        self.places = collections.OrderedDict()
        self.manners = collections.OrderedDict()
        self.height = collections.OrderedDict()
        self.backness = collections.OrderedDict()
        self.vowel_feature = None
        self.voice_feature = None
        self.diph_feature = None
        self.rounded_feature = None

    def __setstate__(self, state):
        if 'stresses' not in state:
            state['stresses'] = {}
        self.__dict__.update(state)

    def __len__(self):
        return len(self._data.keys())

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __getitem__(self, key):
        if isinstance(key, slice):
            return sorted(self._data.keys())[key]
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __iter__(self):
        for k in sorted(self._data.keys()):
            yield self._data[k]

    def __contains__(self, item):
        if isinstance(item, str):
            return item in self._data.keys()
        elif isinstance(item, Segment):
            return item.symbol in self._data.keys()
        return False

    def valid_feature_strings(self):
        strings = []
        for v in self.possible_values:
            for f in self.features:
                strings.append(v+f)
        return strings

    def find_min_feature_pairs(self, features, others = None):
        plus_segs = []
        minus_segs = []
        output = collections.defaultdict(list)
        redundant = self.get_redundant_features(features, others)
        for seg in self:
            if any(seg[f] not in set('+-') for f in features):
                continue
            if not seg.feature_match(others):
                continue
            for seg2 in self:
                if seg == seg2:
                    continue
                if seg.minimal_difference(seg2, features + redundant):
                    break
            else:
                continue
            if seg not in output[tuple(seg[f] for f in features)]:
                output[tuple(seg[f] for f in features)].append(seg)
            if seg2 not in output[tuple(seg2[f] for f in features)]:
                output[tuple(seg2[f] for f in features)].append(seg2)
        return output

    def get_redundant_features(self, features, others = None):
        redundant_features = []
        if isinstance(features, str):
            features = [features]
        if others is None:
            others = []
        other_feature_names = [x[1:] for x in others]
        for f in self.features:
            if f in features:
                continue
            if f in other_feature_names:
                continue
            feature_values = collections.defaultdict(set)
            for seg in self:
                if others is not None:
                    if not seg.feature_match(others):
                        continue
                if seg == '#':
                    continue
                value = tuple(seg[x] for x in features)
                other_value = seg[f]
                feature_values[value].add(other_value)
                if any(len(x) > 1 for x in feature_values.values()):
                    break
            if any(len(x) > 1 for x in feature_values.values()):
                continue
            redundant_features.append(f)
        return redundant_features

    def features_to_segments(self, feature_description):
        """
        Given a feature description, return the segments in the inventory
        that match that feature description

        Feature descriptions should be either lists, such as
        ['+feature1', '-feature2'] or strings that can be separated into
        lists by ',', such as '+feature1,-feature2'.

        Parameters
        ----------
        feature_description : string or list
            Feature values that specify the segments, see above for format

        Returns
        -------
        list of Segments
            Segments that match the feature description

        """
        segments = []
        if isinstance(feature_description, str):
            feature_description = feature_description.split(',')
        for k,v in self._data.items():
            if v.feature_match(feature_description):
                segments.append(k)
        return segments

    def specify(self, specifier):
        if specifier is None:
            for k in self._data.keys():
                self._data[k].specify({})
            self.features = list()
            self.possible_values = set()
            self.cons_columns = collections.OrderedDict()
            self.cons_rows = collections.OrderedDict()
            self.vow_columns = collections.OrderedDict()
            self.vow_rows = collections.OrderedDict()
            self.voice_feature = None
            self.vowel_feature = None
            self.diph_feature = None
            self.rounded_feature = None
        else:
            for k in self._data.keys():
                try:
                    self._data[k].specify(specifier[k].features)
                except KeyError:
                    self._data[k].specify({})
            self.features = specifier.features
            self.possible_values = specifier.possible_values

            self.voice_feature = specifier.voice_feature
            self.vowel_feature = specifier.vowel_feature
            self.diph_feature = specifier.diph_feature
            self.rounded_feature = specifier.rounded_feature

            # Calculate which segments are in which dict
            # (pre calculate feature matches)

            self.places = collections.OrderedDict()
            for k,v in specifier.places.items():
                if len(v) == 0:
                    self.places[k] = set()
                else:
                    self.places[k] = set(self.features_to_segments(v))

            self.manners = collections.OrderedDict()
            for k,v in specifier.manners.items():
                if len(v) == 0:
                    self.manners[k] = set()
                else:
                    self.manners[k] = set(self.features_to_segments(v))

            self.height = collections.OrderedDict()
            for k,v in specifier.height.items():
                if len(v) == 0:
                    self.height[k] = set()
                else:
                    self.height[k] = set(self.features_to_segments(v))

            self.backness = collections.OrderedDict()
            for k,v in specifier.backness.items():
                if len(v) == 0:
                    self.backness[k] = set()
                else:
                    self.backness[k] = set(self.features_to_segments(v))

    def categorize(self, seg):
        if seg == '#':
            return None
        seg_features = seg.features
        if seg.feature_match(self.vowel_feature):
            category = ['Vowel']

            if seg.feature_match(self.diph_feature):
                category.insert(0,'Diphthong')
                return category

            for k,v in self.height.items():
                if seg.symbol in v:
                    category.append(k)
                    break
            else:
                category.append(None)
            for k,v in self.backness.items():
                if seg.symbol in v:
                    category.append(k)
                    break
            else:
                category.append(None)

            if seg.feature_match(self.rounded_feature):
                category.append('Rounded')
            else:
                category.append('Unrounded')
        else:
            category = ['Consonant']

            for k,v in self.places.items():
                if seg.symbol in v:
                    category.append(k)
                    break
            else:
                category.append(None)

            for k,v in self.manners.items():
                if seg.symbol in v:
                    category.append(k)
                    break
            else:
                category.append(None)

            if seg.feature_match(self.voice_feature):
                category.append('Voiced')
            else:
                category.append('Voiceless')
        return category

class Corpus(object):
    """
    Lexicon to store information about Words, such as transcriptions,
    spellings and frequencies

    Parameters
    ----------
    name : string
        Name to identify Corpus

    Attributes
    ----------

    name : str
        Name of the corpus, used only for easy of reference

    attributes : list of Attributes
        List of Attributes that Words in the Corpus have

    wordlist : dict
        Dictionary where every key is a unique string representing a word in a
        corpus, and each entry is a Word object

    words : list of strings
        All the keys for the wordlist of the Corpus

    specifier : FeatureSpecifier
        See the FeatureSpecifier object

    inventory : Inventory
        Inventory that contains information about segments in the Corpus
    """

    #__slots__ = ['name', 'wordlist', 'specifier',
    #            'inventory', 'orthography', 'custom', 'feature_system',
    #            'has_frequency_value','has_spelling_value','has_transcription_value']
    basic_attributes = ['spelling','transcription','frequency']
    def __init__(self, name):
        self.name = name
        self.wordlist = dict()
        self.specifier = None
        self.inventory = Inventory()
        self.has_frequency = True
        self.has_spelling = False
        self.has_wordtokens = False
        self._attributes = [Attribute('spelling','spelling'),
                            Attribute('transcription','tier'),
                            Attribute('frequency','numeric')]

    @property
    def has_transcription(self):
        for a in self.attributes:
            if a.att_type == 'tier' and len(a.range) > 0:
                return True
        return False

    def __eq__(self, other):
        if not isinstance(other,Corpus):
            return False
        if self.wordlist != other.wordlist:
            return False
        return True

    def __iadd__(self, other):
        for a in other.attributes:
            if a not in self.attributes:
                self.add_attribute(a)
        for w in other:
            try:
                sw = self.find(w.spelling)
                sw.frequency += w.frequency
                for a in self.attributes:
                    if getattr(sw, a.name) == a.default_value and getattr(w, a.name) != a.default_value:
                        setattr(sw, a.name, getattr(w, a.name))
                sw.wordtokens += w.wordtokens
            except KeyError:
                self.add_word(w)
        if self.specifier is None and other.specifier is not None:
            self.set_feature_matrix(other.specifier)
        return self

    def key(self, word):
        key = word.spelling
        if self[key] == word:
            return key
        count = 0
        while True:
            count += 1
            key = '{} ({})'.format(word.spelling,count)
            try:
                if self[key] == word:
                    return key
            except KeyError:
                break


    def keys(self):
        for k in sorted(self.wordlist.keys()):
            yield k

    def subset(self, filters):
        """
        Generate a subset of the corpus based on filters.

        Filters for Numeric Attributes should be tuples of an Attribute
        (of the Corpus), a comparison callable (``__eq__``, ``__neq__``,
        ``__gt__``, ``__gte__``, ``__lt__``, or ``__lte__``) and a value
        to compare all such attributes in the Corpus to.

        Filters for Factor Attributes should be tuples of an Attribute,
        and a set of levels for inclusion in the subset.

        Other attribute types cannot currently be the basis for filters.

        Parameters
        ----------
        filters : list of tuples
            See above for format

        Returns
        -------
        Corpus
            Subset of the corpus that matches the filter conditions
        """

        new_corpus = Corpus('')
        new_corpus._attributes = [Attribute(x.name, x.att_type, x.display_name)
                    for x in self.attributes]
        for word in self:
            for f in filters:
                if f[0].att_type == 'numeric':
                    op = f[1]
                    if not op(getattr(word,f[0].name), f[2]):
                        break
                elif f[0].att_type == 'factor':
                    if getattr(word,f[0].name) not in f[1]:
                        break
            else:
                new_corpus.add_word(word)
        return new_corpus

    @property
    def attributes(self):
        return self._attributes

    @property
    def words(self):
        return sorted(list(self.wordlist.keys()))

    def symbol_to_segment(self, symbol):
        for seg in self.inventory:
            if seg.symbol == symbol:
                return seg
        else:
            raise CorpusIntegrityError('Could not find {} in the inventory'.format(symbol))


    def features_to_segments(self, feature_description):
        """
        Given a feature description, return the segments in the inventory
        that match that feature description

        Feature descriptions should be either lists, such as
        ['+feature1', '-feature2'] or strings that can be separated into
        lists by ',', such as '+feature1,-feature2'.

        Parameters
        ----------
        feature_description : string or list
            Feature values that specify the segments, see above for format

        Returns
        -------
        list of Segments
            Segments that match the feature description

        """
        segments = list()
        if isinstance(feature_description,str):
            feature_description = feature_description.split(',')
        for k,v in self.inventory.items():
            if v.feature_match(feature_description):
                segments.append(k)
        return segments

    def segment_to_features(self, seg):
        """
        Given a segment, return the features for that segment.

        Parameters
        ----------
        seg : string or Segment
            Segment or Segment symbol to look up

        Returns
        -------
        dict
            Dictionary with keys as features and values as featue values
        """
        try:
            features = self.specifier.matrix[seg]
        except TypeError:
            features = self.specifier.matrix[seg.symbol]
        return features

    def add_abstract_tier(self, attribute, spec):
        """
        Add a abstract tier (currently primarily for generating CV skeletons
        from tiers).

        Specifiers for abstract tiers should be dictionaries with keys that
        are the abstract symbol (such as 'C' or 'V') and the values are
        iterables of segments that should count as that abstract symbols
        (such as all consonants or all vowels).

        Currently only operates on the ``transcription`` of words.

        Parameters
        ----------
        attribute : Attribute
            Attribute to add/replace

        spec : dict
            Mapping for creating abstract tier
        """
        for i,a in enumerate(self._attributes):
            if attribute.name == a.name:
                self._attributes[i] = attribute
                break
        else:
            self._attributes.append(attribute)
        for word in self:
            word.add_abstract_tier(attribute.name,spec)
            attribute.update_range(getattr(word,attribute.name))

    def add_attribute(self, attribute, initialize_defaults = False):
        """
        Add an Attribute of any type to the Corpus or replace an existing Attribute.

        Parameters
        ----------
        attribute : Attribute
            Attribute to add or replace

        initialize_defaults : boolean
            If True, words will have this attribute set to the ``default_value``
            of the attribute, defaults to False
        """
        for i,a in enumerate(self._attributes):
            if attribute.name == a.name:
                self._attributes[i] = attribute
                break
        else:
            self._attributes.append(attribute)
        if initialize_defaults:
            for word in self:
                word.add_attribute(attribute.name,attribute.default_value)

    def add_count_attribute(self, attribute, sequence_type, spec):
        """
        Add an Numeric Attribute that is a count of a segments in a tier that
        match a given specification.

        The specification should be either a list of segments or a string of
        the format '+feature1,-feature2' that specifies the set of segments.

        Parameters
        ----------
        attribute : Attribute
            Attribute to add or replace

        sequence_type : string
            Specifies whether to use 'spelling', 'transcription' or the name of a
            transcription tier to use for comparisons

        spec : list or str
            Specification of what segments should be counted
        """
        if isinstance(attribute,str):
            attribute = Attribute(attribute,'numeric')
        for i,a in enumerate(self._attributes):
            if attribute.name == a.name:
                self._attributes[i] = attribute
                break
        else:
            self._attributes.append(attribute)
        if isinstance(spec, str):
            tier_segs = self.features_to_segments(spec)
        else:
            tier_segs = spec
        for word in self:
            v = sum([1 for x in getattr(word, sequence_type) if x in tier_segs])
            setattr(word, attribute.name, v)
            attribute.update_range(v)

    def add_tier(self, attribute, spec):
        """
        Add a Tier Attribute based on the transcription of words as a new Attribute
        that includes all segments that match the specification.

        The specification should be either a list of segments or a string of
        the format '+feature1,-feature2' that specifies the set of segments.

        Parameters
        ----------
        attribute : Attribute
            Attribute to add or replace

        spec : list or str
            Specification of what segments should be counted
        """
        if isinstance(attribute,str):
            attribute = Attribute(attribute, 'tier')
        for i,a in enumerate(self._attributes):
            if attribute.name == a.name:
                self._attributes[i] = attribute
                break
        else:
            self._attributes.append(attribute)
        if isinstance(spec, str):
            tier_segs = self.features_to_segments(spec)
        else:
            tier_segs = spec
        attribute._range = tier_segs
        for word in self:
            word.add_tier(attribute.name,tier_segs)

    def remove_word(self, word_key):
        """
        Remove a Word from the Corpus using its identifier in the Corpus.

        If the identifier is not found, nothing happens.

        Parameters
        ----------
        word_key : string
            Identifier to use to remove the Word
        """
        try:
            del self.wordlist[word_key]
        except KeyError:
            pass

    def remove_attribute(self, attribute):
        """
        Remove an Attribute from the Corpus and from all its Word objects.

        Parameters
        ----------
        attribute : Attribute
            Attribute to remove
        """
        if isinstance(attribute,str):
            name = attribute
        else:
            name = attribute.name
        if name in self.basic_attributes:
            return
        for i in range(len(self._attributes)):
            if self._attributes[i].name == name:
                del self._attributes[i]
                break
        else:
            return
        for word in self:
            word.remove_attribute(name)

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self,state):
        try:
            if 'inventory' not in state:
                state['inventory'] = state['_inventory']
            if not isinstance(state['inventory'], Inventory):
                state['inventory'] = Inventory(state['inventory'])
            if 'has_spelling' not in state:
                state['has_spelling'] = state['has_spelling_value']
            if 'has_transcription' in state:
                del state['has_transcription']
            if 'has_wordtokens' not in state:
                state['has_wordtokens'] = False
            if '_freq_base' in state:
                del state['_freq_base']
            if '_attributes' not in state:
                state['_attributes'] = [Attribute('spelling','spelling'),
                                        Attribute('transcription','tier'),
                                        Attribute('frequency','numeric')]
                try:
                    tiers = state.pop('_tiers')
                    for t in tiers:
                        state['_attributes'].append(Attribute(t,'tier'))
                except KeyError:
                    pass
            self.__dict__.update(state)
            self._specify_features()
            #Backwards compatability
            for k,w in self.wordlist.items():
                w._corpus = self
                for a in self.attributes:
                    if a.att_type == 'tier':
                        if not isinstance(getattr(w,a.name), Transcription):
                            setattr(w,a.name,Transcription(getattr(w,a.name)))
                    else:
                        try:
                            a.update_range(getattr(w,a.name))
                        except AttributeError as e:
                            print(k)
                            print(w.__dict__)
                            raise(e)
        except Exception as e:
            raise(e)
            raise(CorpusIntegrityError("An error occurred while loading the corpus: {}.\nPlease redownload or recreate the corpus.".format(str(e))))

    def _specify_features(self):
        self.inventory.specify(self.specifier)

    def check_coverage(self):
        """
        Checks the coverage of the specifier (FeatureMatrix) of the Corpus over the
        inventory of the Corpus

        Returns
        -------
        list
            List of segments in the inventory that are not in the specifier
        """
        if not self.specifier is not None:
            return []
        return [x for x in self.inventory.keys() if x not in self.specifier]

    def iter_words(self):
        """
        Sorts the keys in the corpus dictionary,
        then yields the values in that order

        Returns
        -------
        generator
            Sorted Words in the corpus
        """
        sorted_list = sorted(self.wordlist.keys())
        for word in sorted_list:
            yield self.wordlist[word]

    def iter_sort(self):
        """
        Sorts the keys in the corpus dictionary, then yields the
        values in that order

        Returns
        -------
        generator
            Sorted Words in the corpus

        """
        sorted_list = sorted(self.wordlist.keys())
        for word in sorted_list:
            yield self.wordlist[word]

    def set_feature_matrix(self,matrix):
        """
        Set the feature system to be used by the corpus and make sure
        every word is using it too.

        Parameters
        ----------
        matrix : FeatureMatrix
            New feature system to use in the corpus
        """
        self.specifier = matrix
        self._specify_features()

    def get_random_subset(self, size, new_corpus_name='randomly_generated'):
        """Get a new corpus consisting a random selection from the current corpus

        Parameters
        ----------
        size : int
            Size of new corpus

        new_corpus_name : str

        Returns
        -------
        new_corpus : Corpus
            New corpus object with len(new_corpus) == size
        """
        new_corpus = Corpus(new_corpus_name)
        while len(new_corpus) < size:
            word = self.random_word()
            new_corpus.add_word(word, allow_duplicates=False)
        new_corpus.specifier = self.specifier
        return new_corpus

    def add_word(self, word, allow_duplicates=True):
        """Add a word to the Corpus.
        If allow_duplicates is True, then words with identical spelling can
        be added. They are kept sepearate by adding a "silent" number to them
        which is never displayed to the user. If allow_duplicates is False,
        then duplicates are simply ignored.

        Parameters
        ----------
        word : Word
            Word object to be added

        allow_duplicates : bool
            If False, duplicate Words with the same spelling as an existing
            word in the corpus will not be added

        """
        word._corpus = self
        #If the word doesn't exist, add it
        try:
            check = self.find(word.spelling, keyerror=True)
            if allow_duplicates:
                #Some words have more than one entry in a corpus, e.g. "live" and "live"
                #so they need to be assigned unique keys

                n = 0
                while True:
                    n += 1
                    #key = '{} ({})'.format(word.spelling.lower(),n)
                    key = '{} ({})'.format(word.spelling,n)
                    try:
                        check = self.find(key, keyerror=True)
                    except KeyError:
                    #if isinstance(check, EmptyWord):
                        self.wordlist[key] = word
                        break
            else:
                return
        except KeyError:
            self.wordlist[word.spelling] = word
            if word.spelling is not None:
                #self.orthography.update(word.spelling)
                if not self.has_spelling:
                    self.has_spelling = True

        if word.transcription is not None:
            self.update_inventory(word.transcription)
            word.transcription._list = [self.inventory[x].symbol for x in word.transcription._list]
        for d in word.descriptors:
            if d not in self.attributes:
                if isinstance(getattr(word,d),str):
                    self._attributes.append(Attribute(d,'factor'))
                elif isinstance(getattr(word,d),Transcription):
                    self._attributes.append(Attribute(d,'tier'))
                elif isinstance(getattr(word,d),(int, float)):
                    self._attributes.append(Attribute(d,'numeric'))
        for a in self.attributes:
            if not hasattr(word,a.name):
                word.add_attribute(a.name, a.default_value)
            a.update_range(getattr(word,a.name))

    def update_inventory(self, transcription):
        """
        Update the inventory of the Corpus to ensure it contains all
        the segments in the given transcription

        Parameters
        ----------
        transcription : list
            Segment symbols to add to the inventory if needed
        """
        for s in transcription:
            if isinstance(s, str):
                if s not in self.inventory:
                    self.inventory[s] = Segment(s)
        if transcription.stress_pattern:
            for k,v in transcription.stress_pattern.items():
                self.inventory.stresses[v].add(transcription[k])

    def get_or_create_word(self, **kwargs):
        """
        Get a Word object that has the spelling and transcription
        specified or create that Word, add it to the Corpus and return it.

        Parameters
        ----------
        spelling : string
            Spelling to search for

        transcription : list
            Transcription to search for

        Returns
        -------
        Word
            Existing or newly created Word with the spelling and transcription
            specified
        """
        try:
            spelling = kwargs['spelling']
            if isinstance(spelling,tuple):
                spelling = spelling[1]
        except KeyError:
            return None

        words = self.find_all(spelling)
        for w in words:
            for k,v in kwargs.items():
                if isinstance(v,tuple):
                    v = v[1]
                if isinstance(v,list):
                    v = Transcription(v)
                if getattr(w,k) != v:
                    break
            else:
                return w
        else:
            word = Word(**kwargs)
            self.add_word(word)
        return word

    def random_word(self):
        """Return a randomly selected Word

        Returns
        -------
        Word
            Random Word
        """
        word = random.choice(list(self.wordlist.keys()))
        return self.wordlist[word]

    def get_features(self):
        """
        Get a list of the features used to describe Segments

        Returns
        ----------
        list of str

        """
        return self.specifier.features

    def find(self, word, keyerror=True, ignore_case = False):
        """Search for a Word in the corpus
        If keyerror == True, then raise a KeyError if the word is not found
        If keyerror == False, then return an EmptyWord if the word is not found

        Parameters
        ----------
        word : str
            String representing the spelling of the word (not transcription)

        keyerror : bool
            Set whether a KeyError should be raised if a word is not found

        Returns
        -------
        result : Word or EmptyWord


        Raises
        ------
        KeyError if keyerror == True and word is not found

        """
        patterns = [word]
        if ignore_case:
            patterns.append(word.lower())
            patterns.append(word.title())
        for w in patterns:
            key = w
            try:
                result = self.wordlist[w]
                return result
            except KeyError:
                try:
                    key = '{} (1)'.format(w)
                    result = [self.wordlist[key]]
                    return result
                except KeyError:
                    pass

        raise KeyError('The word \"{}\" is not in the corpus'.format(word))

    def find_all(self, spelling):
        """
        Find all Word objects with the specified spelling

        Parameters
        ----------
        spelling : string
            Spelling to look up

        Returns
        -------
        list of Words
            Words that have the specified spelling
        """
        words = list()
        try:
            words.append(self.wordlist[spelling])
            count = 0
            while True:
                count += 1
                try:
                    words.append(self.wordlist['{} ({})'.format(spelling,count)])
                except KeyError:
                    break
        except KeyError:
            pass
        return words

    def __contains__(self,item):
        return self.wordlist.__contains__(item)

    def __len__(self):
        return len(self.wordlist)

    def __setitem__(self,item,value):
        self.wordlist[item] = value

    def __getitem__(self,item):
        return self.wordlist[item]

    def __iter__(self):
        return iter(self.wordlist.values())


