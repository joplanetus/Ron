# -*- coding:utf8 -*-
# !/usr/bin/env python
# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time

from flask import Flask, request, make_response, jsonify
from flask.logging import create_logger
from GoogleSheet.read import (
    get_best_rate,
    get_last_updated
)
from Random import Random

# Start Flask.
app = Flask(__name__)
log = create_logger(app)


@app.route('/', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    try:
        intent = req.get('queryResult').get('intent').get('displayName')
    except AttributeError:
        return 'json error'

    print('Intent name: ' + intent)
    if intent == 'description':
        res = description(req)
    elif intent == 'compareRate':
        res = compare_rate(req)
    elif intent == 'bestRate':
        res, output_contexts = best_rate(req)
        r = make_response(res)
        r.headers['Content-Type'] = 'application/json'
        return make_response(jsonify({'fulfillmentText': res, 'outputContexts': output_contexts}))
    elif intent == 'rate-followup':
        res = rate_followup(req)
    elif intent == 'bestRate - followup':
        res = compare_followup(req)
    elif intent == 'Default Welcome Intent':
        res = welcome()
    elif intent == 'show_time':
        res = show_time()
    else:
        res = "Unexpected action"
        log.error('Unexpected action')

    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return make_response(jsonify({'fulfillmentText': res}))


def get_parameters(req):
    return req['queryResult']['parameters']


def get_contexts(req, pos):
    return req['queryResult']['outputContexts'][pos]


def description(req):
    parameters = req['queryResult']['parameters']

    abv_description = parameters["Abv_description"]
    response = Random.description(abv_description)
    return response


def compare_rate(req):
    parameters = get_parameters(req)

    params = {
        "bank1": parameters['Australian_Banks'],
        "bank2": parameters['Australian_Banks1'],
        "mortgage": parameters['Mortgage_types'],
        "year_fixed": parameters['year_fixed'],
        "ownership_status": parameters['ownership_status']
    }

    # TODO: Check if bank1 and bank2 are the same. if the same bank, 
    # tell user that he/she put in the same name of bank.
    best_rate_bank1 = get_best_rate(
        params["bank1"] or None, params["mortgage"] or None, 
        params["year_fixed"] or None, params['ownership_status'] or None)
    
    best_rate_bank2 = get_best_rate(
        params["bank2"] or None, params["mortgage"] or
        best_rate_bank1['repayment_type'], params["year_fixed"] or best_rate_bank1['year_fixed'],
        params['ownership_status'] or best_rate_bank1['ownership_type'])

    response = Random.compare_bank(best_rate_bank1, best_rate_bank2)
    return response


def best_rate(req):
    parameters = get_parameters(req)

    params = {
        "bank": parameters['Australian_Banks'],
        "mortgage": parameters['Mortgage_types'],
        "fixed_year": parameters['year_fixed'],
        "ownership_status": parameters['ownership_status']
    }

    best_rate = get_best_rate(
        params['bank'] or None, params['mortgage'] or None,
        params['fixed_year'] or None, params['ownership_status'] or None)

    response = Random.best_bank(params, best_rate)

    # TODO: Static Output Contexts, there should be a better way of doing it.
    output_contexts = [{
        "name": "projects/ron-anpelr/agent/sessions/e1dc138a-9f22-7941-80de-8998ede6221b/contexts/showrate-followup",
        "lifespanCount": 5,
        "parameters": {
            "fixed_year": best_rate['year_fixed'],
            "Australian_Banks": best_rate['bank_name'],
            "repayment_type": best_rate['repayment_type'],
            "ownership_status": best_rate['ownership_type'],
            "rate": best_rate['interest_rate']
        }
    },
        {
            "name": "projects/ron-anpelr/agent/sessions/e1dc138a-9f22-7941-80de-8998ede6221b/contexts/bestrate-followup",
            "lifespanCount": 5,
            "parameters": {
                "rate": best_rate['interest_rate']
            }
        }
    ]

    return response, output_contexts


def compare_followup(req):
    parameters = get_parameters(req)

    params = {
        "bank": parameters['Australian_Banks'],
        "mortgage": parameters['Mortgage_types'],
        "fixed_year": parameters['year_fixed'],
        "ownership_status": parameters['ownership_status']
    }

    context = get_contexts(req, pos=1)
    old_rate = context['parameters']['rate']

    new_best_rate = get_best_rate(
        params['bank'] or None, params['mortgage'] or None, 
        params['fixed_year'] or None, params['ownership_status'] or None)

    response = Random.best_rate_compare_followup(old_rate, new_best_rate)
    return response


def rate_followup(req):
    parameters = get_parameters(req)
    params = {
        "bank": parameters['Australian_Banks'],
        "mortgage": parameters['Mortgage_types'],
        "fixed_year": parameters['year_fixed'],
        "ownership_status": parameters['ownership_status']
    }
    best_rate = get_best_rate(
        params['bank'] or None, params['mortgage'] or None, 
        params['fixed_year'] or None, params['ownership_status'] or None)
    response = Random.best_bank(
        params, best_rate)

    return response

def welcome():
    timestamp_updated = get_last_updated()

    response = Random.welcome_response(timestamp_updated)
    return response

def show_time():
    timestamp_updated = get_last_updated()

    response = Random.show_time(timestamp_updated)
    return response

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0', threaded=True)
