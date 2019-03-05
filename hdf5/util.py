#    Copyright (c) 2017 Idiap Research Institute, http://www.idiap.ch/
#    Written by Nikolaos Pappas <nikolaos.pappas@idiap.ch>,
#
#    This file is part of mhan.
#
#    mhan is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3 as
#    published by the Free Software Foundation.
#
#    mhan is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with mhan. If not, see http://www.gnu.org/licenses/

import os
import sys
import h5py
import pickle
import json, gzip
import numpy as np
from nltk.tokenize import sent_tokenize, word_tokenize
from keras.utils.np_utils import to_categorical
from keras.preprocessing.sequence import pad_sequences

LABB = {'english': 'en', 'german': 'de', 'spanish': 'es',
	'portuguese': 'pt', 'ukrainian': 'uk', 'russian': 'ru',
	'arabic': 'ar', 'persian': 'fa' }

def load_meanyvecc(wvec, y_idxs, wpad):
	wdim = wvec[0].shape[0]
	total = wpad
	vecs = wvec[y_idxs[:wpad]]
	return vecs.mean(axis=0)

def load_data(path=None):
	"""Load and return the specified dataset."""
	h =  h5py.File(path, 'r')
	print ("\t%s" % (path)).ljust(80) + "OK"

	try:
		label_ids = h['label_ids']
	except:
		label_ids = {}
	return h['X_ids'], h['Y_ids'], label_ids

def load_word_vectors(language, path):
	"""Function to load pre-trained word vectors."""
	print "[*] Loading %s word vectors..." % language
	wvec, vocab = {}, {}
	embeddings = pickle.load(open(path))
	wvec[language] = embeddings[1]
	vocab[language] = list(embeddings[0])
	print ("\t%s" % (path)).ljust(80) + "OK"
	return wvec, vocab


def load_vectors(x_idxs, y_idxs, idxs, wpad, num_labels, model):
	"""Load word vectors for a given sequence and apply zero-padding
	   according to the pre-defined limits."""
	X_vecs, Y_labels = [],  []
	revids = model.revids
	for i, idx in enumerate(idxs):
		try:
			x = x_idxs[str(idx)].value
			x_padded = np.zeros((wpad))
			if len(x) > wpad:
				x_padded[:wpad] = x[:wpad]
			else:
				x_padded[0:len(x)] = x
			y_cats =  np.sum(to_categorical(revids[y_idxs[str(idx)]], num_classes=num_labels),axis=0)
			X_vecs.append(x_padded)
			Y_labels.append(y_cats)
		except:
			continue
	return X_vecs, Y_labels

def load_vectors_bup(wvec, labels, x_idxs, y_idxs, wpad):
	"""Load word vectors for a given sequence and apply zero-padding
	   according to the pre-defined limits."""
	X_vecs, Y_labels = [],  []
	for idx, x in enumerate(x_idxs):
		x_vec  = pad_sequences([x], maxlen=wpad, padding='post').tolist()[0]
		y_cats =  np.sum(to_categorical(y_idxs[idx], num_classes=len(labels)),axis=0)
		y_cats[y_cats>1] = 1
		X_vecs.append(x_vec)
		Y_labels.append(y_cats)
	return X_vecs, Y_labels

def pick_best(dev_path):
	""" Pick the best model according to its validation score in the
	    specified experiment folder path. """
	ap = [float(open(dev_path+fn).read().split(' ')[1]) for fn in os.listdir(dev_path) if fn.find('val')>-1]
	weights = [fn for fn in os.listdir(dev_path) if fn.find('weights')>-1]
	best_idx = ap.index(max(ap))
	epoch_num = int(weights[best_idx].split('_')[1].split('-')[0])
	print "[*] Loading best model (e=%d, ap=%.3f)..." % (epoch_num, ap[best_idx])
	print ("\t%s" % (dev_path+weights[best_idx]) ).ljust(80) + "OK"
	return epoch_num, dev_path+weights[best_idx]

def export(lang, lang_idx, source_idx, epreds, watts, satts, XT_ids, YT_ids, vocabs, labels, top_k=20):
	""" Function which returns a dictionary with the top-k predictions and
	    attention scores of a given model on a given test set, along with
	    the corresponding texts and their gold labels. """
	out = {}
	for i, x in enumerate(XT_ids[lang_idx]):
		text, tags, gold_tags = [], [], []
		for j, xi in enumerate(x):
			text.append([vocabs[lang_idx][wid] for wid in xi])
		for y in YT_ids[lang_idx][i]:
			labwords = labels[lang_idx][y]
			words = [vocabs[lang_idx][int(wid)] for wid in labwords.split('_')]
			gold_tags.append(' '.join(words))
		top_ids = np.argsort(epreds[i])[::-1]
		for y in top_ids[:top_k]:
			labwords = labels[source_idx][y]
			words = [vocabs[source_idx][int(wid)] for wid in labwords.split('_')]
			tags.append([' '.join(words), str(epreds[i][y])] )
		out["%s_%d" % (	LABB[lang], i)] = {'text': text,
				  'watts': watts[i].tolist(),
				  'satts': satts[i].tolist(),
				  'gold_tags': gold_tags,
				  'tags': tags}
	return out

def one_error(reals, preds):
	""" Computes the one-error metric between ground truth and predictions. """
	max_idx = np.argmax(preds)
	if max_idx in reals.nonzero()[0].tolist():
		return 0
	else:
		return 1

def load_missing_args(args, parsed_args):
	""" Load default or given arguments in case they are missing from the
	    set of arguments of the pre-trained model."""
	args['train'] = parsed_args.train
	args['path'] = parsed_args.path
	args['source'] = parsed_args.source
	args['target'] = parsed_args.target
	args['test'] = parsed_args.test
	args['store_test'] = parsed_args.store_test
	args['t'] = parsed_args.t
	args['mode'] = parsed_args.mode
	args['seen_ids'] = parsed_args.seen_ids
	args['unseen_ids'] = parsed_args.unseen_ids
	args['chunks'] = parsed_args.chunks
	args['bs'] = parsed_args.bs
	if parsed_args.languages is None:
		parsed_args.languages = args['languages']
	return args, parsed_args
