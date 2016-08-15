#! /usr/bin/ENV python3
"""Runs the Metadata Map"""

import flask
import os
import uuid
import threading
import pickle
import random
import sys
import numpy as np

from activetm.active import evaluate
from activetm.active import select
from activetm import models
from activetm import utils
from ankura.topic import topic_summary_tokens

APP = flask.Flask(__name__, static_url_path='')

def _get_user_dict_on_start():
    """Load user data if server restarted"""
    # This maintains state if the server crashes
    try:
        last_state = open('last_state.pickle', 'rb')
    except IOError:
        print('No last_state.pickle file, assuming no previous state')
    else:
        state = pickle.load(last_state)
        print('last_state.pickle file loaded')
        last_state.close()
        return state['USER_DICT']
    # but if the server is starting fresh, so does the user data
    return {}


def _get_dataset():
    """Get the dataset from a pickle file in the local directory"""
    with open('dataset.pickle', 'rb') as in_file:
        dataset = pickle.load(in_file)
        return dataset


###############################################################################
# USER_DICT holds information for individual users
USER_DICT = _get_user_dict_on_start()
# MODELS holds the model for each user
MODELS = {}
SELECT_METHOD = select.factory['random']
CAND_SIZE = 500
LABEL_INCREMENT = 1

# Start training after START_TRAINING labeled documents
START_TRAINING = 30
# Train every TRAINING_INCREMENT labeled documents after START_TRAINING
TRAINING_INCREMENT = 10

# Label and uncertainty if we don't have a trained model
BASE_LABEL = 0.5
BASE_UNCERTAINTY = 0.5

LOCK = threading.Lock()
RNG = random.Random()
DATASET = _get_dataset()
ALL_DOC_IDS = [doc for doc in range(DATASET.num_docs)]
###############################################################################


def _save_state():
    """Save the state of the server to a pickle file"""
    last_state = {}
    last_state['USER_DICT'] = USER_DICT
    pickle.dump(last_state, open('last_state.pickle', 'wb'))


@APP.route('/')
def serve_landing_page():
    """Serve the landing page for the Metadata Map UI"""
    return flask.send_from_directory('static', 'index.html')


@APP.route('/end')
def serve_end():
    """Serve the end page, which gets rid of cookies and deletes the user"""
    return flask.send_from_directory('static', 'end.html')


@APP.route('/removeuser')
def remove_user():
    """Remove a user when that user goes to end.html"""
    uid = str(flask.request.headers.get('uuid'))
    # Remove the uid and all related information from the USER_DICT
    USER_DICT.pop(uid, None)
    return flask.jsonify({})


def _build_model():
    """Build a model for a user"""
    settings = {}
    settings['model'] = 'semi_ridge_anchor'
    settings['numtopics'] = 20
    settings['numtrain'] = 1
    settings['expgrad_epsilon'] = 1e-4
    return models.build(RNG, settings)


def _train_model(uid):
    """Train the model if we have enough labeled data"""
    restarted = False
    trained = False
    with LOCK:
        # If uid is not in MODELS, it means the server restarted and we
        #   need to retrain the model if it was trained before the restart
        if uid not in MODELS:
            MODELS[uid] = (_build_model(), _build_model())
            restarted = True
        num_labeled_ids = len(USER_DICT[uid]['docs_with_labels'])
        # Train at 30, 40, 50... documents labeled
        if (num_labeled_ids >= START_TRAINING and
        (restarted or num_labeled_ids % TRAINING_INCREMENT == 0)):
            USER_DICT[uid]['training_complete'] = False
            labeled_doc_ids = []
            labels_one = []
            labels_two = []
            for doc_id, label in USER_DICT[uid]['docs_with_labels'].items():
                labeled_doc_ids.append(doc_id)
                # Labels are tuples, one value for horiz and one for vert
                labels_one.append(label['x'])
                labels_two.append(label['y'])
            MODELS[uid][0].train(DATASET, labeled_doc_ids, labels_one, True)
            MODELS[uid][1].train(DATASET, labeled_doc_ids, labels_two, True)
            # Get topics for each document, new ones if we retrained the model
            for doc_number in USER_DICT[uid]['docs_with_labels'].keys():
                doc_tokens = DATASET.doc_tokens(doc_number)
                docws = MODELS[uid][0]._convert_vocab_space(doc_tokens)
                topics = list(MODELS[uid][0]._predict_topics(0, docws))
                USER_DICT[uid]['docs_with_labels'][doc_number]['topics'] = topics
            for doc_number in USER_DICT[uid]['predicted_docs'].keys():
                doc_tokens = DATASET.doc_tokens(doc_number)
                docws = MODELS[uid][0]._convert_vocab_space(doc_tokens)
                topics = list(MODELS[uid][0]._predict_topics(0, docws))
                USER_DICT[uid]['predicted_docs'][doc_number]['topics'] = topics
            USER_DICT[uid]['training_complete'] = True
            trained = True
    return trained


@APP.route('/uuid')
def get_uid():
    """Send a UUID to the client"""
    uid = str(uuid.uuid4())
    data = {'id': uid}
    # Create a model here
    MODELS[uid] = (_build_model(), _build_model())
    with LOCK:
        USER_DICT[uid] = {
            'current_doc': -1,
            # This is a doc_number to label mapping
            'docs_with_labels': {},
            'predicted_docs': {},
            'unlabeled_doc_ids': list(ALL_DOC_IDS),
            'training_complete': False
        }
        _save_state()
    return flask.jsonify(data)


@APP.route('/labeldoc', methods=['POST'])
def label_doc():
    """Receive the label for the previously sent document"""
    uid = str(flask.request.headers.get('uuid'))
    doc_number = int(flask.request.values.get('doc_number'))
    label_x = float(flask.request.values.get('label_x'))
    label_y = float(flask.request.values.get('label_y'))
    text = DATASET.doc_metadata(doc_number, 'text')
    title = DATASET.titles[doc_number]
    topics = None
    with LOCK:
        if uid in USER_DICT:
            # If this endpoint was hit multiple times (say while the model was
            #   training), then we want to only act on the first request
            if doc_number in USER_DICT[uid]['docs_with_labels'].keys():
                return flask.jsonify(user_id=uid)
            if USER_DICT[uid]['training_complete']:
                doc_tokens = DATASET.doc_tokens(doc_number)
                docws = MODELS[uid][0]._convert_vocab_space(doc_tokens)
                topics = list(MODELS[uid][0]._predict_topics(0, docws))
            USER_DICT[uid]['docs_with_labels'][doc_number] = {'x': label_x,
                                                              'y': label_y,
                                                              'text': text,
                                                              'title': title,
                                                              'topics': topics}
            USER_DICT[uid]['unlabeled_doc_ids'].remove(doc_number)
    _save_state()
    return flask.jsonify({'topics': topics})


@APP.route('/getdoc')
def get_doc():
    """Get the next document for this user"""
    uid = str(flask.request.headers.get('uuid'))
    doc_number = -1
    document = ''
    predicted_label_x = BASE_LABEL
    uncertainty_x = BASE_UNCERTAINTY
    predicted_label_y = BASE_LABEL
    uncertainty_y = BASE_UNCERTAINTY
    if uid not in MODELS:
        _train_model(uid)
    with LOCK:
        if uid in USER_DICT:
            # do what we need to get the right document for this user
            docs_with_labels = USER_DICT[uid]['docs_with_labels']
            unlabeled_doc_ids = USER_DICT[uid]['unlabeled_doc_ids']
            cand_set = select.reservoir(unlabeled_doc_ids, RNG, CAND_SIZE)
            # We are currently choosing based on what model 0 wants
            # TODO: Use both models' output to choose the next doc
            doc_number = SELECT_METHOD(DATASET, docs_with_labels.keys(),
                        cand_set, MODELS[uid][0], RNG, LABEL_INCREMENT)[0] 
            document = DATASET.doc_metadata(doc_number, 'text')
            doc_title = DATASET.titles[doc_number]
            USER_DICT[uid]['current_doc'] = doc_number
            if (len(docs_with_labels) >= START_TRAINING and
            USER_DICT[uid]['training_complete'] is True):
                doc = DATASET.doc_tokens(doc_number)
                predicted_label_x = MODELS[uid][0].predict(doc)
                uncertainty_x = MODELS[uid][0].get_uncertainty(doc)
                predicted_label_y = MODELS[uid][1].predict(doc)
                uncertainty_y = MODELS[uid][1].get_uncertainty(doc)
    _save_state()
    return flask.jsonify(document=document,
                         doc_number=doc_number,
                         doc_title=doc_title,
                         predicted_label_x=predicted_label_x,
                         uncertainty_x=uncertainty_x,
                         predicted_label_y=predicted_label_y,
                         uncertainty_y=uncertainty_y)


@APP.route('/train')
def train_endpoint():
    """Start training the user's model if needed"""
    uid = str(flask.request.headers.get('uuid'))
    trained = False
    if uid in USER_DICT:
        trained = _train_model(uid)
        # If we trained, we need to give the client the new topics
        labeled_docs = USER_DICT[uid]['docs_with_labels']
        predicted_docs = USER_DICT[uid]['predicted_docs']
        return flask.jsonify({'trained': trained,
                              'labeled_docs': labeled_docs,
                              'predicted_docs': predicted_docs})
    return flask.jsonify({'trained': trained})


@APP.route('/istrained')
def is_model_trained():
    """Check if the user's model is trained"""
    uid = str(flask.request.headers.get('uuid'))
    trained = False
    if uid in USER_DICT:
        if USER_DICT[uid]['training_complete']:
            trained = True
    return flask.jsonify({'trained': trained})


@APP.route('/olddoc')
def old_doc():
    """Get old document and predicted/labeled document values for a user"""
    uid = str(flask.request.headers.get('uuid'))
    doc_number = USER_DICT[uid]['current_doc']
    document = DATASET.doc_metadata(doc_number, 'text')
    doc_title = DATASET.titles[doc_number]
    predicted_label_x = BASE_LABEL
    uncertainty_x = BASE_UNCERTAINTY
    predicted_label_y = BASE_LABEL
    uncertainty_y = BASE_UNCERTAINTY
    topic_tokens = None
    if uid not in MODELS:
        _train_model(uid)
    with LOCK:
        if len(USER_DICT[uid]['docs_with_labels']) >= START_TRAINING:
            doc = DATASET.doc_tokens(doc_number)
            predicted_label_x = MODELS[uid][0].predict(doc)
            uncertainty_x = MODELS[uid][0].get_uncertainty(doc)
            predicted_label_y = MODELS[uid][1].predict(doc)
            uncertainty_y = MODELS[uid][1].get_uncertainty(doc)
            topics = MODELS[uid][0].get_topics(0)
            topic_tokens = topic_summary_tokens(topics, DATASET)
    return flask.jsonify(document=document,
                         doc_number=doc_number,
                         doc_title=doc_title,
                         predicted_label_x=predicted_label_x,
                         uncertainty_x=uncertainty_x,
                         predicted_label_y=predicted_label_y,
                         uncertainty_y=uncertainty_y,
                         labeled_docs=USER_DICT[uid]['docs_with_labels'],
                         predicted_docs=USER_DICT[uid]['predicted_docs'],
                         topic_tokens=topic_tokens)


@APP.route('/predictions')
def make_predictions():
    """Make num_docs predictions and send them to the client"""
    uid = str(flask.request.headers.get('uuid'))
    num_docs = int(flask.request.headers.get('num_docs'))
    # These are the documents to send
    send_docs = random.sample(USER_DICT[uid]['unlabeled_doc_ids'], num_docs)
    for i, doc_number in enumerate(send_docs):
        doc = DATASET.doc_tokens(doc_number)
        label_x = MODELS[uid][0].predict(doc)
        label_y = MODELS[uid][1].predict(doc)
        doc_text = DATASET.doc_metadata(doc_number, 'text')
        doc_title = DATASET.titles[doc_number]
        doc_tokens = DATASET.doc_tokens(doc_number)
        docws = MODELS[uid][0]._convert_vocab_space(doc_tokens)
        topics = list(MODELS[uid][0]._predict_topics(0, docws))
        send_docs[i] = {'document': doc_text,
                        'doc_number': doc_number,
                        'doc_title': doc_title,
                        'predicted_label_x': label_x,
                        'predicted_label_y': label_y,
                        'topics': topics}
        USER_DICT[uid]['predicted_docs'][doc_number] = {'x': label_x,
                                                        'y': label_y,
                                                        'title': doc_title,
                                                        'text': doc_text,
                                                        'topics': topics}
        USER_DICT[uid]['unlabeled_doc_ids'].remove(doc_number)
    _save_state()
    return flask.jsonify(documents=send_docs)


@APP.route('/topics')
def get_topics():
    """Return the topics for each model"""
    uid = str(flask.request.headers.get('uuid'))
    topics = MODELS[uid][0].get_topics(0)
    topic_tokens = topic_summary_tokens(topics, DATASET)
    return flask.jsonify({'topic_tokens': topic_tokens})


@APP.route('/vocab')
def get_vocab():
    """Return the vocabulary for the dataset"""
    return flask.jsonify({'vocab': DATASET.vocab})


if __name__ == '__main__':
    APP.run(debug=True,
            host='0.0.0.0',
            port=3000)
